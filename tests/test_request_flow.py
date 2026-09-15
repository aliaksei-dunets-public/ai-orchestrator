from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator import RequestFlow, RequestRouter, TaskCreator
from orchestrator_task_manager import TaskManagerService


class RequestFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = TaskManagerService(self.root)

    def test_direct_route_stops_before_task_creator(self) -> None:
        def unexpected_builder(*args):
            raise AssertionError("Task Creator не должен вызываться для direct_response")

        flow = RequestFlow(
            RequestRouter(lambda request, context: {
                "route": "direct_response", "suggested_type": None, "confidence": "high"
            }),
            TaskCreator(self.service, unexpected_builder),
        )
        result = flow.handle("Объясни разницу между REST и GraphQL")
        self.assertEqual(result.route.route, "direct_response")
        self.assertIsNone(result.creation)

    def test_managed_route_creates_task_via_public_service(self) -> None:
        def builder(request, task_type, context):
            return {
                "title": "Исправить расчёт",
                "objective": "Исправить сценарий X",
                "acceptance_criteria": ["X возвращает ожидаемое значение"],
                "constraints": ["Не менять публичный API"],
            }

        flow = RequestFlow(
            RequestRouter(lambda request, context: {
                "route": "managed_work", "suggested_type": "implementation", "confidence": "high"
            }),
            TaskCreator(self.service, builder),
        )
        result = flow.handle("Исправь расчёт X")
        self.assertEqual(result.creation.result, "success")
        self.assertEqual(result.creation.task["id"], "TASK-0001")
        self.assertEqual(result.creation.artifact, {"type": "task", "ref": "TASK-0001"})
        self.assertEqual(self.service.get_task("TASK-0001")["original_request"], "Исправь расчёт X")

    def test_missing_user_information_returns_needs_input_without_persisting(self) -> None:
        creator = TaskCreator(
            self.service,
            lambda request, task_type, context: {"open_questions": ["Какой endpoint затронут?"]},
        )
        result = creator.create("Исправь проблему", "investigation")
        self.assertEqual(result.result, "needs_input")
        self.assertEqual(result.questions, ("Какой endpoint затронут?",))
        self.assertEqual(self.service.list_tasks(), [])

    def test_invalid_router_result_is_rejected(self) -> None:
        router = RequestRouter(lambda request, context: {
            "route": "managed_work", "suggested_type": None, "confidence": "high"
        })
        with self.assertRaises(ValueError):
            router.route("Найди причину")

    def test_invalid_draft_is_failure(self) -> None:
        creator = TaskCreator(self.service, lambda request, task_type, context: {"title": "Без цели"})
        result = creator.create("Сделай что-нибудь", "exploration")
        self.assertEqual(result.result, "failure")
        self.assertEqual(result.error["code"], "invalid_draft")


if __name__ == "__main__":
    unittest.main()
