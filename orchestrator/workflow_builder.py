"""Декларативная сборка графов: проверка и компиляция без исполнения действий."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .runtime_contracts import Graph, Node

NAME = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
REF = re.compile(r"^[a-zA-Z][a-zA-Z0-9_/-]*@[1-9][0-9]*$")
TOP = {"schema_version", "component", "inputs", "outputs", "outcomes", "execution",
       "effects", "config_schema", "config", "nodes", "exits", "model_profiles",
       "runtime", "terminal_states"}


class WorkflowBuildError(ValueError):
    """Ошибка с местом в определении и машинным кодом."""

    def __init__(self, code: str, message: str, location: str = ""):
        self.code, self.location = code, location
        super().__init__(message)

    def as_dict(self):
        return {"code": self.code, "message": str(self), "location": self.location}


def fail(message, location="", code="invalid_definition"):
    raise WorkflowBuildError(code, message, location)


def object_at(value, location, allowed=None):
    if not isinstance(value, dict):
        fail("Ожидается объект", location)
    if allowed is not None and set(value) - set(allowed):
        fail("Неизвестные поля: " + ", ".join(sorted(set(value) - set(allowed))), location)
    return value


def text(value, location):
    if not isinstance(value, str) or not value.strip():
        fail("Ожидается непустая строка", location)
    return value


def positive(value, location):
    if type(value) is not int or value < 1:
        fail("Ожидается положительное целое число", location)
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_toml(path):
    try:
        return tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise WorkflowBuildError("read_error", str(exc), str(path)) from exc


def merge(base, patch):
    result = copy.deepcopy(base)
    for key, value in patch.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else copy.deepcopy(value)
    return result


def trace(value, source, prefix=""):
    result = {}
    for key, child in value.items():
        field = prefix + key
        if isinstance(child, dict) and child:
            result.update(trace(child, source, field + "."))
        else:
            result[field] = source
    return result


def check_schema(schema, location):
    object_at(schema, location, {"type", "properties", "required", "additionalProperties", "items", "enum", "minimum", "maximum", "minItems", "minLength"})
    kind = schema.get("type")
    if kind not in {"object", "array", "string", "integer", "number", "boolean", "null"}:
        fail("Неподдерживаемый тип схемы", location)
    if "enum" in schema and (not isinstance(schema["enum"], list) or not schema["enum"]):
        fail("enum должен быть непустым списком", location)
    if kind == "object":
        props = object_at(schema.get("properties", {}), location + ".properties")
        required = schema.get("required", [])
        if not isinstance(required, list) or any(not isinstance(k, str) or k not in props for k in required) or len(set(required)) != len(required):
            fail("required должен перечислять уникальные объявленные properties", location)
        if type(schema.get("additionalProperties", False)) is not bool:
            fail("additionalProperties поддерживает только boolean", location)
        for key, child in props.items():
            check_schema(child, location + "." + key)
    elif "properties" in schema or "required" in schema or "additionalProperties" in schema:
        fail("Поля object заданы для другого типа", location)
    if kind == "array":
        check_schema(schema.get("items"), location + ".items")
    elif "items" in schema or "minItems" in schema:
        fail("Поля array заданы для другого типа", location)
    for key in ("minItems", "minLength"):
        if key in schema and (type(schema[key]) is not int or schema[key] < 0):
            fail(key + " должен быть неотрицательным integer", location)
    if "minLength" in schema and kind != "string":
        fail("minLength допустим только для string", location)
    for key in ("minimum", "maximum"):
        if key in schema and (kind not in {"number", "integer"} or type(schema[key]) not in {int, float}):
            fail(key + " допустим только для чисел", location)
    if "minimum" in schema and "maximum" in schema and schema["minimum"] > schema["maximum"]:
        fail("minimum больше maximum", location)


def validate_value(value, schema, location):
    kind = schema["type"]
    valid = {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str),
             "integer": type(value) is int, "number": type(value) in {int, float}, "boolean": type(value) is bool, "null": value is None}[kind]
    if not valid:
        fail("Значение не соответствует типу " + kind, location, "contract_mismatch")
    if "enum" in schema and not any(type(value) is type(item) and value == item for item in schema["enum"]):
        fail("Значение отсутствует в enum", location, "contract_mismatch")
    if kind == "object":
        props = schema.get("properties", {})
        if set(schema.get("required", [])) - set(value):
            fail("Отсутствуют обязательные поля", location, "contract_mismatch")
        if not schema.get("additionalProperties", False) and set(value) - set(props):
            fail("Неизвестные поля результата", location, "contract_mismatch")
        for key in value.keys() & props.keys():
            validate_value(value[key], props[key], location + "." + key)
    if kind == "array":
        if len(value) < schema.get("minItems", 0):
            fail("Недостаточно элементов", location, "contract_mismatch")
        for i, item in enumerate(value):
            validate_value(item, schema["items"], f"{location}[{i}]")
    if kind == "string" and len(value) < schema.get("minLength", 0):
        fail("Слишком короткая строка", location, "contract_mismatch")
    if kind in {"integer", "number"}:
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            fail("Значение выходит за границы", location, "contract_mismatch")


class ComponentLibrary:
    """Явно заданные каталоги; конфигурация не импортирует исполняемый код."""

    def __init__(self, roots):
        if isinstance(roots, (str, Path)):
            roots = [roots]
        self.components, self.contracts, self.sources = {}, {}, {}
        for root in map(Path, roots):
            if not root.is_dir():
                fail("Каталог библиотеки отсутствует", str(root), "read_error")
            for path in sorted((root / "contracts").glob("*.json")):
                try:
                    item = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, ValueError) as exc:
                    raise WorkflowBuildError("read_error", str(exc), str(path)) from exc
                object_at(item, str(path), {"id", "schema"})
                cid = text(item.get("id"), str(path) + ".id")
                check_schema(item.get("schema"), cid)
                if cid in self.contracts:
                    fail("Контракт объявлен повторно", cid)
                self.contracts[cid] = item["schema"]
            for path in sorted((root / "components").glob("*.toml")):
                item = read_toml(path)
                ref = self.validate_manifest(item, str(path))
                if ref in self.components:
                    fail("Компонент объявлен повторно", ref)
                self.components[ref] = item
                self.sources[ref] = str(path)
        for ref, item in self.components.items():
            self.validate_contracts(item, ref)

    def validate_manifest(self, item, location):
        object_at(item, location, TOP)
        if type(item.get("schema_version")) is not int or item["schema_version"] != 1:
            fail("Поддерживается schema_version=1", location)
        meta = object_at(item.get("component"), location + ".component", {"id", "version", "kind", "title", "description", "entry"})
        ref = text(meta.get("id"), location) + "@" + str(positive(meta.get("version"), location))
        if not REF.fullmatch(ref) or meta.get("kind") not in {"node", "subgraph", "workflow"}:
            fail("Неверный id или kind компонента", location)
        text(meta.get("title"), location + ".title")
        text(meta.get("description"), location + ".description")
        for field in ("inputs", "outputs"):
            for name, contract in object_at(item.get(field, {}), location + "." + field).items():
                if not NAME.fullmatch(name):
                    fail("Неверное имя порта", location + "." + name)
                text(contract, location + "." + name)
        outcomes = object_at(item.get("outcomes"), location + ".outcomes")
        if not outcomes:
            fail("Нужен хотя бы один outcome", location)
        for outcome, ports in outcomes.items():
            if not NAME.fullmatch(outcome) or not isinstance(ports, list) or any(not isinstance(p, str) or p not in item.get("outputs", {}) for p in ports) or len(set(ports)) != len(ports):
                fail("Исход должен перечислять уникальные выходные порты", location + ".outcomes." + outcome)
        for key, value in object_at(item.get("effects", {}), location + ".effects", {"writes_repository", "writes_task_manager", "external_actions"}).items():
            if type(value) is not bool:
                fail("Эффект должен быть boolean", location + ".effects." + key)
        if meta["kind"] == "node":
            if any(key in item for key in ("nodes", "exits", "terminal_states")) or "entry" in meta:
                fail("Атомарный узел не содержит вложенный граф", location)
            execution = object_at(item.get("execution"), location + ".execution", {"kind", "model_profile", "instruction", "skill", "capability"})
            if execution.get("kind") not in {"agent", "tool", "deterministic"}:
                fail("Узел требует execution.kind", location)
            for key, value in execution.items():
                text(value, location + ".execution." + key)
            if execution["kind"] == "agent" and not execution.get("instruction") and not execution.get("skill"):
                fail("Agent узел требует instruction или skill", location)
            if execution["kind"] != "agent" and ("model_profile" in execution or not execution.get("capability")):
                fail("Tool/deterministic требует capability и не принимает model_profile", location)
            if set(item.get("effects", {})) != {"writes_repository", "writes_task_manager", "external_actions"}:
                fail("Узел должен явно объявить все эффекты", location)
        else:
            text(meta.get("entry"), location + ".entry")
            if not object_at(item.get("nodes"), location + ".nodes"):
                fail("Подграф должен содержать узлы", location)
            object_at(item.get("exits"), location + ".exits")
            for key, value in object_at(item.get("execution", {}), location + ".execution", {"model_profile"}).items():
                text(value, location + ".execution." + key)
        if meta["kind"] != "workflow" and any(key in item for key in ("model_profiles", "runtime", "terminal_states")):
            fail("Профили и runtime/terminal_states принадлежат корневому workflow", location)
        return ref

    def validate_contracts(self, item, location):
        for field in ("inputs", "outputs"):
            for contract in item.get(field, {}).values():
                if contract not in self.contracts:
                    fail("Контракт отсутствует в библиотеке: " + contract, location, "unknown_contract")

    def get(self, ref):
        if not isinstance(ref, str) or not REF.fullmatch(ref) or ref not in self.components:
            fail("Компонент отсутствует или ссылка не фиксирует версию", str(ref), "unknown_component")
        return copy.deepcopy(self.components[ref])

    def catalog(self):
        return [{"ref": ref, **copy.deepcopy(item["component"]), "inputs": item.get("inputs", {}),
                 "outputs": item.get("outputs", {}), "outcomes": item["outcomes"]} for ref, item in sorted(self.components.items())]


@dataclass(frozen=True)
class ResolvedWorkflow:
    graph: Graph
    _snapshot: bytes

    def to_dict(self):
        return json.loads(self._snapshot)

    @property
    def digest(self):
        return self.to_dict()["digest"]

    @property
    def runtime_options(self):
        return self.to_dict()["runtime"]

    def validate_outputs(self, node_id, outcome, outputs):
        snap = self.to_dict()
        if node_id not in snap["leaves"]:
            fail("Неизвестный runtime node", node_id)
        node = snap["leaves"][node_id]
        if outcome not in node["outcomes"]:
            fail("Неизвестный outcome", node_id)
        object_at(outputs, node_id, node["outputs"])
        if set(node["outcomes"][outcome]) - set(outputs):
            fail("Отсутствуют обязательные выходные порты", node_id, "contract_mismatch")
        for port, value in outputs.items():
            validate_value(value, snap["contracts"][node["outputs"][port]], node_id + "." + port)


class WorkflowBuilder:
    def __init__(self, library: ComponentLibrary):
        self.library = library

    def load(self, path, *, overlay=None):
        return self.resolve(read_toml(path), overlay=read_toml(overlay) if overlay else None,
                            source=str(path), overlay_source=str(overlay) if overlay else "project")

    def resolve(self, definition, *, overlay=None, source="workflow", overlay_source="project"):
        definition = copy.deepcopy(definition)
        self.library.validate_manifest(definition, source)
        self.library.validate_contracts(definition, source)
        if definition["component"]["kind"] != "workflow":
            fail("Компиляция требует корневой workflow; подключите подграф как экземпляр", source)
        tree = self._expand(definition, "", [], source)
        profiles = copy.deepcopy(definition.get("model_profiles", {}))
        runtime = copy.deepcopy(definition.get("runtime", {}))
        profile_sources = trace(profiles, source)
        runtime_sources = trace(runtime, source)
        if overlay is not None:
            object_at(overlay, overlay_source, {"schema_version", "nodes", "model_profiles", "runtime"})
            if type(overlay.get("schema_version")) is not int or overlay["schema_version"] != 1:
                fail("Overlay требует schema_version=1", overlay_source)
            patches = object_at(overlay.get("nodes", {}), overlay_source + ".nodes")
            for path, patch in sorted(patches.items(), key=lambda pair: (pair[0].count("."), pair[0])):
                self._overlay(tree, path, patch, overlay_source)
            profiles = merge(profiles, object_at(overlay.get("model_profiles", {}), overlay_source + ".model_profiles"))
            runtime = merge(runtime, object_at(overlay.get("runtime", {}), overlay_source + ".runtime"))
            profile_sources.update(trace(overlay.get("model_profiles", {}), overlay_source))
            runtime_sources.update(trace(overlay.get("runtime", {}), overlay_source))
        for name, profile in object_at(profiles, "model_profiles").items():
            if not NAME.fullmatch(name):
                fail("Неверное имя профиля", name)
            object_at(profile, "model_profiles." + name, {"provider", "model", "reasoning"})
            text(profile.get("provider"), name + ".provider")
            text(profile.get("model"), name + ".model")
            if "reasoning" in profile:
                text(profile["reasoning"], name + ".reasoning")
        self._finalize(tree, {}, {}, profiles)
        self._check_graph(tree)
        terminals = object_at(definition.get("terminal_states", {}), "terminal_states", definition["outcomes"])
        if set(terminals) != set(definition["outcomes"]) or any(t not in {"succeeded", "failed", "cancelled"} for t in terminals.values()):
            fail("Корневые outcomes требуют явных terminal_states", "terminal_states")
        leaves = {}
        flat = {}
        self._compile(tree, terminals, flat, leaves)
        object_at(runtime, "runtime", {"max_results", "node_limits"})
        runtime.setdefault("max_results", 100)
        runtime_sources.setdefault("max_results", "core-default")
        positive(runtime["max_results"], "runtime.max_results")
        limits = object_at(runtime.setdefault("node_limits", {}), "runtime.node_limits", flat)
        for key, value in limits.items():
            positive(value, "runtime.node_limits." + key)
        graph = Graph(definition["component"]["id"], definition["component"]["version"], self._entry(tree), flat)
        graph_data = {"graph_id": graph.graph_id, "version": graph.version, "entry_node": graph.entry_node,
                      "nodes": {nid: {"node_id": nid, "input_contract": n.input_contract, "output_contract": n.output_contract,
                                     "outcomes": list(n.outcomes), "transitions": dict(n.transitions),
                                     "required_outputs_by_outcome": {o: list(p) for o, p in n.required_outputs_by_outcome.items()}} for nid, n in graph.nodes.items()}}
        used = {node["ref"] for node in self._walk(tree) if node["ref"] in self.library.components}
        snapshot = {"schema_version": 1, "purpose": "workflow-definition", "tree": tree, "graph": graph_data, "leaves": leaves,
                    "runtime": runtime, "model_profiles": profiles, "model_profile_provenance": profile_sources,
                    "runtime_provenance": runtime_sources, "contracts": copy.deepcopy(self.library.contracts),
                    "component_digests": {ref: digest(self.library.components[ref]) for ref in sorted(used)}}
        snapshot["digest"] = "workflow/v1:" + digest(snapshot)
        return ResolvedWorkflow(graph, canonical(snapshot))

    @staticmethod
    def _walk(node):
        yield node
        for child in node.get("children", {}).values():
            yield from WorkflowBuilder._walk(child)

    def _expand(self, definition, path, stack, source, instance=None, budget=None):
        budget = [0] if budget is None else budget
        budget[0] += 1
        if budget[0] > 2000:
            fail("Композиция превышает 2000 экземпляров", path)
        ref = definition["component"]["id"] + "@" + str(definition["component"]["version"])
        if ref in stack or len(stack) >= 20:
            fail("Рекурсивная композиция или глубина больше 20", path, "component_cycle")
        result = {"id": path or definition["component"]["id"], "ref": ref, "definition": copy.deepcopy(definition),
                  "inputs": {}, "transitions": {}, "provenance": trace(definition, "library:" + ref)}
        if instance is not None:
            object_at(instance, path, {"ref", "inputs", "transitions", "config", "execution"})
            result["inputs"] = copy.deepcopy(instance.get("inputs", {}))
            result["transitions"] = copy.deepcopy(instance.get("transitions", {}))
            for key in ("config", "execution"):
                if key in instance:
                    result["definition"][key] = merge(result["definition"].get(key, {}), object_at(instance[key], path + "." + key))
            result["provenance"].update(trace(instance, source))
        if definition["component"]["kind"] != "node":
            children = {}
            for name, spec in definition["nodes"].items():
                if not NAME.fullmatch(name) or name in {"succeeded", "failed", "cancelled"}:
                    fail("Неверное имя экземпляра", path + "." + name)
                object_at(spec, path + "." + name, {"ref", "inputs", "transitions", "config", "execution"})
                child = self.library.get(spec.get("ref"))
                if child["component"]["kind"] == "workflow":
                    fail("Workflow нельзя использовать как подграф", name)
                children[name] = self._expand(child, (path + "." if path else "") + name, stack + [ref], source, spec, budget)
            result["children"] = children
        return result

    def _overlay(self, tree, path, patch, source):
        object_at(patch, path, {"operation", "ref", "inputs", "transitions", "config", "execution"})
        parent = tree
        segments = path.split(".")
        for part in segments[:-1]:
            if part not in parent.get("children", {}):
                fail("Override ссылается на неизвестный экземпляр", path)
            parent = parent["children"][part]
        name = segments[-1]
        if name not in parent.get("children", {}):
            fail("Override ссылается на неизвестный экземпляр", path)
        old = parent["children"][name]
        operation = patch.get("operation")
        if operation == "replace":
            new_definition = self.library.get(patch.get("ref"))
            if new_definition["component"]["kind"] == "workflow":
                fail("Замена требует node или subgraph", path)
            for key in ("inputs", "outputs", "outcomes"):
                if new_definition.get(key, {}) != old["definition"].get(key, {}):
                    fail("Внешние контракты или outcomes замены несовместимы", path, "incompatible_replacement")
            spec = {"ref": patch["ref"], "inputs": old["inputs"], "transitions": old["transitions"]}
            spec.update({k: v for k, v in patch.items() if k not in {"operation", "ref"}})
            ancestor_refs = [tree["ref"]]
            cursor = tree
            for part in segments[:-1]:
                cursor = cursor["children"][part]
                ancestor_refs.append(cursor["ref"])
            new = self._expand(new_definition, old["id"], ancestor_refs, source, spec)
            new["provenance"].update({"ref": source})
            parent["children"][name] = new
        elif operation == "patch" and "ref" not in patch:
            for key in ("inputs", "transitions"):
                if key in patch:
                    old[key] = merge(old[key], object_at(patch[key], path + "." + key))
            for key in ("config", "execution"):
                if key in patch:
                    old["definition"][key] = merge(old["definition"].get(key, {}), object_at(patch[key], path + "." + key))
            old["provenance"].update(trace({k: v for k, v in patch.items() if k != "operation"}, source))
        else:
            fail("Нужна явная operation=patch или replace; ref разрешён только для replace", path)

    def _finalize(self, node, inherited, inherited_sources, profiles):
        definition, path = node["definition"], node["id"]
        params = {}
        schemas = object_at(definition.get("config_schema", {}), path + ".config_schema")
        for key, entry in schemas.items():
            if not NAME.fullmatch(key):
                fail("Неверное имя config параметра", path + ".config_schema")
            object_at(entry, path + ".config_schema." + key, {"schema", "default"})
            check_schema(entry.get("schema"), path + ".config_schema." + key)
            if "default" in entry:
                params[key] = copy.deepcopy(entry["default"])
                node["provenance"].setdefault("config." + key, "library:" + node["ref"])
        params.update(object_at(definition.get("config", {}), path + ".config", schemas))
        if set(params) != set(schemas):
            fail("Отсутствуют обязательные config параметры", path)
        for key, value in params.items():
            validate_value(value, schemas[key]["schema"], path + ".config." + key)
        node["config"] = params
        own = object_at(definition.get("execution", {}), path + ".execution", {"kind", "model_profile", "instruction", "skill", "capability"})
        effective = merge(inherited, own)
        sources = dict(inherited_sources)
        sources.update({key: node["provenance"].get("execution." + key, "library:" + node["ref"]) for key in own})
        if definition["component"]["kind"] == "node":
            kind = own.get("kind")
            if kind not in {"agent", "tool", "deterministic"}:
                fail("Узел требует execution.kind", path)
            # По дереву наследуется только профиль; instruction/capability не наследуются.
            effective = dict(own)
            if kind == "agent":
                effective.setdefault("model_profile", inherited.get("model_profile", "standard"))
                text(effective["model_profile"], path + ".execution.model_profile")
                if effective["model_profile"] not in profiles:
                    fail("Модельный профиль не связан с моделью", path, "unknown_model_profile")
                if not effective.get("instruction") and not effective.get("skill"):
                    fail("Agent узел требует instruction или skill", path)
                sources.setdefault("model_profile", "core-default")
            else:
                if "model_profile" in own:
                    fail("Детерминированный/tool узел не принимает model_profile", path)
                text(effective.get("capability"), path + ".capability")
                sources.pop("model_profile", None)
        for key, value in effective.items():
            text(value, path + ".execution." + key)
        node["execution"] = effective
        node["provenance"].update({"execution." + k: v for k, v in sources.items() if k in effective})
        for child in node.get("children", {}).values():
            self._finalize(child, {"model_profile": effective["model_profile"]} if "model_profile" in effective else {},
                           {"model_profile": node["provenance"].get("execution.model_profile", "core-default")} if "model_profile" in effective else {}, profiles)
        node["effects"] = dict(definition.get("effects", {}))
        if "children" in node:
            for child in node["children"].values():
                for key, value in child["effects"].items():
                    node["effects"][key] = node["effects"].get(key, False) or value
        definition["effects"] = dict(node["effects"])

    def _binding(self, graph, binding, location):
        text(binding, location)
        if binding.startswith("input:"):
            port = binding[6:]
            if port not in graph["definition"].get("inputs", {}):
                fail("Неизвестный вход графа", location)
            return graph["definition"]["inputs"][port], None
        parts = binding.split(".")
        if len(parts) != 2 or parts[0] not in graph["children"]:
            fail("Binding должен иметь вид input:port или instance.port", location)
        output = graph["children"][parts[0]]["definition"].get("outputs", {})
        if parts[1] not in output:
            fail("Неизвестный выходной порт", location)
        return output[parts[1]], binding

    def _check_graph(self, graph):
        if not graph.get("children"):
            return
        definition, nodes = graph["definition"], graph["children"]
        entry = definition["component"]["entry"]
        if entry not in nodes:
            fail("Entry ссылается на неизвестный узел", graph["id"])
        exits = object_at(definition["exits"], graph["id"] + ".exits", definition["outcomes"])
        if set(exits) != set(definition["outcomes"]):
            fail("Все outcomes графа требуют exit bindings", graph["id"])
        incoming = {n: [] for n in nodes}
        exit_edges = {o: [] for o in exits}
        for name, node in nodes.items():
            self._check_graph(node)
            d = node["definition"]
            inputs = object_at(node["inputs"], node["id"] + ".inputs", d.get("inputs", {}))
            if set(inputs) != set(d.get("inputs", {})):
                fail("Каждому входу нужен binding", node["id"])
            for port, binding in inputs.items():
                actual, _ = self._binding(graph, binding, node["id"] + ".inputs." + port)
                if actual != d["inputs"][port]:
                    fail("Несовместимые контракты портов", node["id"] + ".inputs." + port, "contract_mismatch")
            transitions = object_at(node["transitions"], node["id"] + ".transitions", d["outcomes"])
            if set(transitions) != set(d["outcomes"]):
                fail("Каждому outcome нужен переход", node["id"])
            for outcome, target in transitions.items():
                text(target, node["id"])
                if outcome in {"needs_input", "blocked"} and target != name:
                    fail("Wait outcome должен оставаться на текущем экземпляре", node["id"])
                if target.startswith("exit:") and target[5:] in exits:
                    exit_edges[target[5:]].append((name, outcome))
                elif target in nodes:
                    incoming[target].append((name, outcome))
                else:
                    fail("Неизвестная цель перехода", node["id"] + ".transitions." + outcome)
        reached = {entry}
        while True:
            new = reached | {t for name in reached for t in nodes[name]["transitions"].values() if t in nodes}
            if new == reached:
                break
            reached = new
        if reached != set(nodes):
            fail("Граф содержит недостижимые узлы", graph["id"])
        if any(not edges for edges in exit_edges.values()):
            fail("Объявлен недостижимый выход графа", graph["id"])
        all_ports = {n + "." + p for n, node in nodes.items() for p in node["definition"].get("outputs", {})}
        available = {n: (set() if n == entry else set(all_ports)) for n in nodes}
        def after(name, outcome):
            own_ports = {name + "." + p for p in nodes[name]["definition"].get("outputs", {})}
            return (available[name] - own_ports) | {name + "." + p for p in nodes[name]["definition"]["outcomes"][outcome]}
        # Пересечение гарантированных артефактов всех путей, включая первый вход
        # в цикл. Наличие порта в manifest не означает наличие его результата.
        while True:
            changed = False
            for name in nodes:
                candidates = [after(n, o) for n, o in incoming[name]]
                if name == entry:
                    candidates.append(set())
                value = set.intersection(*candidates) if candidates else set()
                if value != available[name]:
                    available[name] = value
                    changed = True
            if not changed:
                break
        for name, node in nodes.items():
            for port, binding in node["inputs"].items():
                _, token = self._binding(graph, binding, node["id"] + ".inputs." + port)
                if token is not None and token not in available[name]:
                    fail("Артефакт не гарантирован на каждом пути к узлу", node["id"] + ".inputs." + port, "unavailable_artifact")
        for outcome, bindings in exits.items():
            object_at(bindings, graph["id"] + ".exits." + outcome, definition.get("outputs", {}))
            if set(bindings) != set(definition["outcomes"][outcome]):
                fail("Exit должен явно вернуть обязательные порты исхода", graph["id"] + ".exits." + outcome)
            guaranteed = set.intersection(*(after(n, o) for n, o in exit_edges[outcome]))
            for port, binding in bindings.items():
                actual, token = self._binding(graph, binding, graph["id"] + ".exits." + outcome)
                if actual != definition["outputs"][port]:
                    fail("Несовместимый контракт выхода графа", graph["id"], "contract_mismatch")
                if token is not None and token not in guaranteed:
                    fail("Выходной артефакт не гарантирован", graph["id"], "unavailable_artifact")

    @staticmethod
    def _entry(node):
        return WorkflowBuilder._entry(node["children"][node["definition"]["component"]["entry"]]) if "children" in node else node["id"]

    def _compile(self, node, exit_targets, flat, leaves):
        if "children" not in node:
            definition = node["definition"]
            flat[node["id"]] = Node(node["id"], node["ref"] + ":inputs", node["ref"] + ":outputs",
                tuple(definition["outcomes"]), exit_targets, required_outputs_by_outcome=definition["outcomes"])
            leaves[node["id"]] = {"ref": node["ref"], "inputs": definition.get("inputs", {}), "outputs": definition.get("outputs", {}),
                                  "outcomes": definition["outcomes"], "bindings": node["inputs"], "execution": node["execution"], "config": node["config"]}
            return
        for child in node["children"].values():
            transitions = {}
            for outcome, target in child["transitions"].items():
                transitions[outcome] = exit_targets[target[5:]] if target.startswith("exit:") else self._entry(node["children"][target])
            self._compile(child, transitions, flat, leaves)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Проверка и экспорт workflow; не запускает действия")
    parser.add_argument("command", choices=["catalog", "validate", "export"])
    parser.add_argument("definition", nargs="?")
    parser.add_argument("--library", action="append", required=True)
    parser.add_argument("--overlay")
    parser.add_argument("--json", dest="json_path")
    parser.add_argument("--html", dest="html_path")
    args = parser.parse_args(argv)
    try:
        library = ComponentLibrary(args.library)
        if args.command == "catalog":
            result = {"components": library.catalog()}
        else:
            if not args.definition:
                fail("Нужен путь к определению")
            resolved = WorkflowBuilder(library).load(args.definition, overlay=args.overlay)
            result = {"digest": resolved.digest, "nodes": len(resolved.graph.nodes), "entry_node": resolved.graph.entry_node,
                      "purpose": "definition-only"}
            if args.command == "export":
                if not args.json_path and not args.html_path:
                    fail("Нужен --json или --html")
                outputs = [(args.json_path, json.dumps(resolved.to_dict(), ensure_ascii=False, indent=2))] if args.json_path else []
                if args.html_path:
                    from .workflow_viewer import render_workflow
                    outputs.append((args.html_path, render_workflow(resolved)))
                # Экспорт не затирает определение, overlay или файлы библиотеки.
                protected = {Path(args.definition).resolve()}
                if args.overlay:
                    protected.add(Path(args.overlay).resolve())
                targets = [Path(path).resolve() for path, _ in outputs]
                if len(set(targets)) != len(targets):
                    fail("JSON и HTML требуют разных выходных файлов")
                for target in targets:
                    if target in protected or any(target.is_relative_to(Path(root).resolve()) for root in args.library):
                        fail("Экспорт не может изменять входные файлы/библиотеку", str(target))
                for path, content in outputs:
                    target = Path(path).resolve()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
        return 0
    except WorkflowBuildError as exc:
        print(json.dumps({"ok": False, "error": exc.as_dict()}, ensure_ascii=False), file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": {"code": "io_error", "message": str(exc)}}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
