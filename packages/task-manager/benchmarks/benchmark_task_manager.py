"""Воспроизводимые замеры на временных проектах без изменения рабочей базы."""
from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import statistics
import sys
import tempfile
import time
from pathlib import Path

from orchestrator_task_manager import TaskManagerService
from orchestrator_task_manager.service import _sha256


def measure(callback, repeats: int) -> dict:
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        callback()
        samples.append((time.perf_counter() - started) * 1000)
    ordered = sorted(samples)
    return {"p50_ms": round(statistics.median(samples), 3),
            "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * .95))], 3)}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", type=int, nargs="+", default=[100, 500, 1000])
    parser.add_argument("--repeats", type=int, default=20)
    args = parser.parse_args()
    if args.repeats < 1 or any(count < 1 for count in args.counts):
        parser.error("counts и repeats должны быть положительными")
    report = {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
              "platform": platform.platform(), "repeats": args.repeats,
              "workload": "неархивные created-задачи, одно событие на задачу; новый процесс, повторные чтения",
              "projects": [], "sha256": {}}
    for count in args.counts:
        with tempfile.TemporaryDirectory(prefix="task-manager-bench-") as directory:
            service = TaskManagerService(Path(directory))
            create_samples = []
            started = time.perf_counter()
            for index in range(count):
                tick = time.perf_counter()
                service.create_task(title=f"Задача {index}", task_type="implementation",
                                    objective="Проверить производительность", original_request="Замер",
                                    acceptance_criteria=["Результат измерен"])
                create_samples.append((time.perf_counter() - tick) * 1000)
            row = {"count": count, "create_total_ms": round((time.perf_counter() - started) * 1000, 3),
                   "create_p50_ms": round(statistics.median(create_samples), 3),
                   "create_p95_ms": round(sorted(create_samples)[min(count - 1, int(count * .95))], 3)}
            row["list_page"] = measure(lambda: service.list_tasks(limit=100), args.repeats)
            row["list_all"] = measure(lambda: service.list_tasks(limit=None), args.repeats)
            row["health_check"] = measure(service.health_check, args.repeats)
            row["export"] = measure(lambda: service.export_state(Path(directory) / "export.json"), args.repeats)
            if hasattr(service, "summary"):
                row["summary"] = measure(service.summary, args.repeats)
            row["database_bytes"] = service.repository.path.stat().st_size
            report["projects"].append(row)
    with tempfile.TemporaryDirectory(prefix="task-manager-hash-") as directory:
        path = Path(directory) / "artifact.bin"
        for size in (1024, 1024 ** 2, 100 * 1024 ** 2):
            with path.open("wb") as stream:
                remaining = size
                chunk = b"x" * min(size, 1024 ** 2)
                while remaining:
                    stream.write(chunk[:remaining])
                    remaining -= min(remaining, len(chunk))
            report["sha256"][str(size)] = measure(lambda: _sha256(path), min(args.repeats, 5))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
