from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


COMMON_FIELDS = ("schema_version", "title", "type", "mode", "risk", "created_by")
QUICK_HEADINGS = (
    "## Исходный запрос",
    "## Цель",
    "## Объём задачи",
    "### Входит в scope",
    "### Не входит в scope",
    "## Критерии приёмки",
    "## План реализации",
    "## Открытые вопросы",
)
STANDARD_HEADINGS = QUICK_HEADINGS + (
    "## Проблема или потребность",
    "## Текущее поведение",
    "## Ожидаемое поведение",
    "## Анализ",
    "## Выбранный подход",
    "## Рассмотренные альтернативы",
    "## Затрагиваемые компоненты",
    "## Ограничения",
    "## Риски",
    "## Plan Review",
)
TASK_ID_RE = re.compile(r"TASK-\d{4,}")
CRITICAL_QUESTION_RE = re.compile(
    r"(?im)^\s*-\s*(?:\[critical\]|critical\s*:|критическ(?:ий|ая)\s*:)",
)


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}, ["frontmatter must start on the first line"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, ["frontmatter closing delimiter is missing"]
    result: dict[str, str] = {}
    errors: list[str] = []
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            errors.append(f"invalid frontmatter line: {line}")
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in result:
            errors.append(f"duplicate frontmatter field: {key}")
        result[key] = value.strip().strip("\"'")
    return result, errors


def validate_text(text: str, expected_state: str | None = None) -> list[str]:
    fields, errors = parse_frontmatter(text)
    for field in COMMON_FIELDS:
        if not fields.get(field):
            errors.append(f"missing frontmatter field: {field}")
    if fields.get("schema_version") != "1":
        errors.append("schema_version must equal 1")
    if fields.get("mode") not in {"quick", "standard", "deep"}:
        errors.append("mode must be quick, standard, or deep")
    if fields.get("risk") not in {"low", "medium", "high", "critical"}:
        errors.append("risk must be low, medium, high, or critical")
    if fields.get("mode") == "deep" and fields.get("approach_approved", "").lower() != "true":
        errors.append("deep context requires approach_approved: true")
    if "status" in fields:
        errors.append("status is forbidden in Task Context")

    task_id = fields.get("id", "")
    registered = bool(TASK_ID_RE.fullmatch(task_id))
    if expected_state == "registered" and not registered:
        errors.append("registered context must contain id TASK-XXXX")
    if expected_state == "draft" and task_id.lower() not in {"", "null", "none", "~"}:
        errors.append("draft context must omit id or set it to null")
    if registered:
        try:
            if int(fields.get("revision", "0")) < 1:
                raise ValueError
        except ValueError:
            errors.append("registered context must contain a positive integer revision")
        expected_title = f"# {task_id} — {fields.get('title', '')}"
        if expected_title not in text.splitlines():
            errors.append(f"registered context must contain heading: {expected_title}")
        if "# Execution Record" not in text.splitlines():
            errors.append("registered context must contain '# Execution Record'")

    required_headings = QUICK_HEADINGS if fields.get("mode") == "quick" else STANDARD_HEADINGS
    lines = set(text.splitlines())
    for heading in required_headings:
        if heading not in lines:
            errors.append(f"missing required heading: {heading}")
    open_questions = text.split("## Открытые вопросы", 1)
    if len(open_questions) == 2:
        section = open_questions[1].split("\n#", 1)[0]
        if CRITICAL_QUESTION_RE.search(section):
            errors.append("critical open question blocks registration")
    if "\ufffd" in text:
        errors.append("contains Unicode replacement characters")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Task Context contract.")
    parser.add_argument("context", type=Path)
    state = parser.add_mutually_exclusive_group()
    state.add_argument("--draft", action="store_true")
    state.add_argument("--registered", action="store_true")
    args = parser.parse_args(argv)

    try:
        text = args.context.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"FAIL {args.context}: {exc}", file=sys.stderr)
        return 1
    expected = "draft" if args.draft else "registered" if args.registered else None
    errors = validate_text(text, expected)
    if errors:
        print(f"FAIL {args.context}", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"PASS {args.context}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
