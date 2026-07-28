from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping, Sequence


SECTION_NAMES = (
    ("changes", "Changes"),
    ("validation", "Validation"),
    ("decisions", "Decisions"),
    ("risks", "Risks"),
    ("next_actions", "Next actions"),
)
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|password|secret|access[_-]?token|refresh[_-]?token)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\b(?:ghp|github_pat|sk)-[A-Za-z0-9_-]{12,}\b"),
)


def redact(text: str) -> str:
    value = text
    value = SECRET_PATTERNS[0].sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
    value = SECRET_PATTERNS[1].sub("Bearer [REDACTED]", value)
    value = SECRET_PATTERNS[2].sub("[REDACTED]", value)
    return value


def _items(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Sequence):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def render_session_report(data: Mapping[str, object]) -> str:
    title = redact(str(data.get("title") or "Session Report"))
    lines = [f"# {title}"]
    summary = str(data.get("summary") or "").strip()
    if summary:
        lines.extend(("", redact(summary)))
    for key, heading in SECTION_NAMES:
        entries = _items(data.get(key))
        if not entries:
            continue
        lines.extend(("", f"## {heading}", ""))
        lines.extend(f"- {redact(item)}" for item in entries)
    return "\n".join(lines).rstrip() + "\n"


def write_session_report(path: Path | str, data: Mapping[str, object]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = render_session_report(data)
    destination.write_text(content, encoding="utf-8", newline="\n")
    return destination


def session_memory_candidates(data: Mapping[str, object]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for kind, key, confidence in (
        ("decision", "decisions", 1.0),
        ("lesson", "validation", 0.8),
        ("observation", "changes", 0.7),
    ):
        for content in _items(data.get(key)):
            safe = redact(content)
            if safe != content:
                continue
            candidates.append(
                {
                    "kind": kind,
                    "content": safe,
                    "confidence": confidence,
                    "requires_approval": True,
                }
            )
    return candidates
