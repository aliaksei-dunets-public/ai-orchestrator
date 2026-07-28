from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .language_policy import LanguagePolicyError, classify_path


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


def _language_metadata_present(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return False
    try:
        end = lines.index("---", 1)
    except ValueError:
        return False
    return any(line.strip().startswith("language:") for line in lines[1:end])


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

    # Apply the repository language contract when the target project has one.
    # Small isolated unit-test roots may intentionally omit the policy and keep
    # the legacy source-authority contract.
    policy_path = root / "config/language-policy.json"
    if policy_path.is_file():
        try:
            decision = classify_path(root, path)
        except LanguagePolicyError as exc:
            raise SourceAuthorityError(f"language policy rejected source: {exc}") from exc
        if not decision.graph_eligible:
            raise SourceAuthorityError(
                f"source is not an English canonical graph source: {decision.reason}"
            )
        if (
            relative.as_posix().startswith(("docs/", "skills/"))
            or relative.name == "README.md"
        ) and not _language_metadata_present(path):
            raise SourceAuthorityError("source language metadata is required")

    category = "other"
    authoritative = False
    posix = relative.as_posix()
    if posix.startswith("docs/specifications/"):
        category, authoritative = "specification", True
    elif posix.startswith("docs/adr/"):
        text = path.read_text(encoding="utf-8").lower()
        accepted = "status:** accepted" in text
        category, authoritative = "accepted_adr", accepted
    elif posix.startswith(".orchestrator/tasks/contexts/"):
        text = path.read_text(encoding="utf-8").lower()
        completed = (
            "# execution record" in text
            and "status: completed" in text
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
