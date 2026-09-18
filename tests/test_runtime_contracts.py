from __future__ import annotations

import copy
import importlib.util
import unittest

import orchestrator
from orchestrator import Graph, Node, NodeResult, RuntimeError, WaitState, WorkflowRun, validate_node_result
from orchestrator import runtime_contracts


class RuntimeContractsTests(unittest.TestCase):
    def node(self, **options):
        return Node("work", "input/v1", "output/v1", ("success",), {"success": "succeeded"}, **options)

    def test_callback_api_removed_but_shared_exports_retained(self):
        for name in ("GraphRuntime", "PreparationWorkflow"):
            self.assertFalse(hasattr(orchestrator, name))
            self.assertNotIn(name, orchestrator.__all__)
        for name in ("workflow_runtime", "preparation_workflow"):
            self.assertIsNone(importlib.util.find_spec(f"orchestrator.{name}"))
        for name in ("Graph", "Node", "NodeResult", "WaitState", "WorkflowRun", "RuntimeError", "validate_node_result"):
            self.assertIs(getattr(orchestrator, name), getattr(runtime_contracts, name))

    def test_graph_loader_rejects_duplicates_malformed_nodes_and_unknown_targets(self):
        definition = {"graph_id": "g", "version": 1, "entry_node": "work", "nodes": [
            {"node_id": "work", "input_contract": "in/v1", "output_contract": "out/v1",
             "outcomes": ["success"], "transitions": {"success": "succeeded"}}]}
        variants = [copy.deepcopy(definition) for _ in range(5)]
        variants[0]["nodes"] *= 2
        variants[1]["nodes"] = {"work": "not-a-node"}
        variants[2]["nodes"][0]["transitions"]["success"] = "missing"
        variants[3]["version"] = True
        variants[4]["entry_node"] = "missing"
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(RuntimeError):
                Graph.from_dict(variant)
        self.assertEqual(Graph.from_dict(definition).nodes["work"].node_id, "work")

    def test_graph_and_transitions_are_detached_and_immutable(self):
        transitions = {"success": "succeeded"}
        node = Node("work", "in/v1", "out/v1", ("success",), transitions)
        nodes = {"work": node}
        graph = Graph("g", 1, "work", nodes)
        transitions["success"] = "failed"
        nodes.clear()
        self.assertEqual(graph.nodes["work"].transitions["success"], "succeeded")
        with self.assertRaises(TypeError):
            graph.nodes["new"] = node
        with self.assertRaises(TypeError):
            node.transitions["success"] = "failed"

    def test_node_requires_matching_outcomes_and_valid_required_outputs(self):
        for outcomes, transitions, required in ((None, {}, ()), (("success", "success"), {"success": "succeeded"}, ()),
                                                (("success",), {}, ()), (("success",), {"success": "succeeded"}, ("",))):
            with self.subTest(outcomes=outcomes), self.assertRaises(RuntimeError):
                Node("work", "in", "out", outcomes, transitions, required)

    def test_required_outputs_can_be_data_or_artifact_and_rejection_is_structured(self):
        node = self.node(required_outputs=("proof",))
        validate_node_result(node, NodeResult("work", "success", data={"proof": True}))
        artifact = {"ref": "A", "contract": "result/v1", "role": "proof", "sha256": "a" * 64, "value": {"ok": True}}
        validate_node_result(node, NodeResult("work", "success", artifacts={"proof": artifact}))
        for result, code in ((NodeResult("other", "success"), "node_mismatch"),
                             (NodeResult("work", "unknown"), "unknown_outcome"),
                             (NodeResult("work", "success"), "contract_violation"),
                             (NodeResult("work", "success", data=[]), "contract_violation")):
            with self.subTest(result=result), self.assertRaises(RuntimeError) as error:
                validate_node_result(node, result)
            self.assertEqual(error.exception.code, code)
            self.assertEqual(error.exception.as_dict()["code"], code)

    def test_artifact_shape_checks_preserve_repository_boundary(self):
        artifact = {"ref": "A", "contract": "result/v1", "role": "proof", "sha256": "a" * 64, "uri": "repository:A"}
        validate_node_result(self.node(), NodeResult("work", "success", artifacts={"proof": artifact}))
        variants = []
        for field, value in (("ref", ""), ("contract", None), ("role", 4), ("sha256", "fake"), ("uri", "")):
            variants.append({**artifact, field: value})
        variants.append({k: v for k, v in artifact.items() if k != "uri"})
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(RuntimeError):
                validate_node_result(self.node(), NodeResult("work", "success", artifacts={"proof": variant}))
        for key, value in (("", artifact), (42, artifact), ("proof", "not-a-mapping")):
            with self.assertRaises(RuntimeError):
                validate_node_result(self.node(), NodeResult("work", "success", artifacts={key: value}))

    def test_result_wait_and_base_snapshot_serialization_are_detached(self):
        wait = WaitState("w", "work", "user_input", question="Question", answer={"nested": [1]})
        result = NodeResult("work", "success", data={"nested": [1]})
        run = WorkflowRun("r", None, "g", 1, "request", "running", "work", {"nested": [1]},
                          results={"work": result.to_dict()}, wait=wait, last_result=result)
        snapshot = run.to_dict()
        snapshot["inputs"]["nested"].append(2)
        snapshot["wait"]["answer"]["nested"].append(2)
        snapshot["results"]["work"]["data"]["nested"].append(2)
        snapshot["last_result"]["data"]["nested"].append(2)
        self.assertEqual(run.inputs["nested"], [1])
        self.assertEqual(wait.answer["nested"], [1])
        self.assertEqual(result.data["nested"], [1])
        self.assertEqual(run.results["work"]["data"]["nested"], [1])
        self.assertNotIn("revision", run.to_dict())
        self.assertNotIn("history", run.to_dict())
