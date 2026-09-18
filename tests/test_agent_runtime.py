from __future__ import annotations

import copy
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from orchestrator import (
    AgentGraphRuntime, AgentWorkflowRun, Graph, Node, NodeResult,
    RuntimeError, WaitState, validate_node_result,
)
from orchestrator_task_manager import TaskError, TaskManagerService


def graph(*, loop: bool = False, required: tuple[str, ...] = ()) -> Graph:
    return Graph("agent-process-v1", 1, "work", {
        "work": Node("work", "input/v1", "result/v1",
                     ("success", "needs_input", "blocked", "failure"),
                     {"success": "work" if loop else "finish", "needs_input": "work",
                      "blocked": "work", "failure": "failed"}, required),
        "finish": Node("finish", "result/v1", "finish/v1", ("approved",), {"approved": "succeeded"}),
    })


class AgentRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = AgentGraphRuntime()
        self.run = self.runtime.create_run(graph(), {"request": "Проверить №1"}, run_id="RUN-AGENT")

    def submit(self, result: NodeResult):
        return self.runtime.submit_result(self.run.run_id, result, expected_revision=self.run.revision)

    def reject(self, code: str, call) -> None:
        before = self.runtime.inspect_run(self.run.run_id).to_dict()
        with self.assertRaises(RuntimeError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.runtime.inspect_run(self.run.run_id).to_dict(), before)

    def wait(self, *, blocker: bool = False, wait_id: str = "WAIT-1"):
        return self.submit(NodeResult(
            "work", "blocked" if blocker else "needs_input",
            wait=WaitState(wait_id, "work", "blocker" if blocker else "user_input",
                           question=None if blocker else "Какой вариант?",
                           reason="Нет доступа" if blocker else None),
        ))

    def test_explicit_progress_and_terminal_actions(self) -> None:
        self.assertIsInstance(self.run, AgentWorkflowRun)
        actions = self.runtime.available_actions(self.run.run_id)
        self.assertEqual(actions["revision"], 1)
        self.assertEqual(actions["actions"], ["submit_result", "cancel"])
        self.assertEqual(actions["node"]["transitions"]["success"], "finish")
        self.run = self.submit(NodeResult("work", "success", data={"evidence": ["src.py:1"]}))
        self.assertEqual((self.run.current_node, self.run.revision), ("finish", 2))
        self.run = self.submit(NodeResult("finish", "approved"))
        self.assertEqual((self.run.state, self.run.revision), ("succeeded", 3))
        self.assertEqual(self.runtime.available_actions(self.run.run_id)["actions"], [])
        self.assertEqual([e["revision"] for e in self.run.history], [2, 3])
        self.reject("invalid_state", lambda: self.submit(NodeResult("finish", "approved")))
        self.reject("invalid_state", lambda: self.runtime.cancel(self.run.run_id, "Поздно", expected_revision=3))
        self.assertFalse(hasattr(self.runtime, "step"))

    def test_stale_duplicate_and_malformed_results_are_atomic(self) -> None:
        self.reject("node_mismatch", lambda: self.submit(NodeResult("other", "success")))
        self.reject("unknown_outcome", lambda: self.submit(NodeResult("work", "teleport")))
        self.reject("contract_violation", lambda: self.submit({"node_id": "work"}))
        self.reject("contract_violation", lambda: self.submit(NodeResult("work", "success", data=[])))
        self.reject("contract_violation", lambda: self.submit(NodeResult("work", "success", artifacts={"x": {"ref": "x"}})))
        self.reject("contract_violation", lambda: self.submit(NodeResult("work", "success", wait=WaitState("X", "work", "user_input"))))
        self.run = self.submit(NodeResult("work", "success"))
        self.reject("run_revision_conflict", lambda: self.runtime.submit_result(self.run.run_id, NodeResult("work", "success"), expected_revision=1))
        for revision in (True, 0, -1, "2", None):
            with self.subTest(revision=revision):
                self.reject("contract_violation", lambda: self.runtime.submit_result(self.run.run_id, NodeResult("finish", "approved"), expected_revision=revision))

    def test_wait_answer_is_explicit_and_does_not_execute_node(self) -> None:
        self.run = self.wait()
        self.assertEqual(self.runtime.available_actions(self.run.run_id)["actions"], ["resume_wait", "cancel"])
        self.reject("invalid_state", lambda: self.submit(NodeResult("work", "success")))
        self.reject("stale_wait", lambda: self.runtime.resume_wait(self.run.run_id, expected_revision=2, wait_id="OLD", node_id="work", answer="Да"))
        self.reject("node_mismatch", lambda: self.runtime.resume_wait(self.run.run_id, expected_revision=2, wait_id="WAIT-1", node_id="finish", answer="Да"))
        self.reject("contract_violation", lambda: self.runtime.resume_wait(self.run.run_id, expected_revision=2, wait_id="WAIT-1", node_id="work"))
        answer = {"choice": ["A"]}
        self.run = self.runtime.resume_wait(self.run.run_id, expected_revision=2, wait_id="WAIT-1", node_id="work", answer=answer)
        answer["choice"].append("B")
        self.assertEqual((self.run.current_node, self.run.state, self.run.revision), ("work", "running", 3))
        self.assertEqual(self.run.resumed_wait["answer"], {"choice": ["A"]})
        self.assertEqual(self.run.last_result.outcome, "needs_input")
        self.assertEqual(self.run.result_counts, {"work": 1})
        self.reject("invalid_state", lambda: self.runtime.resume_wait(self.run.run_id, expected_revision=3, wait_id="WAIT-1", node_id="work", answer="Другой"))
        self.reject("unknown_outcome", lambda: self.submit(NodeResult("work", "bad")))
        self.assertIsNotNone(self.runtime.inspect_run(self.run.run_id).resumed_wait)
        self.run = self.submit(NodeResult("work", "success", data={"decision": "A"}))
        self.assertIsNone(self.run.resumed_wait)
        self.assertEqual(self.run.history[1]["wait"]["answer"], {"choice": ["A"]})

    def test_null_answer_is_valid_but_wrong_response_shape_is_not(self) -> None:
        self.run = self.wait()
        self.reject("contract_violation", lambda: self.runtime.resume_wait(self.run.run_id, expected_revision=2, wait_id="WAIT-1", node_id="work", answer=None, resolution="Лишнее"))
        self.run = self.runtime.resume_wait(self.run.run_id, expected_revision=2, wait_id="WAIT-1", node_id="work", answer=None)
        self.assertIsNone(self.run.resumed_wait["answer"])

    def test_blocker_requires_resolution_and_reused_wait_is_rejected(self) -> None:
        self.run = self.wait(blocker=True)
        self.reject("contract_violation", lambda: self.runtime.resume_wait(self.run.run_id, expected_revision=2, wait_id="WAIT-1", node_id="work", resolution=" "))
        self.reject("contract_violation", lambda: self.runtime.resume_wait(self.run.run_id, expected_revision=2, wait_id="WAIT-1", node_id="work", resolution="Готово", answer=None))
        self.run = self.runtime.resume_wait(self.run.run_id, expected_revision=2, wait_id="WAIT-1", node_id="work", resolution="Доступ восстановлен")
        self.assertEqual(self.run.resumed_wait["resolution"], "Доступ восстановлен")
        self.reject("stale_wait", lambda: self.wait(blocker=True))
        self.run = self.wait(blocker=True, wait_id="WAIT-2")
        self.reject("stale_wait", lambda: self.runtime.resume_wait(self.run.run_id, expected_revision=4, wait_id="WAIT-1", node_id="work", resolution="Старое"))

    def test_invalid_wait_never_changes_state(self) -> None:
        invalid = [None, "wait", WaitState("W", "other", "user_input", question="Q"),
                   WaitState("W", "work", "blocker", reason="R"),
                   WaitState("W", "work", "user_input", question=" "),
                   WaitState("W", "work", "user_input", question="Q", answer="Уже ответил")]
        for wait in invalid:
            with self.subTest(wait=wait):
                code = "node_mismatch" if isinstance(wait, WaitState) and wait.node_id == "other" else "contract_violation"
                self.reject(code, lambda: self.submit(NodeResult("work", "needs_input", wait=wait)))
        self.reject("contract_violation", lambda: self.submit(NodeResult("work", "blocked")))

    def test_per_node_and_global_budgets_are_enforced(self) -> None:
        for limits in ({"node_limits": {"work": 2}}, {"max_results": 2}):
            with self.subTest(limits=limits):
                self.runtime = AgentGraphRuntime()
                self.run = self.runtime.create_run(graph(loop=True), {}, **limits)
                self.run = self.submit(NodeResult("work", "success"))
                self.run = self.submit(NodeResult("work", "success"))
                self.assertEqual(self.runtime.available_actions(self.run.run_id)["remaining_results"], 0)
                self.assertEqual(self.runtime.available_actions(self.run.run_id)["actions"], ["cancel"])
                self.reject("result_limit_exceeded", lambda: self.submit(NodeResult("work", "success")))
                self.run = self.runtime.cancel(self.run.run_id, "Лимит", expected_revision=3)
                self.assertEqual(self.run.state, "cancelled")

    def test_waits_count_toward_budget_resume_does_not(self) -> None:
        self.runtime = AgentGraphRuntime()
        self.run = self.runtime.create_run(graph(loop=True), {}, max_results=1)
        self.run = self.wait()
        self.run = self.runtime.resume_wait(self.run.run_id, expected_revision=2, wait_id="WAIT-1", node_id="work", answer="A")
        self.assertEqual(self.run.result_counts, {"work": 1})
        self.reject("result_limit_exceeded", lambda: self.submit(NodeResult("work", "success")))

    def test_published_history_and_old_snapshots_remain_isolated_across_actions(self) -> None:
        runtime = AgentGraphRuntime()
        run = runtime.create_run(graph(loop=True), {"nested": {"items": [0]}})
        payload = {"nested": {"items": [1]}}
        first = runtime.submit_result(run.run_id, NodeResult("work", "success", data=payload), expected_revision=1)
        expected_first = first.to_dict()
        payload["nested"]["items"].append(99)
        second = runtime.submit_result(run.run_id, NodeResult("work", "success", data={"nested": {"items": [2]}}), expected_revision=2)
        self.assertEqual(first.to_dict(), expected_first)
        self.assertEqual(second.history[0]["result"]["data"]["nested"]["items"], [1])
        first.history[0]["result"]["data"]["nested"]["items"].append(99)
        second.inputs["nested"]["items"].append(99)
        second.results["work"]["data"]["nested"]["items"].append(99)
        second.history[0]["result"]["data"]["nested"]["items"].append(99)
        before = runtime.inspect_run(run.run_id).to_dict()
        with self.assertRaises(RuntimeError):
            runtime.submit_result(run.run_id, NodeResult("work", "unknown"), expected_revision=3)
        self.assertEqual(before, runtime.inspect_run(run.run_id).to_dict())
        original_copy = copy.deepcopy
        def fail_snapshot(value, *args, **kwargs):
            if isinstance(value, AgentWorkflowRun):
                raise MemoryError("injected public snapshot failure")
            return original_copy(value, *args, **kwargs)
        for action in (
            lambda: runtime.submit_result(run.run_id, NodeResult("work", "success", data={"new": [3]}), expected_revision=3),
            lambda: runtime.cancel(run.run_id, "Stop", expected_revision=3),
        ):
            with patch("orchestrator.agent_runtime.copy.deepcopy", side_effect=fail_snapshot), self.assertRaises(MemoryError):
                action()
            self.assertEqual(before, runtime.inspect_run(run.run_id).to_dict())
        cancelled = runtime.cancel(run.run_id, "Stop", expected_revision=3)
        self.assertEqual(cancelled.inputs["nested"]["items"], [0])
        self.assertEqual(cancelled.results["work"]["data"]["nested"]["items"], [2])
        self.assertEqual(cancelled.history[0]["result"]["data"]["nested"]["items"], [1])
        self.assertEqual(cancelled.history[-1]["reason"], "Stop")

    def test_json_and_snapshot_isolation(self) -> None:
        inputs = {"nested": {"items": [1]}}
        limits = {"work": 2}
        self.runtime = AgentGraphRuntime()
        self.run = self.runtime.create_run(graph(), inputs, node_limits=limits)
        inputs["nested"]["items"].append(2)
        limits["work"] = 9
        self.run.inputs["nested"]["items"].append(3)
        result = NodeResult("work", "success", data={"items": ["A"]})
        self.run = self.submit(result)
        result.data["items"].append("B")
        self.run.history[0]["result"]["data"]["items"].append("C")
        stored = self.runtime.inspect_run(self.run.run_id).to_dict()
        self.assertEqual(stored["inputs"], {"nested": {"items": [1]}})
        self.assertEqual(stored["results"]["work"]["data"], {"items": ["A"]})
        self.assertEqual(stored["node_limits"], {"work": 2})
        self.assertEqual(json.loads(json.dumps(stored, ensure_ascii=False, allow_nan=False)), stored)
        actions = self.runtime.available_actions(self.run.run_id)
        actions["node"]["transitions"]["approved"] = "bad"
        self.assertEqual(self.runtime.available_actions(self.run.run_id)["node"]["transitions"]["approved"], "succeeded")

    def test_non_json_values_are_rejected_atomically(self) -> None:
        cyclic: list = []
        cyclic.append(cyclic)
        for value in (float("nan"), float("inf"), object(), {1: "wrong-key"}, ("tuple",), cyclic):
            with self.subTest(value=type(value).__name__):
                self.reject("contract_violation", lambda: self.submit(NodeResult("work", "success", data={"value": value})))

    def test_creation_validation_and_dict_graph(self) -> None:
        for kwargs in ({"max_results": True}, {"max_results": 0}, {"node_limits": {"missing": 1}},
                       {"node_limits": {"work": False}}, {"node_limits": []}, {"phase": "bad"},
                       {"task_ref": "TASK-X"}, {"task_definition_version": 1}, {"run_id": ""}):
            with self.subTest(kwargs=kwargs), self.assertRaises(RuntimeError):
                self.runtime.create_run(graph(), {}, **kwargs)
        with self.assertRaises(RuntimeError):
            self.runtime.create_run(graph(), [], run_id="BAD")
        with self.assertRaises(RuntimeError):
            self.runtime.create_run(graph(), {}, run_id=self.run.run_id)
        raw = {"graph_id": "G", "version": 1, "entry_node": "N", "nodes": [{
            "node_id": "N", "input_contract": "I", "output_contract": "O", "outcomes": ["done"],
            "transitions": {"done": "succeeded"}}]}
        created = self.runtime.create_run(raw, {}, run_id="DICT")
        raw["nodes"][0]["transitions"]["done"] = "failed"
        self.assertEqual(self.runtime.submit_result(created.run_id, NodeResult("N", "done"), expected_revision=1).state, "succeeded")

    def test_required_outputs_and_shared_validator(self) -> None:
        self.runtime = AgentGraphRuntime()
        self.run = self.runtime.create_run(graph(required=("proof",)), {})
        self.reject("contract_violation", lambda: self.submit(NodeResult("work", "success")))
        validate_node_result(graph(required=("proof",)).nodes["work"], NodeResult("work", "success", data={"proof": "test"}))
        self.run = self.submit(NodeResult("work", "success", data={"proof": "test"}))
        self.assertEqual(self.run.current_node, "finish")

    def test_failure_cancel_and_missing_run(self) -> None:
        second = self.runtime.create_run(graph(), {}, run_id="SECOND")
        self.run = self.submit(NodeResult("work", "failure", error={"reason": "Test failure"}))
        self.assertEqual(self.run.state, "failed")
        cancelled = self.runtime.cancel(second.run_id, "Пользователь отменил", expected_revision=1)
        self.assertEqual((cancelled.state, cancelled.revision), ("cancelled", 2))
        self.assertEqual(self.runtime.inspect_run(self.run.run_id).state, "failed")
        with self.assertRaises(RuntimeError) as caught:
            self.runtime.inspect_run("MISSING")
        self.assertEqual(caught.exception.code, "run_not_found")

    def test_competing_results_only_one_is_committed(self) -> None:
        self.runtime = AgentGraphRuntime()
        self.run = self.runtime.create_run(graph(loop=True), {})
        barrier = threading.Barrier(2)

        def submit_once():
            barrier.wait(timeout=5)
            try:
                self.runtime.submit_result(self.run.run_id, NodeResult("work", "success"), expected_revision=1)
                return "accepted"
            except RuntimeError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: submit_once(), range(2)))
        self.assertCountEqual(outcomes, ["accepted", "run_revision_conflict"])
        run = self.runtime.inspect_run(self.run.run_id)
        self.assertEqual((run.revision, len(run.history), run.result_counts), (2, 1, {"work": 1}))

    def test_default_budget_bounds_a_cycle(self) -> None:
        self.runtime = AgentGraphRuntime()
        self.run = self.runtime.create_run(graph(loop=True), {})
        for _ in range(100):
            self.run = self.submit(NodeResult("work", "success"))
        self.assertEqual((self.run.revision, len(self.run.history)), (101, 100))
        self.reject("result_limit_exceeded", lambda: self.submit(NodeResult("work", "success")))

    def test_valid_artifact_is_isolated_and_hash_is_not_semantic_evidence(self) -> None:
        artifact = {"ref": "A", "role": "result", "contract": "result/v1", "sha256": "a" * 64, "value": {"ok": True}}
        self.run = self.submit(NodeResult("work", "success", artifacts={"proof": artifact}))
        artifact["value"]["ok"] = False
        self.assertTrue(self.runtime.inspect_run(self.run.run_id).results["work"]["artifacts"]["proof"]["value"]["ok"])
        # Generic runtime проверяет форму, но не объявляет verify repository реализованным.
        self.assertEqual(self.run.last_result.artifacts["proof"]["sha256"], "a" * 64)

    def test_all_mutations_require_revision_and_reserved_node_ids_are_rejected(self) -> None:
        self.run = self.wait()
        self.reject("run_revision_conflict", lambda: self.runtime.resume_wait(self.run.run_id, expected_revision=1, wait_id="WAIT-1", node_id="work", answer="A"))
        self.reject("run_revision_conflict", lambda: self.runtime.cancel(self.run.run_id, "Отмена", expected_revision=1))
        self.reject("contract_violation", lambda: self.runtime.cancel(self.run.run_id, " ", expected_revision=2))
        bad = Graph("reserved", 1, "succeeded", {"succeeded": Node("succeeded", "i", "o", ("done",), {"done": "succeeded"})})
        with self.assertRaises(RuntimeError) as caught:
            self.runtime.create_run(bad, {})
        self.assertEqual(caught.exception.code, "contract_violation")

    def test_task_definition_binding_and_task_lifecycle_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            service = TaskManagerService(Path(root))
            task = service.create_task(title="Задача", task_type="implementation", objective="Проверить",
                                       original_request="Проверить", acceptance_criteria=["Проверено"])
            self.runtime = AgentGraphRuntime()
            self.run = self.runtime.create_run(graph(), {}, task_ref=task["id"], task_definition_version=task["definition_version"], phase="execution")
            self.reject("stale_definition", lambda: self.submit(NodeResult("work", "success")))
            self.reject("contract_violation", lambda: self.runtime.submit_result(self.run.run_id, NodeResult("work", "success"), expected_revision=1, task_definition_version=True))
            refined = service.refine_task_definition(task["id"], task["version"], objective="Новая цель")
            self.reject("stale_definition", lambda: self.runtime.submit_result(self.run.run_id, NodeResult("work", "success"), expected_revision=1, task_definition_version=refined["definition_version"]))
            # Новый run привязан к прочитанному текущему definition; lifecycle не меняется.
            self.run = self.runtime.create_run(graph(), {}, task_ref=task["id"], task_definition_version=refined["definition_version"], phase="execution")
            for node_id, outcome in (("work", "success"), ("finish", "approved")):
                current = service.get_task(task["id"])
                self.run = self.runtime.submit_result(self.run.run_id, NodeResult(node_id, outcome), expected_revision=self.run.revision, task_definition_version=current["definition_version"])
            self.assertEqual(self.run.state, "succeeded")
            self.assertEqual(service.get_task(task["id"])["status"], "created")
            self.assertEqual(len(service.get_history(task["id"])), 2)
            with self.assertRaises(TaskError):
                service.mark_ready(task["id"], refined["version"])
            with self.assertRaises(TaskError):
                service.claim_task(task["id"], refined["version"], worker_ref="agent")
            self.assertEqual(service.health_check(), [])



if __name__ == "__main__":
    unittest.main()
