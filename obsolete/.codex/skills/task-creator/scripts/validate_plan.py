from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_DOCUMENT_MARKERS = (
    "**Goal:**",
    "**Architecture:**",
    "**Tech Stack:**",
    "## Global Constraints",
    "## Deliverables",
    "## Dependencies",
    "## Acceptance Criteria",
    "## Testing Strategy",
    "## Risks and Rollback",
    "## Implementation Tasks",
)
REQUIRED_TASK_MARKERS = (
    "**Files:**",
    "**Interfaces:**",
    "**Acceptance:**",
    "**Tests:**",
)
PLACEHOLDER_RE = re.compile(
    r"\b(?:TBD|TODO|FIXME|implement later|fill in details)\b",
    re.IGNORECASE,
)
TASK_RE = re.compile(r"^### Task \d+: .+$", re.MULTILINE)


def validate_text(text: str) -> list[str]:
    errors: list[str] = []
    if "\ufffd" in text:
        errors.append("contains Unicode replacement characters")
    lines = text.splitlines()
    first_line = lines[0] if lines else ""
    if not re.fullmatch(r"# .+ Implementation Plan", first_line):
        errors.append("first line must match '# <name> Implementation Plan'")
    for marker in REQUIRED_DOCUMENT_MARKERS:
        if marker not in text:
            errors.append(f"missing required marker: {marker}")
    placeholder = PLACEHOLDER_RE.search(text)
    if placeholder:
        errors.append(f"contains placeholder: {placeholder.group(0)}")

    matches = list(TASK_RE.finditer(text))
    if not matches:
        errors.append("must contain at least one '### Task N: ...' section")
        return errors

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.start():end]
        label = match.group(0)
        for marker in REQUIRED_TASK_MARKERS:
            if marker not in section:
                errors.append(f"{label}: missing {marker}")
        if not re.search(r"^- \[ \] \*\*Step \d+:", section, re.MULTILINE):
            errors.append(f"{label}: missing checkbox implementation steps")
    return errors


def validate_path(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"cannot read UTF-8 file: {exc}"]
    return validate_text(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate task-creator implementation plans.")
    parser.add_argument("plans", nargs="+", type=Path)
    args = parser.parse_args(argv)

    failed = False
    for path in args.plans:
        errors = validate_path(path)
        if errors:
            failed = True
            print(f"FAIL {path}", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
        else:
            print(f"PASS {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
