from __future__ import annotations

import unittest
from pathlib import Path

from orchestrator.platforms import load_platform_profile, resolve_capability


ROOT = Path(__file__).resolve().parents[2]


class PlatformAdapterScenarioTests(unittest.TestCase):
    def test_shell_no_shell_virtual_uri_and_sub_agent_cases(self) -> None:
        codex = load_platform_profile(ROOT / "profiles/platforms/codex.yaml")
        antigravity = load_platform_profile(ROOT / "profiles/platforms/google-antigravity.yaml")
        claude = load_platform_profile(ROOT / "profiles/platforms/claude-vscode.yaml")
        self.assertEqual(codex["maturity"], "stable")
        self.assertEqual(antigravity["maturity"], "experimental")
        self.assertEqual(claude["maturity"], "experimental")
        self.assertEqual(resolve_capability(codex, "shell").mode, "native")
        self.assertEqual(resolve_capability(antigravity, "virtual_uri").mode, "native")
        self.assertEqual(resolve_capability(claude, "virtual_uri").mode, "fallback")
        self.assertEqual(resolve_capability(codex, "review_isolation").adapter, "sub-agent")
        self.assertEqual(resolve_capability(claude, "review_isolation").adapter, "clean-context-review")


class GoogleAntigravityAdapterTests(unittest.TestCase):
    def test_antigravity_contract_before_later_adapters(self) -> None:
        profile = load_platform_profile(ROOT / "profiles/platforms/google-antigravity.yaml")
        self.assertEqual(profile["adapter_order"], 1)
        self.assertEqual(profile["maturity"], "experimental")
        self.assertEqual(resolve_capability(profile, "shell").mode, "native")
        self.assertEqual(resolve_capability(profile, "virtual_uri").mode, "native")
        self.assertEqual(resolve_capability(profile, "review_isolation").mode, "fallback")


class GitHubCopilotAdapterTests(unittest.TestCase):
    def test_copilot_contract_after_antigravity(self) -> None:
        profile = load_platform_profile(ROOT / "profiles/platforms/github-copilot-vscode.yaml")
        self.assertEqual(profile["adapter_order"], 2)
        self.assertEqual(profile["maturity"], "experimental")
        self.assertEqual(resolve_capability(profile, "shell").adapter, "vscode-terminal")
        self.assertEqual(resolve_capability(profile, "virtual_uri").adapter, "vscode-uri")
        self.assertEqual(resolve_capability(profile, "review_isolation").mode, "fallback")


class ClaudeAdapterTests(unittest.TestCase):
    def test_claude_contract_after_copilot(self) -> None:
        profile = load_platform_profile(ROOT / "profiles/platforms/claude-vscode.yaml")
        self.assertEqual(profile["adapter_order"], 3)
        self.assertEqual(profile["maturity"], "experimental")
        self.assertEqual(resolve_capability(profile, "shell").adapter, "vscode-terminal")
        self.assertEqual(resolve_capability(profile, "virtual_uri").mode, "fallback")
        self.assertEqual(resolve_capability(profile, "review_isolation").mode, "fallback")
