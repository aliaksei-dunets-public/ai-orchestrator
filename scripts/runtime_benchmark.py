"""Измерение in-memory AgentGraphRuntime без внешних эффектов."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator import AgentGraphRuntime, Graph, Node, NodeResult


def measure(kind: str, count: int, size: int) -> dict:
    payload = ({"text": "x" * size} if kind == "string" else
               {"rows": [{"i": i, "text": "x" * 96} for i in range(math.ceil(size / 128))]})
    node = Node("work", "input/v1", "output/v1", ("success",), {"success": "work"})
    runtime = AgentGraphRuntime()
    run = runtime.create_run(Graph("benchmark", 1, "work", {"work": node}), {}, max_results=count)
    latencies = []
    tracemalloc.start()
    started = time.perf_counter()
    for _ in range(count):
        before = time.perf_counter()
        run = runtime.submit_result(run.run_id, NodeResult("work", "success", data=payload), expected_revision=run.revision)
        latencies.append((time.perf_counter() - before) * 1000)
    total = time.perf_counter() - started
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    before = time.perf_counter()
    snapshot = runtime.inspect_run(run.run_id)
    inspect_ms = (time.perf_counter() - before) * 1000
    assert len(snapshot.history) == count
    return {"kind": kind, "results": count, "payload_json_bytes": len(json.dumps(payload).encode()),
            "total_seconds": round(total, 4), "median_submit_ms": round(statistics.median(latencies), 3),
            "first_submit_ms": round(latencies[0], 3), "last_submit_ms": round(latencies[-1], 3),
            "inspect_ms_without_tracing": round(inspect_ms, 3),
            "retained_mib": round(current / 2**20, 3), "peak_mib": round(peak / 2**20, 3)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--counts", type=int, nargs="+", default=[10, 50, 100])
    parser.add_argument("--payload-size", type=int, default=32768)
    args = parser.parse_args()
    results = []
    for kind in ("string", "nested_json"):
        for count in args.counts:
            result = measure(kind, count, args.payload_size)
            results.append(result)
            print(json.dumps(result), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"python": sys.version, "tracemalloc": True, "results": results}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
