"""Демонстрационный JSON host. Это fixture, не LLM и не провайдер API."""
import argparse
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--project", type=Path, required=True)
args = parser.parse_args()
value = json.load(sys.stdin.buffer)
if value["operation"] == "probe":
    profile = value["profile"]
    response = {"available": profile["provider"] == "local-fixture" and profile["model"] == "fixture-v1",
                "provider": profile["provider"], "model": profile["model"]}
else:
    request = value["request"]
    node = request["node_id"].rsplit(".", 1)[-1]
    inputs = request["inputs"]
    if node == "scope":
        result = {"outcome": "success", "outputs": {"scope": {"checks": ["arithmetic"]}}}
    elif node == "summary":
        record = inputs["execution_record"]
        status = "failed" if record["failed"] else "passed"
        result = {"outcome": status, "outputs": {"result": {"status": status,
            "summary": "Результат реального локального unittest", "evidence_refs": record["evidence_refs"]}}}
    elif node == "impact":
        targets = inputs["project_profile"]["documentation_targets"]
        result = {"outcome": "assessed", "outputs": {"impact": {"impacted": bool(targets), "targets": targets}}}
    elif node == "update":
        impact = inputs["impact"]
        references = []
        root = args.project.resolve()
        for name in impact["targets"]:
            path = (root / name).resolve()
            if not path.is_relative_to(root) or Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("Демонстрационный target должен оставаться внутри project")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Локальный workflow\n\nUnittest пройден; описание сохранено Documentation-подграфом.\n",
                            encoding="utf-8")
            references.append(str(path))
        status = "success" if impact["impacted"] else "no_change"
        result = {"outcome": status, "outputs": {"result": {"status": status,
            "summary": "Демонстрационная документация обновлена" if references else "Документация без изменений",
            "evidence_refs": references or inputs["testing_result"]["evidence_refs"]}}}
    else:
        raise ValueError("Неизвестный fixture node")
    selected = request["selected_executor"]
    response = {"provider": selected["provider"], "model": selected["model"], "result": result}
sys.stdout.buffer.write(json.dumps(response, ensure_ascii=False).encode("utf-8") + b"\n")
