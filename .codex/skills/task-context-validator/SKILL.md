---
name: task-context-validator
description: Валидировать quick, standard и deep Task Context перед регистрацией, включая frontmatter, обязательные разделы, критические вопросы и approval deep-подхода. Использовать непосредственно перед Task Manager registration.
---

# Task Context Validator

Использовать канонический contract из `skills/task-creator/references/task-context-contract.md` и script `skills/task-creator/scripts/validate_task_context.py`. Критический открытый вопрос или отсутствие deep approval возвращает blocked result; содержимое автоматически не исправлять.
