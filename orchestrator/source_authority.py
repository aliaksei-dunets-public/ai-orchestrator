from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


class SourceAuthorityError(ValueError):
    pass


@dataclass(frozen=True)
class SourceAuthority:
    source: str
    source_digest: str
    category: str
    authoritative: bool


def _inside(root: Path, candidate: Path) -> Path:
    try:
        return candidate.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise SourceAuthorityError("source is outside the project root") from exc


def classify_source(project_root: Path | str, source: Path | str) -> SourceAuthority:
    root = Path(project_root).resolve()
    path = Path(source)
    if not path.is_absolute():
        path = root / path
    relative = _inside(root, path)
    if not path.is_file():
        raise SourceAuthorityError("source does not exist")
    parts = relative.parts
    lowered = {part.lower() for part in parts}
    if lowered & {".git", ".env", "secrets", "credentials", "releases"}:
        raise SourceAuthorityError("source path is excluded from memory and knowledge")

    category = "other"
    authoritative = False
    posix = relative.as_posix()
    if posix.startswith("docs/specifications/"):
        category, authoritative = "specification", True
    elif posix.startswith("docs/adr/"):
        text = path.read_text(encoding="utf-8").lower()
        accepted = "status:** accepted" in text or "статус:** принято" in text
        category, authoritative = "accepted_adr", accepted
    elif posix.startswith(".orchestrator/tasks/contexts/"):
        text = path.read_text(encoding="utf-8").lower()
        completed = (
            "# execution record" in text
            and ("status: completed" in text or "итог выполнения" in text and "completed" in text)
        )
        category, authoritative = "completed_task_context", completed
    elif posix.startswith(".orchestrator/reviews/approved/"):
        category, authoritative = "approved_review", True
    elif "session" in path.name.lower() or posix.startswith("reports/"):
        category = "session_report"

    return SourceAuthority(
        source=posix,
        source_digest=hashlib.sha256(path.read_bytes()).hexdigest(),
        category=category,
        authoritative=authoritative,
    )
