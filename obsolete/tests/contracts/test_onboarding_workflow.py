from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.onboarding_workflow import inspect_onboarding
from orchestrator.platforms import load_platform_profile


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = (
    "project-config.schema.json",
    "onboarding-interaction.schema.json",
    "onboarding-session.schema.json",
)


class OnboardingWorkflowContractTests(unittest.TestCase):
    def test_workflow_is_registered_and_references_agent_steps(self) -> None:
        registry = json.loads(
            (ROOT / "registries/workflows.json").read_text(encoding="utf-8")
        )
        entry = next(
            item
            for item in registry["entries"]
            if item["id"] == "project-onboarding"
        )
        self.assertTrue(entry["enabled"])
        workflow = (ROOT / entry["path"]).read_text(encoding="utf-8")
        for step in (
            "discover-core",
            "inspect-target",
            "prepare-preview",
            "request-approval",
            "apply-project-integration",
            "validate-health",
            "validate-idempotency",
            "finalize-report",
        ):
            self.assertIn(f"id: {step}", workflow)
        self.assertIn("on_failure: rollback", workflow)

    def test_onboarding_schemas_use_json_schema_2020_12(self) -> None:
        for name in SCHEMAS:
            payload = json.loads(
                (ROOT / "config/schemas" / name).read_text(encoding="utf-8")
            )
            self.assertEqual(
                payload["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
                name,
            )
            self.assertEqual(payload["type"], "object", name)
            self.assertFalse(payload["additionalProperties"], name)

    def test_inspect_payload_matches_declared_interaction_surface(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "config/schemas/onboarding-interaction.schema.json"
            ).read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temporary:
            payload = inspect_onboarding(
                ROOT / "skills/system/project-onboarding/SKILL.md",
                temporary,
                {},
            ).to_dict()
        self.assertEqual(set(payload), set(schema["required"]))
        self.assertLessEqual(set(payload), set(schema["properties"]))
        self.assertEqual(payload["status"], "needs_input")
        self.assertTrue(payload["questions"])

    def test_platform_profiles_declare_onboarding_adapters(self) -> None:
        for path in sorted((ROOT / "profiles/platforms").glob("*.yaml")):
            profile = load_platform_profile(path)
            onboarding = profile["onboarding"]
            self.assertIn("instruction_target", onboarding)
            self.assertTrue(onboarding["skill_projection_target"])
            self.assertTrue(onboarding["interaction_adapter"])
            self.assertTrue(onboarding["approval_adapter"])
            self.assertNotEqual(
                onboarding["skill_projection_target"],
                onboarding["instruction_target"],
            )
            interaction = profile["capabilities"]["interaction"]
            self.assertIn(interaction["mode"], {"native", "fallback"})
