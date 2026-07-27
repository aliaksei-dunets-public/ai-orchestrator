from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.session_report import redact, render_session_report, write_session_report


ROOT = Path(__file__).resolve().parents[2]


class SessionReportTests(unittest.TestCase):
    def test_renders_non_empty_sections_deterministically(self) -> None:
        data = {
            "title": "Build session",
            "summary": "Completed the slice.",
            "changes": ["Added runtime"],
            "validation": ["unit tests passed"],
            "decisions": ["Use JSON"],
            "risks": ["Migration"],
            "next_actions": ["Implement phase 5"],
        }
        first = render_session_report(data)
        second = render_session_report(data)
        self.assertEqual(first, second)
        expected = (ROOT / "tests" / "fixtures" / "session-report.md").read_text(encoding="utf-8")
        self.assertEqual(first, expected)
        for heading in ("Changes", "Validation", "Decisions", "Risks", "Next actions"):
            self.assertIn(f"## {heading}", first)

    def test_redacts_common_credentials(self) -> None:
        content = render_session_report(
            {
                "changes": [
                    "api_key=abcdef",
                    "Authorization: Bearer abc.def.ghi",
                    "password: hunter2",
                    "sk-abcdefghijklmnopqrstuvwxyz",
                ]
            }
        )
        for secret in ("abcdef", "abc.def.ghi", "hunter2", "sk-abcdefghijklmnopqrstuvwxyz"):
            self.assertNotIn(secret, content)
        self.assertIn("[REDACTED]", content)

    def test_omits_empty_sections_and_writes_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "reports" / "session.md"
            write_session_report(path, {"changes": ["Изменение"], "risks": []})
            content = path.read_text(encoding="utf-8")
            self.assertIn("## Changes", content)
            self.assertNotIn("## Risks", content)

    def test_standalone_redaction(self) -> None:
        self.assertEqual(redact("refresh_token=secret"), "refresh_token=[REDACTED]")
