from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from orchestrator.onboarding_workflow import (
    OnboardingError,
    apply_onboarding,
    inspect_onboarding,
    plan_onboarding,
    rollback_onboarding,
)


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/system/project-onboarding/SKILL.md"


class AgentLedOnboardingScenarioTests(unittest.TestCase):
    def _python_project(self, root: Path) -> None:
        (root / "pyproject.toml").write_text(
            "[project]\nname='sample'\n",
            encoding="utf-8",
        )
        (root / "src").mkdir()
        (root / "src/app.py").write_text("print('ok')\n", encoding="utf-8")

    def test_inspect_returns_only_ambiguous_questions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self._python_project(target)
            result = inspect_onboarding(SKILL, target, {})
            self.assertEqual(result.status, "needs_input")
            self.assertEqual(
                {question.id for question in result.questions},
                {"platform_profile", "external_core_path"},
            )
            platform = next(
                item for item in result.questions if item.id == "platform_profile"
            )
            self.assertTrue(any(choice.recommended for choice in platform.choices))
            self.assertNotIn("technology_profiles", {q.id for q in result.questions})

    def test_existing_platform_instruction_selects_unambiguous_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self._python_project(target)
            (target / "AGENTS.md").write_text(
                "# Existing Codex instructions\n",
                encoding="utf-8",
            )
            result = inspect_onboarding(
                SKILL,
                target,
                {"external_core_path": "confirm"},
            )
            self.assertEqual(result.status, "ready")
            self.assertEqual(result.platform_profile, "codex")
            self.assertNotIn(
                "platform_profile",
                {question.id for question in result.questions},
            )

    def test_resolved_answers_produce_complete_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self._python_project(target)
            result = plan_onboarding(
                SKILL,
                target,
                {
                    "platform_profile": "codex",
                    "external_core_path": "confirm",
                },
            )
            self.assertEqual(result.status, "preview_ready")
            self.assertEqual(result.platform_profile, "codex")
            self.assertEqual(result.technology_profiles, ("python",))
            self.assertTrue(result.plan_hash)
            self.assertTrue(result.target_fingerprint)
            paths = {change.path for change in result.changes}
            self.assertIn(".orchestrator/config.json", paths)
            self.assertIn(".orchestrator/project-context.md", paths)
            self.assertIn(".orchestrator/memory/entries.jsonl", paths)
            self.assertIn(".orchestrator/memory/events.jsonl", paths)
            self.assertIn(".orchestrator/memory/approvals.jsonl", paths)
            self.assertIn(".orchestrator/knowledge/ontology.json", paths)
            self.assertIn(".orchestrator/knowledge/nodes.jsonl", paths)
            self.assertIn(".orchestrator/knowledge/edges.jsonl", paths)
            self.assertIn("AGENTS.md", paths)
            self.assertIn(".gitignore", paths)
            self.assertTrue(result.rollback_paths)
            self.assertIn("core-health", result.validation_steps)
            self.assertIn("idempotency", result.validation_steps)

    def test_apply_preserves_user_instructions_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self._python_project(target)
            original = "# Project rules\n\nKeep this content.\n"
            (target / "AGENTS.md").write_text(original, encoding="utf-8")
            answers = {
                "platform_profile": "codex",
                "external_core_path": "confirm",
            }
            preview = plan_onboarding(SKILL, target, answers)
            result = apply_onboarding(
                SKILL,
                target,
                answers,
                approved_plan_hash=preview.plan_hash,
            )
            self.assertEqual(result.status, "completed")
            instructions = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertTrue(instructions.startswith(original))
            self.assertIn("<!-- ai-orchestrator:start -->", instructions)
            gitignore = (target / ".gitignore").read_text(encoding="utf-8")
            self.assertIn(".orchestrator/tasks/checkpoints/", gitignore)
            self.assertIn(".orchestrator/memory/proposals/", gitignore)
            self.assertIn(".orchestrator/knowledge/indexes/", gitignore)
            self.assertIn(".orchestrator/migrations/backups/", gitignore)
            self.assertNotIn(".orchestrator/memory/entries.jsonl", gitignore)
            self.assertNotIn(".orchestrator/knowledge/nodes.jsonl", gitignore)
            self.assertNotIn(".orchestrator/tasks/*.lock", gitignore)
            second = plan_onboarding(SKILL, target, answers)
            self.assertEqual(second.status, "preview_ready")
            self.assertEqual(second.changes, ())

    def test_graph_proposal_is_previewed_applied_and_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self._python_project(target)
            answers = {
                "platform_profile": "codex",
                "external_core_path": "confirm",
                "knowledge_graph": {
                    "schema_version": 1,
                    "nodes": [
                        {
                            "id": "app-component",
                            "kind": "component",
                            "label": "Application",
                            "source": "src/app.py",
                        },
                        {
                            "id": "project-document",
                            "kind": "document",
                            "label": "Project metadata",
                            "source": "pyproject.toml",
                        },
                    ],
                    "edges": [
                        {
                            "id": "app-defined-by-project",
                            "source_node": "app-component",
                            "target_node": "project-document",
                            "relation": "defined_by",
                            "source": "pyproject.toml",
                        }
                    ],
                },
            }
            preview = plan_onboarding(SKILL, target, answers)
            self.assertEqual(preview.status, "preview_ready")
            node_change = next(
                item for item in preview.changes
                if item.path == ".orchestrator/knowledge/nodes.jsonl"
            )
            self.assertIn('"id":"app-component"', node_change.content)
            self.assertIn("knowledge-graph", preview.validation_steps)
            result = apply_onboarding(
                SKILL,
                target,
                answers,
                approved_plan_hash=preview.plan_hash,
            )
            self.assertEqual(result.status, "completed")
            self.assertIn(
                '"id":"app-component"',
                (target / ".orchestrator/knowledge/nodes.jsonl").read_text(encoding="utf-8"),
            )
            self.assertTrue(
                (target / ".orchestrator/knowledge/indexes/index.json").is_file()
            )
            self.assertEqual(plan_onboarding(SKILL, target, answers).changes, ())

    def test_graph_proposal_digest_is_rejected_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self._python_project(target)
            answers = {
                "platform_profile": "codex",
                "external_core_path": "confirm",
                "knowledge_graph": {
                    "schema_version": 1,
                    "nodes": [
                        {
                            "id": "app-component",
                            "kind": "component",
                            "label": "Application",
                            "source": "src/app.py",
                            "source_digest": "0" * 64,
                        }
                    ],
                    "edges": [],
                },
            }
            with self.assertRaisesRegex(OnboardingError, "source_digest"):
                plan_onboarding(SKILL, target, answers)
            self.assertFalse((target / ".orchestrator/config.json").exists())

    def test_stale_approval_is_rejected_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self._python_project(target)
            answers = {
                "platform_profile": "codex",
                "external_core_path": "confirm",
            }
            preview = plan_onboarding(SKILL, target, answers)
            (target / "AGENTS.md").write_text(
                "Changed after preview.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(OnboardingError, "stale"):
                apply_onboarding(
                    SKILL,
                    target,
                    answers,
                    approved_plan_hash=preview.plan_hash,
                )
            self.assertFalse((target / ".orchestrator/config.json").exists())

    def test_validation_error_triggers_verified_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self._python_project(target)
            original = "Original instructions.\n"
            (target / "AGENTS.md").write_text(original, encoding="utf-8")
            answers = {
                "platform_profile": "codex",
                "external_core_path": "confirm",
            }
            preview = plan_onboarding(SKILL, target, answers)
            result = apply_onboarding(
                SKILL,
                target,
                answers,
                approved_plan_hash=preview.plan_hash,
                validation_hook=lambda _core, _target, _plan: (
                    "ERROR forced validation failure",
                ),
            )
            self.assertEqual(result.status, "rolled_back")
            self.assertTrue(result.rollback_verified)
            self.assertEqual(
                (target / "AGENTS.md").read_text(encoding="utf-8"),
                original,
            )
            self.assertFalse((target / ".orchestrator/config.json").exists())

    def test_manual_rollback_refuses_to_overwrite_newer_user_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self._python_project(target)
            (target / "AGENTS.md").write_text(
                "Original instructions.\n",
                encoding="utf-8",
            )
            answers = {
                "platform_profile": "codex",
                "external_core_path": "confirm",
            }
            preview = plan_onboarding(SKILL, target, answers)
            result = apply_onboarding(
                SKILL,
                target,
                answers,
                approved_plan_hash=preview.plan_hash,
            )
            self.assertEqual(result.status, "completed")
            newer = "User change after onboarding.\n"
            (target / "AGENTS.md").write_text(newer, encoding="utf-8")
            with self.assertRaisesRegex(OnboardingError, "changed since"):
                rollback_onboarding(target)
            self.assertEqual(
                (target / "AGENTS.md").read_text(encoding="utf-8"),
                newer,
            )

    def test_cancel_before_preview_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self._python_project(target)
            result = inspect_onboarding(
                SKILL,
                target,
                {
                    "platform_profile": "codex",
                    "external_core_path": "cancel",
                },
            )
            self.assertEqual(result.status, "cancelled")
            self.assertFalse((target / ".orchestrator").exists())

    def test_agent_script_returns_machine_readable_questions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self._python_project(target)
            script = (
                ROOT
                / "skills/system/project-onboarding/scripts/onboard_project.py"
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "inspect",
                    "--target",
                    str(target),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "needs_input")
            self.assertTrue(payload["questions"])
