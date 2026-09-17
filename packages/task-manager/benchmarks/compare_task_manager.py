"""Парное сравнение с доверенной копией task_manager.py до рефакторинга."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sqlite3
import statistics
import sys
import tempfile
import time
from pathlib import Path

from orchestrator_task_manager import TaskManagerService


def aggregate(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {"p50_ms": round(statistics.median(values), 3),
            "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * .95))], 3)}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path,
                        help="Доверенный самостоятельный Python-модуль прежней реализации")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=30)
    args = parser.parse_args()
    if args.count < 1 or args.repeats < 1:
        parser.error("count и repeats должны быть положительными")
    spec = importlib.util.spec_from_file_location("task_manager_baseline", args.baseline)
    if spec is None or spec.loader is None:
        parser.error("baseline должен указывать на Python-модуль")
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    report = {"count": args.count, "repeats": args.repeats, "warmup": 3,
              "baseline_sha256": hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
              "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
              "platform": platform.platform(),
              "method": "Чередование AB/BA в одном процессе на одной временной базе",
              "cases": {}}
    with tempfile.TemporaryDirectory(prefix="task-manager-paired-") as directory:
        root = Path(directory)
        old = baseline.TaskManagerService(root)
        for index in range(args.count):
            old.create_task(title=f"T{index}", task_type="implementation", objective="O",
                            original_request="R", acceptance_criteria=["A"])
        new = TaskManagerService(root)
        cases = {
            "list_page": (lambda: old.list_tasks(limit=100), lambda: new.list_tasks(limit=100)),
            "list_all": (lambda: old.list_tasks(limit=None), lambda: new.list_tasks(limit=None)),
            "summary": (old.summary, new.summary),
            "health_check": (old.health_check, new.health_check),
            "export": (lambda: old.export_state(root / "export.json"),
                       lambda: new.export_state(root / "export.json")),
        }
        for name, callbacks in cases.items():
            for _ in range(3):
                for callback in callbacks:
                    callback()
            samples = [[], []]
            for repeat in range(args.repeats):
                for position in ((0, 1) if repeat % 2 == 0 else (1, 0)):
                    started = time.perf_counter()
                    callbacks[position]()
                    samples[position].append((time.perf_counter() - started) * 1000)
            report["cases"][name] = {"before": aggregate(samples[0]),
                                      "after": aggregate(samples[1])}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
