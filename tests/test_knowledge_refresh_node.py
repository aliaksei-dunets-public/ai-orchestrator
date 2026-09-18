from __future__ import annotations

import unittest
from types import SimpleNamespace

from orchestrator import (GraphStatus, KnowledgeRefreshNode, KnowledgeRefreshPolicy,
                          KnowledgeRefreshRequest, KnowledgeRefreshResult)
from orchestrator.knowledge_contracts import KnowledgeError


class FakeKnowledgeService:
    def __init__(self, refresh_result, *, state="fresh", graph_version="v1", digest="a" * 64):
        self.refresh_result = refresh_result
        self.full_calls = 0
        self.incremental_calls = []
        self._status = GraphStatus(state, {"digest": digest}, {"digest": digest},
                                   {"version": graph_version}, {"package": "graphifyy"})
        self._snapshot = SimpleNamespace(digest=digest)

    def status(self):
        return self._status

    def snapshot(self):
        return self._snapshot

    def refresh(self, **kwargs):
        self.full_calls += 1
        return self.refresh_result

    def refresh_incremental(self, *, allow_full_fallback=True):
        self.incremental_calls.append(allow_full_fallback)
        return self.refresh_result


class KnowledgeRefreshNodeTests(unittest.TestCase):
    def result(self, status="indexed", mode="incremental"):
        return KnowledgeRefreshResult(status, {"digest": "a" * 64}, {"version": "v2"},
                                      2, 1, mode=mode, details={"changed": []})

    def test_automatic_requires_trusted_node(self):
        with self.assertRaises(KnowledgeError):
            KnowledgeRefreshPolicy(mode="full", authorization="automatic")

    def test_graph_declares_all_outcomes_and_confirmation_wait(self):
        service = FakeKnowledgeService(self.result())
        node = KnowledgeRefreshNode(service)
        self.assertEqual(node.graph.nodes["knowledge_refresh"].output_contract, "knowledge-refresh-node/v1")
        result = node.execute(KnowledgeRefreshRequest(
            policy=KnowledgeRefreshPolicy(mode="full", authorization="required")))
        self.assertEqual(result.outcome, "awaiting_confirmation")
        self.assertFalse(result.data["result"]["commit_allowed"])
        self.assertIsNotNone(result.wait)

    def test_auto_never_allows_full_fallback(self):
        service = FakeKnowledgeService(KnowledgeRefreshResult("fallback_required", None, None,
            error={"code": "fallback_required"}, mode="incremental"), state="missing")
        result = KnowledgeRefreshNode(service).execute(KnowledgeRefreshRequest())
        self.assertEqual(result.outcome, "fallback_required")
        self.assertFalse(result.data["result"]["commit_allowed"])
        self.assertEqual(service.incremental_calls, [False])
        self.assertEqual(service.full_calls, 0)

    def test_incremental_success_allows_fresh_candidate(self):
        service = FakeKnowledgeService(self.result())
        result = KnowledgeRefreshNode(service).execute(KnowledgeRefreshRequest(
            policy=KnowledgeRefreshPolicy(mode="incremental")))
        self.assertEqual(result.outcome, "success")
        self.assertTrue(result.data["result"]["commit_allowed"])
        self.assertEqual(service.incremental_calls, [False])

    def test_automatic_full_requires_explicit_trusted_policy(self):
        service = FakeKnowledgeService(self.result(mode="full-rebuild"))
        result = KnowledgeRefreshNode(service).execute(KnowledgeRefreshRequest(
            policy=KnowledgeRefreshPolicy(mode="full", authorization="automatic", trusted=True),
            explicit_decision_ref="graph-policy:maintenance"))
        self.assertEqual(result.outcome, "success")
        self.assertTrue(result.data["result"]["commit_allowed"])
        self.assertEqual(service.full_calls, 1)

    def test_failed_refresh_with_stale_graph_denies_commit(self):
        service = FakeKnowledgeService(KnowledgeRefreshResult("failed", None, None,
            error={"code": "provider_timeout"}, mode="incremental"), state="stale")
        result = KnowledgeRefreshNode(service).execute(KnowledgeRefreshRequest())
        self.assertEqual(result.outcome, "stale")
        self.assertFalse(result.data["result"]["commit_allowed"])


if __name__ == "__main__":
    unittest.main()
