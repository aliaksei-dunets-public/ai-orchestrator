from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "generated",
    "__pycache__",
}
SECRET_NAMES = {".env", ".env.local", "credentials.json", "secrets.json", "id_rsa", "id_ed25519"}
MANUAL_START = "<!-- manual:start -->"
MANUAL_END = "<!-- manual:end -->"


@dataclass(frozen=True)
class ProjectFacts:
    root_name: str
    markers: tuple[str, ...]
    source_directories: tuple[str, ...]


@dataclass(frozen=True)
class OnboardingResult:
    changed: bool
    diff: str
    content: str


def collect_facts(root: Path | str, *, max_files: int = 5000) -> ProjectFacts:
    project = Path(root).resolve()
    markers: list[str] = []
    source_directories: set[str] = set()
    count = 0
    for path in project.rglob("*"):
        relative = path.relative_to(project)
        if any(part in IGNORED_DIRECTORIES for part in relative.parts):
            continue
        if path.name.lower() in SECRET_NAMES or path.name.lower().startswith(".env."):
            continue
        if path.is_file():
            count += 1
            if count > max_files:
                break
            if path.name in {"pyproject.toml", "package.json", "pom.xml", "build.gradle", "abapgit.xml"}:
                markers.append(relative.as_posix())
            if len(relative.parts) > 1 and path.suffix in {".py", ".ts", ".js", ".java", ".abap"}:
                source_directories.add(relative.parts[0])
    return ProjectFacts(project.name, tuple(sorted(set(markers))), tuple(sorted(source_directories)))


def _manual_block(existing: str) -> str:
    if not existing:
        return f"{MANUAL_START}\nAdd project-specific notes here.\n{MANUAL_END}"
    start = existing.find(MANUAL_START)
    end = existing.find(MANUAL_END)
    if start < 0 and end < 0:
        raise ValueError("Existing Project Context has no ownership markers")
    if start < 0 or end < start:
        raise ValueError("Existing Project Context has conflicting ownership markers")
    return existing[start : end + len(MANUAL_END)]


def render_project_context(facts: ProjectFacts, *, existing: str = "") -> str:
    manual = _manual_block(existing)
    markers = "\n".join(f"- `{item}`" for item in facts.markers) or "- None detected."
    sources = "\n".join(f"- `{item}`" for item in facts.source_directories) or "- None detected."
    return (
        "# Project Context\n\n"
        "<!-- generated:start -->\n"
        f"## Project\n\n`{facts.root_name}`\n\n"
        f"## Evidence markers\n\n{markers}\n\n"
        f"## Source directories\n\n{sources}\n"
        "<!-- generated:end -->\n\n"
        "## Manual notes\n\n"
        f"{manual}\n"
    )


def onboard(
    root: Path | str,
    destination: Path | str,
    *,
    dry_run: bool = True,
) -> OnboardingResult:
    target = Path(destination)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    content = render_project_context(collect_facts(root), existing=existing)
    diff = "".join(
        difflib.unified_diff(
            existing.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=str(target),
            tofile=str(target),
        )
    )
    if diff and not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    return OnboardingResult(bool(diff), diff, content)
