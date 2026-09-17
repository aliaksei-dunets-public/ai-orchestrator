from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator_onboarding import (
    OnboardingError,
    apply_plan,
    build_mcp_config,
    build_plan,
    check_task_manager,
)


ANSWERS = {
    "project_name": "Пример",
    "summary": "Тестовый проект.",
    "test_commands": ["python -m unittest"],
    "constraints": ["Не менять пользовательские файлы без согласования."],
}


class OnboardingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name)
        self.core = self.target / "tools/orchestrator"
        (self.core / "docs").mkdir(parents=True)
        (self.core / "README.md").write_text("# Core\n", encoding="utf-8")
        skill = self.core / ".agents/skills/orchestrator-task-manager/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# Skill\n", encoding="utf-8")
        task_manager = self.core / "packages/task-manager"
        (task_manager / "src/orchestrator_task_manager").mkdir(parents=True)
        (task_manager / "src/orchestrator_task_manager/task_mcp.py").write_text("# MCP\n", encoding="utf-8")
        (task_manager / "pyproject.toml").write_text(
            "[project.scripts]\n"
            "orchestrator-task-manager-mcp = \"orchestrator_task_manager.task_mcp:main\"\n",
            encoding="utf-8",
        )

    def test_missing_task_skill_blocks_external_preview(self) -> None:
        (self.core / ".agents/skills/orchestrator-task-manager/SKILL.md").unlink()
        with self.assertRaisesRegex(OnboardingError, "отсутствует skill"):
            build_plan(self.target, self.core, ANSWERS)

    def test_missing_task_manager_mcp_blocks_external_preview(self) -> None:
        (self.core / "packages/task-manager/pyproject.toml").unlink()
        with self.assertRaisesRegex(OnboardingError, "отсутствует MCP Task Manager"):
            build_plan(self.target, self.core, ANSWERS)

    def test_external_project_preview_apply_and_repeat(self) -> None:
        (self.target / "AGENTS.md").write_text("# Правила пользователя\n", encoding="utf-8")
        (self.target / ".gitignore").write_text("build/\n", encoding="utf-8")
        plan = build_plan(self.target, self.core, ANSWERS)
        self.assertEqual(len(plan["changes"]), 4)
        self.assertFalse((self.target / ".orchestrator").exists())
        written = apply_plan(plan, plan["plan_hash"])
        self.assertEqual(len(written), 4)
        self.assertIn("# Правила пользователя", (self.target / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("tools/orchestrator/docs/README.md", (self.target / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("tools/orchestrator/.agents/skills/orchestrator-task-manager/SKILL.md", (self.target / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertNotIn("orchestrator-onboarding", (self.target / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("build/", (self.target / ".gitignore").read_text(encoding="utf-8"))
        self.assertIn(".orchestrator/state/", (self.target / ".gitignore").read_text(encoding="utf-8"))
        self.assertIn("# orchestrator:begin", (self.target / ".gitignore").read_text(encoding="utf-8"))
        self.assertNotIn("<!-- orchestrator:begin -->", (self.target / ".gitignore").read_text(encoding="utf-8"))
        self.assertEqual(build_plan(self.target, self.core, ANSWERS)["changes"], [])

    def test_self_hosted_does_not_copy_core_or_modify_existing_agents(self) -> None:
        (self.target / "README.md").write_text("# Core\n", encoding="utf-8")
        (self.target / "docs").mkdir()
        task_manager = self.target / "packages/task-manager"
        (task_manager / "src/orchestrator_task_manager").mkdir(parents=True)
        (task_manager / "src/orchestrator_task_manager/task_mcp.py").write_text("# MCP\n", encoding="utf-8")
        (task_manager / "pyproject.toml").write_text(
            "[project.scripts]\n"
            "orchestrator-task-manager-mcp = \"orchestrator_task_manager.task_mcp:main\"\n",
            encoding="utf-8",
        )
        (self.target / "AGENTS.md").write_text("# Пользовательские инструкции\n", encoding="utf-8")
        (self.target / ".gitignore").write_text(".orchestrator/state/\n", encoding="utf-8")
        plan = build_plan(self.target, self.target, ANSWERS)
        self.assertEqual({change["path"] for change in plan["changes"]}, {
            ".orchestrator/project.json", ".orchestrator/project-context.md"
        })
        apply_plan(plan, plan["plan_hash"])
        config = json.loads((self.target / ".orchestrator/project.json").read_text(encoding="utf-8"))
        self.assertEqual(config["mode"], "self-hosted")
        self.assertEqual(config["core_path"], ".")
        self.assertEqual((self.target / "AGENTS.md").read_text(encoding="utf-8"), "# Пользовательские инструкции\n")

    def test_stale_file_blocks_all_writes(self) -> None:
        (self.target / "AGENTS.md").write_text("Old\n", encoding="utf-8")
        plan = build_plan(self.target, self.core, ANSWERS)
        (self.target / "AGENTS.md").write_text("Changed\n", encoding="utf-8")
        with self.assertRaisesRegex(OnboardingError, "изменился после preview"):
            apply_plan(plan, plan["plan_hash"])
        self.assertFalse((self.target / ".orchestrator").exists())
        self.assertEqual((self.target / "AGENTS.md").read_text(encoding="utf-8"), "Changed\n")

    def test_wrong_approval_hash_blocks_writes(self) -> None:
        plan = build_plan(self.target, self.core, ANSWERS)
        with self.assertRaisesRegex(OnboardingError, "Хеш плана"):
            apply_plan(plan, "incorrect")
        self.assertFalse((self.target / ".orchestrator").exists())

    def test_core_change_after_preview_blocks_all_writes(self) -> None:
        plan = build_plan(self.target, self.core, ANSWERS)
        (self.core / "README.md").write_text("# Updated core\n", encoding="utf-8")
        with self.assertRaisesRegex(OnboardingError, "Содержимое ядра изменилось"):
            apply_plan(plan, plan["plan_hash"])
        self.assertFalse((self.target / ".orchestrator").exists())

    def test_old_plan_schema_is_rejected(self) -> None:
        plan = build_plan(self.target, self.core, ANSWERS)
        plan["schema_version"] = 1
        with self.assertRaisesRegex(OnboardingError, "Неизвестная версия плана"):
            apply_plan(plan, plan["plan_hash"])

    def test_preview_cli_prints_russian_with_legacy_console_encoding(self) -> None:
        answers = self.target / "answers.json"
        answers.write_text(json.dumps(ANSWERS, ensure_ascii=False), encoding="utf-8")
        output = self.target / "plan.json"
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252"
        script = Path(__file__).resolve().parents[1] / "src/orchestrator_onboarding/onboarding.py"
        result = subprocess.run(
            [
                sys.executable, str(script), "preview", "--target", str(self.target),
                "--core", str(self.core), "--answers", str(answers), "--output", str(output),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("План:", result.stdout)
        self.assertTrue(output.is_file())

    def test_existing_project_context_is_not_overwritten(self) -> None:
        context = self.target / ".orchestrator/project-context.md"
        context.parent.mkdir()
        context.write_text("Пользовательский контекст", encoding="utf-8")
        with self.assertRaisesRegex(OnboardingError, "Уже существует"):
            build_plan(self.target, self.core, ANSWERS)
        self.assertEqual(context.read_text(encoding="utf-8"), "Пользовательский контекст")

    def test_invalid_managed_markers_block_preview(self) -> None:
        (self.target / "AGENTS.md").write_text(
            "<!-- orchestrator:end -->\n<!-- orchestrator:begin -->\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(OnboardingError, "маркеры"):
            build_plan(self.target, self.core, ANSWERS)

    def test_external_core_path_is_rejected(self) -> None:
        separate = tempfile.TemporaryDirectory()
        self.addCleanup(separate.cleanup)
        other = Path(separate.name)
        (other / "README.md").write_text("# Core\n", encoding="utf-8")
        (other / "docs").mkdir()
        with self.assertRaisesRegex(OnboardingError, "внутри целевого проекта"):
            build_plan(self.target, other, ANSWERS)

    def test_broad_ignore_rule_blocks_preview(self) -> None:
        (self.target / ".gitignore").write_text(".orchestrator/\n", encoding="utf-8")
        with self.assertRaisesRegex(OnboardingError, "скрывает версионируемую конфигурацию"):
            build_plan(self.target, self.core, ANSWERS)

    def test_legacy_gitignore_markers_are_migrated(self) -> None:
        (self.target / ".gitignore").write_text(
            "<!-- orchestrator:begin -->\n.orchestrator/state/\n<!-- orchestrator:end -->\n",
            encoding="utf-8",
        )
        plan = build_plan(self.target, self.core, ANSWERS)
        change = next(item for item in plan["changes"] if item["path"] == ".gitignore")
        self.assertIn("# orchestrator:begin", change["content"])
        self.assertNotIn("<!-- orchestrator:begin -->", change["content"])
        apply_plan(plan, plan["plan_hash"])
        content = (self.target / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("# orchestrator:begin", content)

    def test_symlinked_output_is_rejected(self) -> None:
        outside = self.target.parent / "outside-onboarding-test"
        try:
            (self.target / ".orchestrator").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Символические ссылки недоступны")
        with self.assertRaises(OnboardingError):
            build_plan(self.target, self.core, ANSWERS)

    def test_write_failure_restores_previous_files(self) -> None:
        (self.target / "AGENTS.md").write_text("Original\n", encoding="utf-8")
        plan = build_plan(self.target, self.core, ANSWERS)
        from orchestrator_onboarding import onboarding

        real_write = onboarding._atomic_write
        calls = 0

        def fail_once(path: Path, data: bytes) -> None:
            nonlocal calls
            calls += 1
            if calls == 4:
                raise OSError("simulated failure")
            real_write(path, data)

        with patch.object(onboarding, "_atomic_write", side_effect=fail_once):
            with self.assertRaisesRegex(OnboardingError, "восстановлены"):
                apply_plan(plan, plan["plan_hash"])
        self.assertEqual((self.target / "AGENTS.md").read_text(encoding="utf-8"), "Original\n")
        self.assertFalse((self.target / ".orchestrator/project.json").exists())
        self.assertFalse((self.target / ".orchestrator/project-context.md").exists())

    def test_mcp_config_uses_selected_python_and_absolute_project(self) -> None:
        config = build_mcp_config(self.target, Path(sys.executable), name="project-tasks")
        self.assertEqual(config["project-tasks"]["command"], str(Path(sys.executable).resolve()))
        self.assertEqual(config["project-tasks"]["args"][-1], str(self.target.resolve()))

    def test_mcp_config_rejects_output_outside_project(self) -> None:
        with self.assertRaisesRegex(OnboardingError, "внутри целевого проекта"):
            from orchestrator_onboarding import onboarding

            onboarding._safe_output_path(self.target, self.target.parent / "outside.json")

    def test_task_manager_mcp_check_runs_real_handshake(self) -> None:
        report = check_task_manager(self.target, Path(sys.executable))
        self.assertTrue(report["ok"])
        self.assertEqual(report["health_check"], [])
        self.assertGreaterEqual(report["tool_count"], 35)


if __name__ == "__main__":
    unittest.main()
