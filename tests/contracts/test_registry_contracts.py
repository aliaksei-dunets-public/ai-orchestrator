from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RegistryContractTests(unittest.TestCase):
    def test_registries_have_valid_shape_and_live_references(self) -> None:
        for path in sorted((ROOT / "registries").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertIsInstance(payload["entries"], list)
            identifiers: set[str] = set()
            for entry in payload["entries"]:
                self.assertRegex(entry["id"], r"^[a-z0-9][a-z0-9-]*$")
                self.assertNotIn(entry["id"], identifiers)
                identifiers.add(entry["id"])
                self.assertTrue((ROOT / entry["path"]).exists(), entry)

    def test_schemas_use_draft_2020_12(self) -> None:
        for path in sorted((ROOT / "config" / "schemas").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertTrue(re.match(r"https://", payload["$id"]))
