from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "skills" / "task-creator" / "scripts" / "validate_task_context.py"
SPEC = importlib.util.spec_from_file_location("canonical_task_context_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load task context validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


QUICK = """---
schema_version: 1
id: null
title: Quick context
type: feature
mode: quick
risk: low
created_by: task-creation-workflow
---
# Quick context
## Исходный запрос
Create it.
## Цель
Produce a valid draft.
## Объём задачи
Bounded.
### Входит в scope
- Draft.
### Не входит в scope
- Execution.
## Критерии приёмки
- Validator passes.
## План реализации
- Create and validate.
## Открытые вопросы
- Нет.
"""


class TaskContextContractTests(unittest.TestCase):
    def test_quick_draft_without_allocated_id_passes(self) -> None:
        self.assertEqual(VALIDATOR.validate_text(QUICK, "draft"), [])

    def test_fake_draft_id_fails(self) -> None:
        errors = VALIDATOR.validate_text(QUICK.replace("id: null", "id: TASK-9999"), "draft")
        self.assertTrue(any("draft context" in error for error in errors))

    def test_critical_open_question_fails(self) -> None:
        invalid = QUICK.replace("- Нет.", "- CRITICAL: choose destructive migration.")
        errors = VALIDATOR.validate_text(invalid, "draft")
        self.assertTrue(any("critical open question" in error for error in errors))
