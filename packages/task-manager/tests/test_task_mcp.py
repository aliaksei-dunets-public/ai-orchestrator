from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from orchestrator_task_manager.task_mcp import TaskMCPServer


class MCPClient:
    def __init__(self, project: Path) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-m", "orchestrator_task_manager.task_mcp", "--project", str(project)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1,
        )
        self.sequence = 0
        self._request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                      "clientInfo": {"name": "task-manager-tests", "version": "1"}})
        self.notify("notifications/initialized")

    def _request(self, method: str, params: dict | None = None) -> dict:
        self.sequence += 1
        message = {"jsonrpc": "2.0", "id": self.sequence, "method": method}
        if params is not None:
            message["params"] = params
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        assert self.process.stdout is not None
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise AssertionError(f"MCP process ended: {stderr}")
        return json.loads(line)

    def notify(self, method: str, params: dict | None = None) -> None:
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def list_tools(self) -> dict:
        return self._request("tools/list", {})["result"]

    def call(self, name: str, arguments: dict) -> dict:
        response = self._request("tools/call", {"name": name, "arguments": arguments})
        self.assertNotIn("error", response)
        return response["result"]

    def value(self, name: str, arguments: dict) -> dict | list | str | None:
        result = self.call(name, arguments)
        self.assertFalse(result["isError"], result)
        payload = result["structuredContent"]
        if isinstance(payload, dict) and set(payload) == {"value"}:
            return payload["value"]
        return payload

    def error(self, name: str, arguments: dict) -> dict:
        result = self.call(name, arguments)
        self.assertTrue(result["isError"], result)
        return result["structuredContent"]["error"]

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
        self.process.wait(timeout=5)
        stderr = self.process.stderr.read() if self.process.stderr else ""
        stdout = self.process.stdout.read() if self.process.stdout else ""
        if self.process.stderr:
            self.process.stderr.close()
        if self.process.stdout:
            self.process.stdout.close()
        self.assertEqual(self.process.returncode, 0, stderr or stdout)

    # unittest assertions are injected by the test case for this small client.
    def assertEqual(self, *args, **kwargs):
        unittest.TestCase().assertEqual(*args, **kwargs)

    def assertFalse(self, *args, **kwargs):
        unittest.TestCase().assertFalse(*args, **kwargs)

    def assertTrue(self, *args, **kwargs):
        unittest.TestCase().assertTrue(*args, **kwargs)

    def assertNotIn(self, *args, **kwargs):
        unittest.TestCase().assertNotIn(*args, **kwargs)


class TaskMCPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.client = MCPClient(self.root)

    def tearDown(self) -> None:
        self.client.close()
        self.temporary.cleanup()

    def test_help_is_utf8_safe_on_legacy_windows_code_page(self) -> None:
        environment = dict(__import__("os").environ)
        environment["PYTHONIOENCODING"] = "cp1252"
        completed = subprocess.run(
            [sys.executable, "-m", "orchestrator_task_manager.task_mcp", "--help"],
            capture_output=True,
            env=environment,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", errors="replace"))
        self.assertIn("Task Manager MCP", completed.stdout.decode("utf-8"))

    def test_protocol_and_tool_catalog(self) -> None:
        tools = self.client.list_tools()["tools"]
        names = {tool["name"] for tool in tools}
        self.assertEqual(len(names), 35)
        self.assertIn("task_create", names)
        self.assertIn("task_accept", names)
        self.assertIn("task_archive", names)
        self.assertIn("task_health_check", names)
        create = next(tool for tool in tools if tool["name"] == "task_create")
        self.assertEqual(set(create["inputSchema"]["required"]), {
            "title", "type", "objective", "original_request", "acceptance_criteria",
        })
        self.assertTrue(create["annotations"]["destructiveHint"])
        health = next(tool for tool in tools if tool["name"] == "task_health_check")
        self.assertTrue(health["annotations"]["readOnlyHint"])

    def test_mcp_enforces_published_schema_without_coercion(self) -> None:
        response = self.client.call("task_create", {
            "title": "Невалидный вызов", "type": "analysis", "objective": "Проверка",
            "original_request": "Проверка", "acceptance_criteria": "не список",
        })
        self.assertTrue(response["isError"])
        self.assertEqual(response["structuredContent"]["error"]["code"], "validation_failed")
        self.assertEqual(self.client.value("task_list", {}), [])

    def test_structured_content_is_always_an_object(self) -> None:
        task = self.client.value("task_create", {
            "title": "Формат", "type": "analysis", "objective": "Проверка",
            "original_request": "Проверка", "acceptance_criteria": ["Есть объект"],
        })
        raw_list = self.client.call("task_list", {})
        raw_document = self.client.call("task_document", {"task_id": task["id"]})
        self.assertIsInstance(raw_list["structuredContent"], dict)
        self.assertEqual(set(raw_list["structuredContent"]), {"value"})
        self.assertIsInstance(raw_document["structuredContent"], dict)

    def test_lifecycle_requires_initialize_before_initialized_notification(self) -> None:
        server = TaskMCPServer(self.root)
        self.assertIsNone(server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        self.assertEqual(response["error"]["code"], -32002)
        self.assertIsNone(server.handle({"jsonrpc": "2.0", "method": "tools/call", "params": {
            "name": "task_create", "arguments": {"title": "x"}
        }}))
        initialized = server.handle({"jsonrpc": "2.0", "id": 2, "method": "initialize",
                                      "params": {"protocolVersion": "2026-07-28"}})
        self.assertEqual(initialized["result"]["protocolVersion"], "2026-07-28")
        self.assertIsNone(server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertIn("tools", server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}})["result"])

    def test_full_lifecycle_from_create_to_archive_and_structured_errors(self) -> None:
        task = self.client.value("task_create", {
            "title": "MCP задача", "type": "implementation", "objective": "Проверить MCP",
            "original_request": "Проверить полный lifecycle", "acceptance_criteria": ["MCP работает"],
        })
        self.assertEqual(task["status"], "created")
        task_id = task["id"]
        version = task["version"]
        self.assertEqual(self.client.value("task_get", {"task_id": task_id})["id"], task_id)
        self.assertEqual(len(self.client.value("task_history", {"task_id": task_id})), 1)

        self.client.value("task_start_preparation", {"task_id": task_id, "expected_version": version, "run_ref": "mcp-prep"})
        task = self.client.value("task_get", {"task_id": task_id})
        plan_folder = self.root / ".orchestrator/tasks" / task_id
        plan_folder.mkdir(parents=True)
        plan = plan_folder / "plan.md"
        plan.write_text("# MCP plan", encoding="utf-8")
        digest = hashlib.sha256(plan.read_bytes()).hexdigest()
        task = self.client.value("task_attach_artifact", {"task_id": task_id, "expected_version": task["version"],
            "role": "plan", "ref": "plan", "path": f".orchestrator/tasks/{task_id}/plan.md", "sha256": digest})
        task = self.client.value("task_attach_artifact", {"task_id": task_id, "expected_version": task["version"],
            "role": "plan_review", "ref": "review", "metadata": {"status": "approved", "plan_sha256": digest}})
        task = self.client.value("task_attach_execution_package", {"task_id": task_id, "expected_version": task["version"],
            "ref": "package", "plan_sha256": digest, "prepared_source_revision": "mcp-rev"})
        task = self.client.value("task_link_workflow_run", {"task_id": task_id, "expected_version": task["version"],
            "run_ref": "mcp-prep", "relation": "finished"})
        task = self.client.value("task_mark_ready", {"task_id": task_id, "expected_version": task["version"]})
        task = self.client.value("task_claim", {"task_id": task_id, "expected_version": task["version"],
            "worker_ref": "mcp-test", "lease_seconds": 60})
        claim = task["active_claim"]["ref"]
        task = self.client.value("task_renew_claim", {"task_id": task_id, "expected_version": task["version"],
            "claim_ref": claim, "lease_seconds": 60})
        task = self.client.value("task_attach_artifact", {"task_id": task_id, "expected_version": task["version"],
            "role": "readiness", "ref": "readiness", "metadata": {"status": "ready", "candidate_revision": "mcp-rev"}})
        task = self.client.value("task_attach_artifact", {"task_id": task_id, "expected_version": task["version"],
            "role": "acceptance_package", "ref": "acceptance"})
        task = self.client.value("task_mark_awaiting_acceptance", {"task_id": task_id, "expected_version": task["version"]})
        task = self.client.value("task_accept", {"task_id": task_id, "expected_version": task["version"],
            "candidate_revision": "mcp-rev", "completion_decision_ref": "mcp-accept", "operation_id": "mcp-accept-1"})
        self.assertEqual(task["status"], "completed")
        task = self.client.value("task_archive", {"task_id": task_id, "expected_version": task["version"], "reason": "Проверено"})
        self.assertIsNotNone(task["archive"])
        self.assertEqual(self.client.value("task_list", {}), [])
        archived = self.client.value("task_list", {"include_archived": True})
        self.assertEqual(len(archived), 1)
        self.assertEqual(self.client.value("task_health_check", {}), [])

        error = self.client.error("task_get", {"task_id": "TASK-9999"})
        self.assertEqual(error["code"], "task_not_found")
        stale = self.client.error("task_cancel", {"task_id": task_id, "expected_version": 1, "reason": "stale"})
        self.assertEqual(stale["code"], "task_version_conflict")

    def test_project_root_isolated_between_mcp_processes(self) -> None:
        other = Path(tempfile.mkdtemp(dir=self.root.parent))
        second = MCPClient(other)
        try:
            task = self.client.value("task_create", {
                "title": "Только проект A", "type": "analysis", "objective": "A", "original_request": "A",
                "acceptance_criteria": ["A"],
            })
            error = second.error("task_get", {"task_id": task["id"]})
            self.assertEqual(error["code"], "task_not_found")
        finally:
            second.close()
            other.joinpath(".orchestrator").exists() and __import__("shutil").rmtree(other / ".orchestrator", ignore_errors=True)
            other.rmdir()

    def test_transfer_paths_cannot_escape_fixed_project_root(self) -> None:
        outside = self.root.parent / "outside-task-manager-export.json"
        for name, arguments in (
            ("task_export", {"destination": str(outside)}),
            ("task_backup", {"destination": str(outside)}),
            ("task_restore", {"source": str(outside)}),
        ):
            with self.subTest(name=name):
                error = self.client.error(name, arguments)
                self.assertEqual(error["code"], "validation_failed")
        self.assertFalse(outside.exists())

    def test_restart_preserves_project_state(self) -> None:
        task = self.client.value("task_create", {
            "title": "Перезапуск MCP", "type": "analysis", "objective": "Проверить", "original_request": "Проверить",
            "acceptance_criteria": ["Состояние сохранено"],
        })
        self.client.close()
        self.client = MCPClient(self.root)
        restored = self.client.value("task_get", {"task_id": task["id"]})
        self.assertEqual(restored["title"], "Перезапуск MCP")
        self.assertEqual(self.client.value("task_health_check", {}), [])


if __name__ == "__main__":
    unittest.main()
