from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from orchestrator.telemetry import JsonlTelemetrySink, RunTelemetry, TelemetryEvent, TokenUsage


ROOT = Path(__file__).resolve().parents[2]


class TelemetryCliScenarioTests(unittest.TestCase):
    def test_json_summary_reports_available_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            JsonlTelemetrySink(path).emit(
                TelemetryEvent(
                    event="run_completed",
                    run_id="TASK-0001:abc",
                    status="completed",
                    metrics=RunTelemetry(
                        attempts=1,
                        tool_calls=2,
                        usage=TokenUsage(total_tokens=42),
                    ),
                )
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "orchestrator",
                    "telemetry",
                    "--path",
                    str(path),
                    "--json",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["runs"], 1)
            self.assertEqual(payload["tool_calls"], 2)
            self.assertEqual(payload["usage"]["total_tokens"], 42)

    def test_missing_log_has_zero_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "orchestrator",
                    "telemetry",
                    "--path",
                    str(Path(temporary) / "missing.jsonl"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("runs=0", completed.stdout)
            self.assertIn("reported_total_tokens=unknown", completed.stdout)

    def test_invalid_jsonl_fails_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            path.write_text("{not-json}\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "orchestrator",
                    "telemetry",
                    "--path",
                    str(path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("TELEMETRY_ERROR", completed.stdout)
            self.assertNotIn("Traceback", completed.stderr)
