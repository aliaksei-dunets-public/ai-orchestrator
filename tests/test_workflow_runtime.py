from __future__ import annotations

import unittest

from orchestrator import Graph, GraphRuntime, Node, NodeResult, RuntimeError as WorkflowRuntimeError, WaitState


def build_graph() -> Graph:
    return Graph(
        graph_id="interactive-v1",
        version=1,
        entry_node="collect",
        nodes={
            "collect": Node("collect", "request/v1", "answer/v1", ("needs_input", "success"),
                             {"needs_input": "collect", "success": "finish"}),
            "finish": Node("finish", "answer/v1", "result/v1", ("success",), {"success": "succeeded"}),
        },
    )


class WorkflowRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = GraphRuntime()
        self.run = self.runtime.create_run(build_graph(), {"request": "Собери данные"}, run_id="RUN-1")

    def test_executes_one_node_per_step_and_reaches_terminal_state(self) -> None:
        calls: list[str] = []

        def executor(node, inputs, run):
            calls.append(node.node_id)
            return NodeResult(node.node_id, "success", data={"done": node.node_id})

        result = self.runtime.step(self.run.run_id, executor)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(calls, ["collect"])
        self.assertEqual(self.runtime.inspect_run("RUN-1").state, "running")
        result = self.runtime.step("RUN-1", executor)
        self.assertEqual(result.node_id, "finish")
        self.assertEqual(calls, ["collect", "finish"])
        self.assertEqual(self.runtime.inspect_run("RUN-1").state, "succeeded")
        with self.assertRaisesRegex(WorkflowRuntimeError, "текущем состоянии"):
            self.runtime.step("RUN-1", executor)

    def test_needs_input_pauses_same_node_and_resume_uses_answer(self) -> None:
        def executor(node, inputs, run):
            if run.wait is None:
                return NodeResult(node.node_id, "needs_input", wait=WaitState(
                    "WAIT-1", node.node_id, "user_input", question="Какой ответ?"
                ))
            return NodeResult(node.node_id, "success", data={"answer": run.wait.answer})

        wait = self.runtime.step("RUN-1", executor)
        self.assertIsInstance(wait, WaitState)
        self.assertEqual(wait.node_id, "collect")
        self.assertEqual(self.runtime.inspect_run("RUN-1").state, "waiting_input")
        with self.assertRaisesRegex(WorkflowRuntimeError, "Ожидание уже изменилось"):
            self.runtime.resume("RUN-1", "да", executor, wait_id="WAIT-old")
        result = self.runtime.resume("RUN-1", {"value": "да"}, executor, wait_id="WAIT-1", node_id="collect")
        self.assertEqual(result.outcome, "success")
        run = self.runtime.inspect_run("RUN-1")
        self.assertEqual(run.current_node, "finish")
        self.assertEqual(run.state, "running")
        self.assertEqual(run.results["collect"]["data"]["answer"], {"value": "да"})

    def test_blocked_run_does_not_advance_or_execute_again(self) -> None:
        graph = Graph("blocked-v1", 1, "block", {
            "block": Node("block", "in/v1", "out/v1", ("blocked", "success"),
                           {"blocked": "block", "success": "succeeded"}),
        })
        run = self.runtime.create_run(graph, {}, run_id="RUN-BLOCKED")
        result = self.runtime.step("RUN-BLOCKED", lambda node, inputs, current: NodeResult(
            node.node_id, "blocked", error={"reason": "access"}
        ))
        self.assertEqual(result.outcome, "blocked")
        self.assertEqual(self.runtime.inspect_run(run.run_id).state, "blocked")
        with self.assertRaisesRegex(WorkflowRuntimeError, "текущем состоянии"):
            self.runtime.step(run.run_id, lambda *_: result)
        resumed = self.runtime.resume_blocked(
            run.run_id,
            lambda node, inputs, current: NodeResult(node.node_id, "success", data={"unblocked": True}),
            wait_id=self.runtime.inspect_run(run.run_id).wait.wait_id,
        )
        self.assertEqual(resumed.outcome, "success")
        self.assertEqual(self.runtime.inspect_run(run.run_id).state, "succeeded")

    def test_contract_and_execution_errors_are_structured(self) -> None:
        with self.assertRaisesRegex(WorkflowRuntimeError, "неизвестный узел"):
            Graph("bad", 1, "start", {"start": Node("start", "in", "out", ("success",), {"success": "missing"})})
        with self.assertRaises(WorkflowRuntimeError) as caught:
            self.runtime.step("RUN-1", lambda node, inputs, run: NodeResult("other", "success"))
        self.assertEqual(caught.exception.code, "node_mismatch")
        self.assertEqual(self.runtime.inspect_run("RUN-1").state, "created")
        with self.assertRaises(WorkflowRuntimeError) as caught:
            self.runtime.step("RUN-1", lambda node, inputs, run: NodeResult(node.node_id, "unknown"))
        self.assertEqual(caught.exception.code, "unknown_outcome")
        with self.assertRaises(WorkflowRuntimeError) as caught:
            self.runtime.step("RUN-1", lambda node, inputs, run: (_ for _ in ()).throw(ValueError("boom")))
        self.assertEqual(caught.exception.code, "execution_failure")
        self.assertEqual(self.runtime.inspect_run("RUN-1").state, "failed")

    def test_cancel_and_run_isolation(self) -> None:
        second = self.runtime.create_run(build_graph(), {"request": "другая"}, run_id="RUN-2")
        cancelled = self.runtime.cancel("RUN-1", "Пользователь отменил запуск")
        self.assertEqual(cancelled.state, "cancelled")
        self.assertEqual(self.runtime.inspect_run(second.run_id).state, "created")
        with self.assertRaisesRegex(WorkflowRuntimeError, "не найден"):
            self.runtime.inspect_run("RUN-404")

    def test_dict_graph_is_loaded_and_snapshots_are_isolated(self) -> None:
        graph = {
            "graph_id": "dict-v1", "version": 1, "entry_node": "only",
            "nodes": [{"node_id": "only", "input_contract": "in", "output_contract": "out",
                        "outcomes": ["success"], "transitions": {"success": "succeeded"}}],
        }
        source = {"nested": {"value": 1}}
        run = self.runtime.create_run(graph, source, run_id="RUN-DICT")
        source["nested"]["value"] = 77
        self.assertEqual(self.runtime.inspect_run(run.run_id).inputs["nested"]["value"], 1)
        run.inputs["nested"]["value"] = 99
        self.assertEqual(self.runtime.inspect_run(run.run_id).inputs["nested"]["value"], 1)

    def test_resume_validation_is_atomic_and_can_be_retried(self) -> None:
        self.runtime.step("RUN-1", lambda node, inputs, run: NodeResult(
            node.node_id, "needs_input", wait=WaitState("WAIT-ATOMIC", node.node_id, "user_input")
        ))

        with self.assertRaises(WorkflowRuntimeError) as caught:
            self.runtime.resume("RUN-1", "bad", lambda node, inputs, run: NodeResult(node.node_id, "unknown"))
        self.assertEqual(caught.exception.code, "unknown_outcome")
        waiting = self.runtime.inspect_run("RUN-1")
        self.assertEqual(waiting.state, "waiting_input")
        self.assertEqual(waiting.wait.answer, None)

        result = self.runtime.resume(
            "RUN-1", "да", lambda node, inputs, run: NodeResult(
                node.node_id, "success", data={"answer": run.wait.answer}
            ), wait_id="WAIT-ATOMIC",
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.runtime.inspect_run("RUN-1").results["collect"]["data"]["answer"], "да")

    def test_returned_result_and_inputs_are_detached_from_runtime(self) -> None:
        payload = {"nested": {"value": 1}}
        result = self.runtime.step("RUN-1", lambda node, inputs, run: NodeResult(
            node.node_id, "success", data=payload
        ))
        payload["nested"]["value"] = 2
        result.data["nested"]["value"] = 3
        stored = self.runtime.inspect_run("RUN-1")
        self.assertEqual(stored.results["collect"]["data"]["nested"]["value"], 1)

    def test_graph_loader_rejects_duplicates_and_malformed_nodes(self) -> None:
        duplicate = {
            "graph_id": "duplicate-v1", "version": 1, "entry_node": "n",
            "nodes": [
                {"node_id": "n", "input_contract": "in", "output_contract": "out",
                 "outcomes": ["success"], "transitions": {"success": "succeeded"}},
                {"node_id": "n", "input_contract": "in", "output_contract": "out",
                 "outcomes": ["success"], "transitions": {"success": "succeeded"}},
            ],
        }
        with self.assertRaisesRegex(WorkflowRuntimeError, "уникальным"):
            Graph.from_dict(duplicate)
        with self.assertRaises(WorkflowRuntimeError) as caught:
            Graph.from_dict({"graph_id": "bad-v1", "version": 1, "entry_node": "n",
                             "nodes": {"n": "not-a-node"}})
        self.assertEqual(caught.exception.code, "contract_violation")
        with self.assertRaises(WorkflowRuntimeError) as caught:
            Node("bad", "in", "out", None, {})
        self.assertEqual(caught.exception.code, "contract_violation")

    def test_artifact_contract_is_structurally_validated(self) -> None:
        valid = {
            "ref": "ARTIFACT-1", "contract": "result/v1", "role": "result",
            "sha256": "a" * 64, "value": {"ok": True},
        }
        result = self.runtime.step("RUN-1", lambda node, inputs, run: NodeResult(
            node.node_id, "success", artifacts={"result": valid}
        ))
        self.assertEqual(result.outcome, "success")
        with self.assertRaises(WorkflowRuntimeError) as caught:
            self.runtime.create_run(build_graph(), {}, run_id="RUN-ARTIFACT-BAD").run_id
            self.runtime.step("RUN-ARTIFACT-BAD", lambda node, inputs, run: NodeResult(
                node.node_id, "success", artifacts={"result": {"ref": "missing"}}
            ))
        self.assertEqual(caught.exception.code, "contract_violation")


if __name__ == "__main__":
    unittest.main()
