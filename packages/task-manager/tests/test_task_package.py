from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TaskPackageTests(unittest.TestCase):
    def test_service_cli_and_web_import_without_orchestrator_core(self) -> None:
        source = Path(__file__).resolve().parents[1] / "src"
        script = (
            "import sys; from pathlib import Path; "
            f"sys.path.insert(0, {str(source)!r}); "
            "from orchestrator_task_manager import TaskManagerService; "
            "from orchestrator_task_manager.task_cli import main; "
            "from orchestrator_task_manager.task_web import render_index; "
            "service = TaskManagerService(Path('.')); "
            "task = service.create_task(title='T', task_type='analysis', objective='O', "
            "original_request='R', acceptance_criteria=['A']); "
            "assert service.get_task(task['id'])['status'] == 'created'; "
            "assert len(service.get_history(task['id'])) == 1; "
            "assert 'Реестр задач' in render_index(service); "
            "assert main(['--project', '.', 'validate']) == 0; "
            "assert 'orchestrator' not in sys.modules"
        )
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-S", "-c", script], cwd=directory,
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
