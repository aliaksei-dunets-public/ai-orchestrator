from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.documentation import (
    broken_local_links,
    documentation_impact,
    evaluate_documentation_gate,
    load_documentation_map,
)


ROOT = Path(__file__).resolve().parents[2]


class DocumentationTests(unittest.TestCase):
    def test_public_cli_change_requires_specification_and_migration(self) -> None:
        mapping = load_documentation_map(ROOT / "config/documentation-map.json")
        impacts = documentation_impact(["orchestrator/task_manager.py"], mapping)
        documents = {item.document for item in impacts}
        self.assertIn("docs/specifications/task-layer-specification-ru.md", documents)
        self.assertIn("docs/migrations/cli-contract.md", documents)

    def test_generated_and_hand_written_docs_have_owners(self) -> None:
        mapping = json.loads((ROOT / "config/documentation-map.json").read_text(encoding="utf-8"))
        self.assertTrue(all(rule.get("owner") for rule in mapping["rules"]))
        self.assertIn("generator", {rule["owner"] for rule in mapping["rules"]})
        self.assertIn("documentation-manager", {rule["owner"] for rule in mapping["rules"]})

    def test_broken_local_links_block_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = root / "README.md"
            document.write_text("[missing](docs/missing.md)\n", encoding="utf-8")
            self.assertEqual(broken_local_links(document, root=root), ["docs/missing.md"])
            (root / "docs").mkdir()
            (root / "docs/missing.md").write_text("ok", encoding="utf-8")
            self.assertEqual(broken_local_links(document, root=root), [])

    def test_task_storage_contract_documents_have_no_broken_links(self) -> None:
        documents = (
            "docs/specifications/orchestrator-specification-ru.md",
            "docs/specifications/task-layer-specification-ru.md",
            "docs/guides/deployment-to-target-project-ru.md",
            "docs/architecture/component-contracts.md",
            "docs/migrations/cli-contract.md",
            "docs/migrations/1.1.md",
            "docs/migrations/1.2.md",
            "docs/adr/0002-project-memory-knowledge-lifecycle.md",
            "docs/adr/0003-task-workspace-execution-modes.md",
            "docs/adr/0004-task-finalization-receipts.md",
            "docs/migrations/1.3-task-workspaces.md",
            "docs/migrations/1.4-task-finalization.md",
            "docs/plans/2026-07-28-task-storage-layout-design.md",
            "CHANGELOG.md",
        )
        for relative in documents:
            self.assertEqual(
                broken_local_links(ROOT / relative, root=ROOT),
                [],
                relative,
            )

    def test_memory_knowledge_runtime_changes_have_canonical_owners(self) -> None:
        mapping = load_documentation_map(ROOT / "config/documentation-map.json")
        impacts = documentation_impact(["orchestrator/retrieval.py"], mapping)
        documents = {item.document for item in impacts}
        self.assertIn("docs/specifications/orchestrator-specification-ru.md", documents)
        self.assertIn("docs/migrations/1.2.md", documents)

    def test_finalization_runtime_changes_have_canonical_owners(self) -> None:
        mapping = load_documentation_map(ROOT / "config/documentation-map.json")
        impacts = documentation_impact(["orchestrator/finalization.py"], mapping)
        documents = {item.document for item in impacts}
        self.assertIn("docs/adr/0004-task-finalization-receipts.md", documents)
        self.assertIn("docs/migrations/1.4-task-finalization.md", documents)
        self.assertIn("docs/guides/memory-and-knowledge-ru.md", documents)

    def test_documentation_gate_requires_update_or_explicit_non_applicability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir()
            (root / "docs").mkdir()
            (root / "docs/contract.md").write_text("# Contract\n", encoding="utf-8")
            (root / "config/documentation-map.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rules": [
                            {
                                "path_prefixes": ["src/"],
                                "documents": ["docs/contract.md"],
                                "owner": "documentation-manager",
                                "reason": "Contract changed.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "missing documentation disposition"):
                evaluate_documentation_gate(root, ["src/runtime.py"], [])
            with self.assertRaisesRegex(ValueError, "absent from changed paths"):
                evaluate_documentation_gate(
                    root,
                    ["src/runtime.py"],
                    [{"document": "docs/contract.md", "status": "updated"}],
                )
            evidence = evaluate_documentation_gate(
                root,
                ["src/runtime.py"],
                [
                    {
                        "document": "docs/contract.md",
                        "status": "not_applicable",
                        "reason": "Internal-only behavior.",
                    }
                ],
            )
            self.assertEqual(evidence[0].status, "not_applicable")
