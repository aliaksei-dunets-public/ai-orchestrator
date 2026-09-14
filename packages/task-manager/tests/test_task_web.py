from __future__ import annotations

import http.client
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from orchestrator_task_manager import TaskManagerService
from orchestrator_task_manager.task_web import make_handler, render_index, render_task


class TaskWebTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.service = TaskManagerService(Path(self.temporary.name))
        self.task = self.service.create_task(
            title="<script>alert(1)</script>", task_type="implementation",
            objective="Проверить <b>экранирование</b>", original_request="<img src=x onerror=alert(1)>",
            acceptance_criteria=["Не исполнять HTML"],
        )

    def test_help_uses_utf8_with_legacy_console_encoding(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252"
        result = subprocess.run(
            [sys.executable, "-m", "orchestrator_task_manager.task_web", "--help"],
            capture_output=True, text=True, encoding="utf-8", env=environment, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Локальный просмотр задач", result.stdout)

    def test_pages_escape_task_content_and_show_history(self) -> None:
        index = render_index(self.service)
        detail = render_task(self.service, self.task["id"])
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", index)
        self.assertNotIn("<script>alert(1)</script>", index)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", detail)
        self.assertIn("Задача создана", detail)

    def test_list_has_search_status_filter_and_pagination(self) -> None:
        for index in range(51):
            self.service.create_task(
                title=f"Задача {index}", task_type="analysis", objective="Проверить поиск",
                original_request="Запрос", acceptance_criteria=["Результат есть"],
            )
        first = render_index(self.service)
        second = render_index(self.service, page=2)
        self.assertIn("Следующая", first)
        self.assertIn("Предыдущая", second)
        self.assertIn("всего 52", first)
        self.assertIn("Задача 0", second)
        filtered = render_index(self.service, query="несуществующая")
        self.assertIn("нет задач", filtered)

    def test_http_is_local_read_only_and_rejects_bad_host(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.service))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
            connection.request("GET", "/", headers={"Host": f"127.0.0.1:{server.server_port}"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn("Content-Security-Policy", response.headers)
            response.read()
            connection.request("POST", "/", body=b"{}", headers={"Host": f"127.0.0.1:{server.server_port}"})
            response = connection.getresponse()
            self.assertEqual(response.status, 405)
            response.read()
            connection.request("GET", "/", headers={"Host": "attacker.example"})
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
            connection.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
