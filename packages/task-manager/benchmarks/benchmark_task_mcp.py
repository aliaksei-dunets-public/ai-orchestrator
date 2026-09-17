"""Измерить тёплый MCP task_get и startup initialize на временном проекте."""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()
    if args.count < 20:
        parser.error("count должен быть не менее 20")
    with tempfile.TemporaryDirectory() as directory:
        project = Path(directory)
        process = subprocess.Popen(
            [sys.executable, "-m", "orchestrator_task_manager.task_mcp", "--project", str(project)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1,
        )
        sequence = 0

        def request(method: str, params: dict | None = None) -> dict:
            nonlocal sequence
            sequence += 1
            message = {"jsonrpc": "2.0", "id": sequence, "method": method}
            if params is not None:
                message["params"] = params
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            process.stdin.flush()
            return json.loads(process.stdout.readline())

        startup_started = time.perf_counter()
        initialize = request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                             "clientInfo": {"name": "benchmark", "version": "1"}})
        startup_ms = (time.perf_counter() - startup_started) * 1000
        assert initialize["result"]["protocolVersion"] == "2025-11-25"
        assert process.stdin is not None
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        process.stdin.flush()
        created = request("tools/call", {"name": "task_create", "arguments": {
            "title": "Benchmark", "type": "analysis", "objective": "Measure", "original_request": "Measure",
            "acceptance_criteria": ["Measured"],
        }})
        task_id = created["result"]["structuredContent"]["id"]
        samples = []
        for _ in range(args.count):
            started = time.perf_counter()
            response = request("tools/call", {"name": "task_get", "arguments": {"task_id": task_id}})
            samples.append((time.perf_counter() - started) * 1000)
            assert response["result"]["isError"] is False
        process.stdin.close()
        process.wait(timeout=5)
        assert process.returncode == 0, process.stderr.read() if process.stderr else ""
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, int(len(ordered) * 0.95) - 1)
    print(json.dumps({
        "count": len(samples), "startup_initialize_ms": round(startup_ms, 3),
        "task_get_p50_ms": round(statistics.median(ordered), 3),
        "task_get_p95_ms": round(ordered[p95_index], 3),
        "task_get_min_ms": round(ordered[0], 3), "task_get_max_ms": round(ordered[-1], 3),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
