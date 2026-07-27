from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.telemetry import (
    JsonlTelemetrySink,
    RunTelemetry,
    TelemetryError,
    TelemetryEvent,
    TokenUsage,
    load_events,
    summarize_events,
)

ROOT = Path(__file__).resolve().parents[2]


class TelemetryTests(unittest.TestCase):
    def test_jsonl_sink_and_summary_use_numeric_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            sink = JsonlTelemetrySink(path)
            sink.emit(
                TelemetryEvent(
                    event="run_completed",
                    run_id="TASK-0001:abc",
                    status="completed",
                    metrics=RunTelemetry(
                        duration_ms=25,
                        attempts=2,
                        retries=1,
                        tool_calls=3,
                        agent_handoffs=1,
                        usage=TokenUsage(total_tokens=120, tool_result_tokens=20),
                    ),
                    recorded_at="2026-07-28T00:00:00+00:00",
                )
            )
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("evidence", raw)
            payload = json.loads(raw)
            self.assertEqual(payload["schema_version"], 1)
            summary = summarize_events(load_events(path))
            self.assertEqual(summary["runs"], 1)
            self.assertEqual(summary["retries"], 1)
            self.assertEqual(summary["usage"]["total_tokens"], 120)

    def test_missing_log_is_empty_and_invalid_counters_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            events = load_events(Path(temporary) / "missing.jsonl")
            self.assertEqual(events, ())
            self.assertIsNone(summarize_events(events)["usage"]["total_tokens"])
        with self.assertRaises(TelemetryError):
            TokenUsage(total_tokens=-1)
        with self.assertRaises(TelemetryError):
            RunTelemetry(tool_calls=-1)

    def test_loaded_events_reject_unknown_fields_and_negative_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            payload = TelemetryEvent(
                event="run_completed",
                run_id="TASK-0001:abc",
                status="completed",
                metrics=RunTelemetry(),
            ).to_dict()
            payload["unexpected"] = "payload"
            path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(TelemetryError, "unknown"):
                load_events(path)

            payload.pop("unexpected")
            payload["metrics"]["usage"]["total_tokens"] = -1
            path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(TelemetryError, "counters"):
                load_events(path)

    def test_schema_matches_payload_free_runtime_contract(self) -> None:
        schema = json.loads(
            (ROOT / "config/schemas/telemetry-event.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["properties"]["metrics"]["properties"]["usage"]["properties"]),
            {
                "static_prompt_tokens",
                "dynamic_context_tokens",
                "retrieved_context_tokens",
                "tool_result_tokens",
                "subagent_input_tokens",
                "subagent_output_tokens",
                "final_output_tokens",
                "total_tokens",
            },
        )
        rendered = json.dumps(schema)
        self.assertNotIn('"prompt"', rendered)
        self.assertNotIn('"evidence"', rendered)
