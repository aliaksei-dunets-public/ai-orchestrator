from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class TaskFinalizationContractTests(unittest.TestCase):
    def test_receipt_schema_is_closed_and_versioned(self) -> None:
        schema = json.loads(
            (ROOT / "config/schemas/task-finalization.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            schema["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertIn("receipt_hash", schema["required"])
        self.assertIn("ready_for_completion", schema["required"])

    def test_operational_receipts_are_ignored_without_hiding_canonical_stores(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".orchestrator/tasks/finalization/", ignore)
        self.assertNotIn("\n.orchestrator/\n", f"\n{ignore}\n")
        self.assertNotIn("\n.orchestrator/memory/\n", f"\n{ignore}\n")
        self.assertNotIn("\n.orchestrator/knowledge/\n", f"\n{ignore}\n")

    def test_registry_has_additive_closed_finalization_summary(self) -> None:
        schema = json.loads(
            (ROOT / "config/schemas/task-registry.schema.json").read_text(
                encoding="utf-8"
            )
        )
        task = schema["properties"]["tasks"]["items"]
        self.assertNotIn("finalization", task["required"])
        finalization = task["properties"]["finalization"]
        self.assertFalse(finalization["additionalProperties"])
        self.assertEqual(
            set(finalization["required"]),
            {"receipt_hash", "changed_paths_digest", "completed_at"},
        )


if __name__ == "__main__":
    unittest.main()
