from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


TERM_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class OntologyError(ValueError):
    pass


@dataclass(frozen=True)
class Ontology:
    node_kinds: frozenset[str]
    relations: frozenset[str]
    core_node_kinds: frozenset[str]
    core_relations: frozenset[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "immutable": False,
            "node_kinds": sorted(self.node_kinds - self.core_node_kinds),
            "relations": sorted(self.relations - self.core_relations),
        }


def _terms(payload: Mapping[str, object], name: str) -> frozenset[str]:
    raw = payload.get(name, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise OntologyError(f"ontology {name} must be a list of strings")
    if len(raw) != len(set(raw)):
        raise OntologyError(f"ontology {name} contains duplicates")
    if any(not TERM_RE.fullmatch(item) for item in raw):
        raise OntologyError(f"invalid ontology term in {name}")
    return frozenset(raw)


def load_core_ontology(path: Path | str | None = None) -> Ontology:
    source = (
        Path(path)
        if path is not None
        else Path(__file__).resolve().parents[1] / "config" / "knowledge-ontology.json"
    )
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OntologyError(f"cannot load Core ontology: {exc}") from exc
    kinds = _terms(payload, "node_kinds")
    relations = _terms(payload, "relations")
    if payload.get("schema_version") != 1 or payload.get("immutable") is not True:
        raise OntologyError("Core ontology must be immutable schema version 1")
    return Ontology(kinds, relations, kinds, relations)


def load_project_ontology(path: Path | str) -> dict[str, object]:
    source = Path(path)
    if not source.exists():
        return {
            "schema_version": 1,
            "immutable": False,
            "node_kinds": [],
            "relations": [],
        }
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OntologyError(f"cannot load project ontology: {exc}") from exc
    if not isinstance(payload, dict):
        raise OntologyError("project ontology must be an object")
    return payload


def merge_ontology(core: Ontology, project: Mapping[str, object]) -> Ontology:
    if project.get("schema_version") != 1 or project.get("immutable") is not False:
        raise OntologyError("project ontology must be additive schema version 1")
    kinds = _terms(project, "node_kinds")
    relations = _terms(project, "relations")
    if kinds & core.core_node_kinds or relations & core.core_relations:
        raise OntologyError("project ontology cannot redefine Core terms")
    return Ontology(
        core.node_kinds | kinds,
        core.relations | relations,
        core.core_node_kinds,
        core.core_relations,
    )
