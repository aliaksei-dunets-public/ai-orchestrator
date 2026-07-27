from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path


IGNORED_NAMES = {"__pycache__", ".DS_Store"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class SkillDrift:
    missing: tuple[str, ...]
    extra: tuple[str, ...]
    changed: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not (self.missing or self.extra or self.changed)


def _files(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    if not root.exists():
        return result
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_NAMES for part in relative.parts) or path.suffix in IGNORED_SUFFIXES:
            continue
        result[relative.as_posix()] = path
    return result


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_skill_drift(source: Path | str, installed: Path | str) -> SkillDrift:
    source_files = _files(Path(source))
    installed_files = _files(Path(installed))
    source_names = set(source_files)
    installed_names = set(installed_files)
    changed = sorted(
        name for name in source_names & installed_names if _digest(source_files[name]) != _digest(installed_files[name])
    )
    return SkillDrift(
        missing=tuple(sorted(source_names - installed_names)),
        extra=tuple(sorted(installed_names - source_names)),
        changed=tuple(changed),
    )


def install_skill(source: Path | str, installed: Path | str) -> SkillDrift:
    source_path = Path(source).resolve()
    installed_path = Path(installed).resolve()
    if not (source_path / "SKILL.md").is_file():
        raise ValueError(f"Canonical skill has no SKILL.md: {source_path}")
    current = check_skill_drift(source_path, installed_path)
    if current.clean:
        return current
    installed_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{installed_path.name}-", dir=installed_path.parent) as temporary:
        staged = Path(temporary) / installed_path.name
        shutil.copytree(
            source_path,
            staged,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store"),
        )
        if os.name == "nt":
            backup = Path(temporary) / f"{installed_path.name}.backup"
            if installed_path.exists():
                shutil.copytree(installed_path, backup)
                shutil.rmtree(installed_path)
            installed_path.mkdir(parents=True)
            try:
                shutil.copytree(staged, installed_path, dirs_exist_ok=True)
            except Exception:
                shutil.rmtree(installed_path, ignore_errors=True)
                if backup.exists():
                    installed_path.mkdir(parents=True)
                    shutil.copytree(backup, installed_path, dirs_exist_ok=True)
                raise
        elif installed_path.exists():
            backup = Path(temporary) / f"{installed_path.name}.backup"
            installed_path.replace(backup)
            try:
                staged.replace(installed_path)
            except Exception:
                backup.replace(installed_path)
                raise
        else:
            staged.replace(installed_path)
    drift = check_skill_drift(source_path, installed_path)
    if not drift.clean:
        raise RuntimeError(f"Installed skill differs from canonical source: {drift}")
    return drift


def install_registered_skills(
    repository_root: Path | str,
    installed_root: Path | str,
) -> dict[str, SkillDrift]:
    repository = Path(repository_root).resolve()
    destination = Path(installed_root).resolve()
    registry_path = repository / "registries/skills.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("entries"), list):
        raise ValueError("Invalid skills registry")
    results: dict[str, SkillDrift] = {}
    seen: set[str] = set()
    for entry in payload["entries"]:
        if not isinstance(entry, dict) or not entry.get("enabled", False):
            continue
        skill_id = entry.get("id")
        relative = entry.get("path")
        if not isinstance(skill_id, str) or not skill_id or skill_id in seen:
            raise ValueError(f"Invalid or duplicate skill id: {skill_id}")
        if not isinstance(relative, str):
            raise ValueError(f"Invalid path for skill {skill_id}")
        source_file = (repository / relative).resolve()
        try:
            source_file.relative_to(repository / "skills")
        except ValueError as exc:
            raise ValueError(f"Skill {skill_id} escapes canonical skills root") from exc
        if source_file.name != "SKILL.md" or source_file.parent.name != skill_id:
            raise ValueError(f"Skill {skill_id} registry path does not match its canonical directory")
        results[skill_id] = install_skill(source_file.parent, destination / skill_id)
        seen.add(skill_id)
    return results
