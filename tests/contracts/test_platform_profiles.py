from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.platforms import (
    PlatformProfileError,
    load_platform_profile,
    resolve_capability,
)


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ORDER = [
    "codex",
    "google-antigravity",
    "github-copilot-vscode",
    "claude-vscode",
]


class PlatformProfileContractTests(unittest.TestCase):
    def test_all_profiles_pass_same_contract_in_required_order(self) -> None:
        profiles = [
            load_platform_profile(path)
            for path in (ROOT / "profiles/platforms").glob("*.yaml")
        ]
        ordered = sorted(profiles, key=lambda item: item["adapter_order"])
        self.assertEqual([item["id"] for item in ordered], EXPECTED_ORDER)
        for profile in ordered:
            self.assertEqual(profile["validation"]["contract_matrix"], "passed")
            for pointer in profile["validation"]["evidence"]:
                relative = pointer.split("#", 1)[0]
                self.assertTrue((ROOT / relative).is_file(), pointer)
            for capability in (
                "shell",
                "virtual_uri",
                "review_isolation",
                "approval",
                "interaction",
            ):
                resolution = resolve_capability(profile, capability)
                self.assertIn(resolution.mode, {"native", "fallback", "blocked"})
                if resolution.mode != "blocked":
                    self.assertTrue(resolution.adapter)

    def test_maturity_matches_native_host_evidence(self) -> None:
        profiles = {
            name: load_platform_profile(
                ROOT / "profiles/platforms" / f"{name}.yaml"
            )
            for name in EXPECTED_ORDER
        }
        self.assertEqual(profiles["codex"]["maturity"], "stable")
        self.assertEqual(
            profiles["codex"]["validation"]["native_smoke"],
            "passed",
        )
        for name in EXPECTED_ORDER[1:]:
            self.assertEqual(profiles[name]["maturity"], "experimental")
            self.assertEqual(
                profiles[name]["validation"]["native_smoke"],
                "not_run",
            )

    def test_stable_profile_requires_native_smoke_evidence(self) -> None:
        profile_path = ROOT / "profiles/platforms/codex.yaml"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["validation"]["native_smoke"] = "not_run"
        with tempfile.TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "invalid-profile.json"
            invalid.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(
                PlatformProfileError,
                "stable platform requires",
            ):
                load_platform_profile(invalid)

    def test_undeclared_capability_is_blocked(self) -> None:
        profile = load_platform_profile(ROOT / "profiles/platforms/codex.yaml")
        resolution = resolve_capability(profile, "telepathy")
        self.assertEqual(resolution.mode, "blocked")
        self.assertIn("not declared", resolution.reason)

    def test_core_has_no_platform_name_branches(self) -> None:
        core = (ROOT / "orchestrator/platforms.py").read_text(encoding="utf-8")
        for platform in EXPECTED_ORDER:
            self.assertNotIn(f'== "{platform}"', core)
            self.assertNotIn(f"== '{platform}'", core)
