---
name: task-analyzer
description: Анализировать repository evidence для задачи, отделять симптом от причины, определять affected components, ограничения, риски и неизвестные. Использовать внутри standard/deep Task Creation Workflow до выбора подхода.
---

# Task Analyzer

1. Прочитать Project Context, profiles, код, тесты, ADR и связанные решения.
2. Отделить проверенные факты от гипотез.
3. Вернуть problem, current/expected behavior, affected components, constraints, risks и evidence paths.
4. Не выбирать реализацию и не менять Task Registry.
