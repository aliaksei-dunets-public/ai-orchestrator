---
language: ru
translation_of: skills/optional/python-code-review/README.md
---

# Python Code Review Skill 2.0

[English version](README.md)

Платформо-независимый навык для AI coding agents, в котором основным механизмом
ревью является не чек-лист, а глобальный анализ поведения и архитектуры системы.

## Главное изменение версии 2.0

Навык сначала заставляет модель:

- восстановить назначение системы и ключевые пользовательские потоки;
- построить модель компонентов, зависимостей, данных и состояния;
- определить инварианты, ответственность и жизненный цикл ресурсов;
- проследить нормальные и аварийные сценарии через несколько файлов и слоёв;
- самостоятельно сформировать гипотезы о проблемах и попытаться их опровергнуть;
- оценить архитектурную согласованность и влияние изменений на всю систему.

Только после этого применяются пятиосевая схема и Python-справочник. Они служат
страховочной сеткой для полноты, а не ограничивают способность модели находить
нестандартные проблемы.

## Ключевая модель scope

Навык разделяет:

- **target scope** — что пользователь просит проверить;
- **context scope** — какой окружающий код нужно прочитать;
- **system horizon** — какое глобальное поведение может быть затронуто.

Поэтому ревью небольшого diff остаётся сфокусированным в отчёте, но анализирует
вызовы, данные, БД, конфигурацию, фоновые процессы и архитектурные последствия.

## Структура

```text
python-code-review-skill/
├── SKILL.md
├── README.ru.md
├── THIRD_PARTY_NOTICES.md
├── references/
│   ├── system-analysis.md
│   ├── python-review.md
│   └── tooling.md
├── reviewers/
│   └── independent-reviewer.md
└── templates/
    └── review-report.md
```

## Режимы

- `CHANGE_REVIEW` — PR, ветка, commit range или локальные изменения.
- `COMPONENT_REVIEW` — модуль, пакет, сервис или отдельная функциональность.
- `PROJECT_AUDIT` — глобальный аудит архитектуры и качества проекта.

Для project audit навык использует осознанную выборку: ключевые end-to-end
потоки, composition roots, общие абстракции, stateful/concurrent code,
интеграции, БД, тестовую архитектуру и hotspots. В отчёте явно указывается, что
изучено глубоко, выборочно или не изучено.

## Установка

Скопируйте всю папку в каталог навыков платформы, сохранив относительные пути:

```text
<project>/.agents/skills/python-code-review/
<project>/.claude/skills/python-code-review/
<project>/.github/skills/python-code-review/
~/.codex/skills/python-code-review/
```

## Рекомендуемый запуск для глобального анализа

```text
Use python-code-review in PROJECT_AUDIT mode.

First reconstruct the architecture and primary end-to-end workflows. Build a
model of control flow, data flow, state ownership, resource lifecycle, failure
propagation, and critical invariants. Perform an open-ended semantic review
before using any checklist.

Identify systemic design problems, duplicated knowledge, hidden coupling,
invalid state transitions, fragile boundaries, operational risks, and gaps in
test architecture. Trace representative normal and failure scenarios across
files and layers.

Use Python-specific rules only as a final coverage backstop. Clearly distinguish
confirmed findings, intentional trade-offs, and unknowns. State what was deeply
inspected, sampled, or not inspected. Dispatch an independent reviewer. Do not
modify files.
```

## Рекомендуемый запуск для PR

```text
Use python-code-review in CHANGE_REVIEW mode for the current branch against
origin/main.

Keep the verdict focused on the change, but use a broad analysis horizon. First
understand the affected subsystem and trace the changed behavior end to end
through callers, persistence, configuration, external boundaries, jobs, and
tests. Do not start with a checklist.

Run repository-native checks, challenge green tests, use Python guidance as a
coverage sweep, and dispatch an independent reviewer. Return systemic and local
findings with evidence and a merge verdict. Do not modify files.
```

## Проектная настройка

В `AGENTS.md` или аналогичной инструкции желательно указать:

- назначение проекта и основные end-to-end потоки;
- архитектурные слои и допустимые зависимости;
- composition roots и точки входа;
- критичные доменные инварианты;
- правила состояния, транзакций, повторных вызовов и retries;
- команды unit/integration/end-to-end tests;
- команды Ruff, mypy/pyright и security checks;
- поддерживаемую версию Python;
- правила работы с БД, API, логами, персональными данными и секретами;
- механизм запуска независимого reviewer.
