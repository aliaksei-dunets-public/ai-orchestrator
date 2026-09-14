from __future__ import annotations

import unittest

from orchestrator.security import (
    memory_knowledge_security_review,
    policy_allows_override,
    route_security_review,
    security_review,
)


class SecurityReviewScenarioTests(unittest.TestCase):
    def test_sensitive_diff_is_always_routed(self) -> None:
        route = route_security_review(["src/auth/token.py"], "+ safe_change = True")
        self.assertTrue(route.required)
        self.assertIn("sensitive path", route.reasons[0])

    def test_seeded_vulnerabilities_block_but_safe_control_does_not(self) -> None:
        vulnerable = security_review(["src/runner.py"], "+ result = eval(user_input)")
        safe = security_review(["src/math.py"], "+ result = parse_integer(user_input)")
        self.assertEqual(vulnerable.verdict, "blocked")
        self.assertEqual(vulnerable.findings[0].severity, "high")
        self.assertEqual(safe.verdict, "approved")

    def test_credentials_are_redacted(self) -> None:
        result = security_review(["src/config.py"], '+ api_key = "super-secret-value"')
        serialized = str(result.to_dict())
        self.assertEqual(result.verdict, "blocked")
        self.assertNotIn("super-secret-value", serialized)
        self.assertIn("REDACTED", serialized)

    def test_immutable_policy_has_no_local_override(self) -> None:
        self.assertFalse(policy_allows_override({"allow_local_bypass": False}))

    def test_memory_knowledge_boundary_blocks_escape_secret_and_unbounded_context(self) -> None:
        result = memory_knowledge_security_review(
            ".",
            source_paths=("../outside.md", ".orchestrator/memory/proposals/x.json"),
            content="api_key=super-secret",
            budget_chars=50000,
        )
        self.assertEqual(result.verdict, "blocked")
        codes = {item.code for item in result.findings}
        self.assertEqual(
            codes,
            {
                "SEC_CONTEXT_PATH_ESCAPE",
                "SEC_CONTEXT_EXCLUDED_SOURCE",
                "SEC_CONTEXT_CREDENTIAL",
                "SEC_CONTEXT_UNBOUNDED",
            },
        )
        self.assertNotIn("super-secret", str(result.to_dict()))
