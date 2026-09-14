from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


IGNORED_NAMES = {"__pycache__", ".DS_Store"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
SKILL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DEFAULT_DISTRIBUTIONS = {"system", "bundled"}
VALID_DISTRIBUTIONS = DEFAULT_DISTRIBUTIONS | {"optional"}


class SkillSelectionError(ValueError):
    pass


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
    # Keep staging outside the projection directory. Some platform hosts watch
    # projection directories and can hold newly-created temporary directories
    # open, which makes recursive backup/copy operations hang on Windows.
    staging_parent = Path(tempfile.gettempdir()) if os.name == "nt" else installed_path.parent.parent
    staging_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{installed_path.name}-", dir=staging_parent) as temporary:
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


def load_skill_selection(project_root: Path | str) -> tuple[str, ...]:
    selection_path = Path(project_root).resolve() / ".orchestrator" / "skills.json"
    if not selection_path.exists():
        return ()
    try:
        payload = json.loads(selection_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SkillSelectionError(f"Cannot read skill selection: {exc}") from exc
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "optional_skills"}:
        raise SkillSelectionError("Skill selection must contain only schema_version and optional_skills")
    if payload.get("schema_version") != 1:
        raise SkillSelectionError("Skill selection schema_version must equal 1")
    selected = payload.get("optional_skills")
    if not isinstance(selected, list):
        raise SkillSelectionError("optional_skills must be an array")
    if any(not isinstance(skill_id, str) or not SKILL_ID_PATTERN.fullmatch(skill_id) for skill_id in selected):
        raise SkillSelectionError("optional_skills contains an invalid skill id")
    if len(selected) != len(set(selected)):
        raise SkillSelectionError("optional_skills must not contain duplicates")
    return tuple(selected)


def _registered_skill_sources(repository: Path) -> list[tuple[str, str, Path]]:
    registry_path = repository / "registries/skills.json"
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SkillSelectionError(f"Cannot read skills registry: {exc}") from exc
    if payload.get("schema_version") != 1 or not isinstance(payload.get("entries"), list):
        raise SkillSelectionError("Invalid skills registry")
    sources: list[tuple[str, str, Path]] = []
    seen: set[str] = set()
    canonical_root = (repository / "skills").resolve()
    for entry in payload["entries"]:
        if not isinstance(entry, dict):
            raise SkillSelectionError("Skills registry entry must be an object")
        skill_id = entry.get("id")
        relative = entry.get("path")
        distribution = entry.get("distribution")
        if (
            not isinstance(skill_id, str)
            or not SKILL_ID_PATTERN.fullmatch(skill_id)
            or skill_id in seen
        ):
            raise SkillSelectionError(f"Invalid or duplicate skill id: {skill_id}")
        if entry.get("kind") != "skill" or not isinstance(relative, str):
            raise SkillSelectionError(f"Invalid registry entry for skill {skill_id}")
        if distribution not in VALID_DISTRIBUTIONS:
            raise SkillSelectionError(f"Invalid distribution for skill {skill_id}: {distribution}")
        source_file = (repository / relative).resolve()
        try:
            source_file.relative_to(canonical_root)
        except ValueError as exc:
            raise SkillSelectionError(f"Skill {skill_id} escapes canonical skills root") from exc
        if source_file.name != "SKILL.md" or source_file.parent.name != skill_id:
            raise SkillSelectionError(
                f"Skill {skill_id} registry path does not match its canonical directory"
            )
        if not source_file.is_file():
            raise SkillSelectionError(f"Canonical skill has no SKILL.md: {skill_id}")
        if entry.get("enabled", False):
            sources.append((skill_id, str(distribution), source_file.parent))
        seen.add(skill_id)
    return sources


def _normalize_optional_skills(optional_skills: Iterable[str]) -> tuple[str, ...]:
    selected = tuple(optional_skills)
    if any(not isinstance(skill_id, str) or not SKILL_ID_PATTERN.fullmatch(skill_id) for skill_id in selected):
        raise SkillSelectionError("optional_skills contains an invalid skill id")
    if len(selected) != len(set(selected)):
        raise SkillSelectionError("optional_skills must not contain duplicates")
    return selected


def resolve_skill_sources(
    repository_root: Path | str,
    *,
    project_root: Path | str | None = None,
    optional_skills: Iterable[str] | None = None,
) -> dict[str, Path]:
    repository = Path(repository_root).resolve()
    entries = _registered_skill_sources(repository)
    requested = (
        load_skill_selection(project_root)
        if optional_skills is None and project_root is not None
        else _normalize_optional_skills(optional_skills or ())
    )
    registered = {skill_id: (distribution, source) for skill_id, distribution, source in entries}
    for skill_id in requested:
        registered_entry = registered.get(skill_id)
        if registered_entry is None:
            raise SkillSelectionError(f"Unknown optional skill: {skill_id}")
        if registered_entry[0] != "optional":
            raise SkillSelectionError(f"Selected skill is not optional: {skill_id}")

    requested_set = set(requested)
    selected = {
        skill_id: source
        for skill_id, distribution, source in entries
        if distribution in DEFAULT_DISTRIBUTIONS
        or (distribution == "optional" and skill_id in requested_set)
    }

    if project_root is None:
        return dict(sorted(selected.items()))
    project_skills = Path(project_root).resolve() / ".orchestrator" / "project-skills"
    if not project_skills.exists():
        return dict(sorted(selected.items()))
    registered_ids = set(registered)
    for source in sorted((path for path in project_skills.iterdir() if path.is_dir()), key=lambda path: path.name):
        skill_id = source.name
        if not SKILL_ID_PATTERN.fullmatch(skill_id):
            raise SkillSelectionError(f"Invalid project-owned skill id: {skill_id}")
        if skill_id in registered_ids:
            raise SkillSelectionError(f"Project-owned skill id collides with library: {skill_id}")
        resolved_source = source.resolve()
        try:
            resolved_source.relative_to(project_skills.resolve())
        except ValueError as exc:
            raise SkillSelectionError(
                f"Project-owned skill escapes project-skills root: {skill_id}"
            ) from exc
        if not (source / "SKILL.md").is_file():
            raise SkillSelectionError(f"Project-owned skill has no SKILL.md: {skill_id}")
        selected[skill_id] = resolved_source
    return dict(sorted(selected.items()))


def _projection_drift(sources: dict[str, Path], destination: Path) -> dict[str, SkillDrift]:
    return {
        skill_id: check_skill_drift(source, destination / skill_id)
        for skill_id, source in sources.items()
    }


def _projection_is_current(sources: dict[str, Path], destination: Path) -> bool:
    installed_ids = (
        {path.name for path in destination.iterdir() if path.is_dir()}
        if destination.exists()
        else set()
    )
    return installed_ids == set(sources) and all(
        drift.clean for drift in _projection_drift(sources, destination).values()
    )


def _copy_skill_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store"),
    )


def _publish_projection(staged: Path, destination: Path, backup: Path) -> None:
    if os.name == "nt":
        if destination.exists():
            shutil.copytree(destination, backup)
            shutil.rmtree(destination)
        try:
            shutil.copytree(staged, destination)
        except Exception:
            shutil.rmtree(destination, ignore_errors=True)
            if backup.exists():
                shutil.copytree(backup, destination)
            raise
        return
    if destination.exists():
        destination.replace(backup)
    try:
        staged.replace(destination)
    except Exception:
        if backup.exists():
            backup.replace(destination)
        raise


def _restore_projection(destination: Path, backup: Path) -> None:
    shutil.rmtree(destination, ignore_errors=True)
    if not backup.exists():
        return
    if os.name == "nt":
        shutil.copytree(backup, destination)
    else:
        backup.replace(destination)


def _validate_projection_destination(
    repository: Path,
    destination: Path,
    project_root: Path | str | None,
) -> None:
    protected = [repository]
    if project_root is not None:
        protected.append(Path(project_root).resolve())
    for root in protected:
        if destination == root:
            raise SkillSelectionError(f"Skill projection cannot replace protected root: {root}")
        try:
            root.relative_to(destination)
        except ValueError:
            continue
        raise SkillSelectionError(f"Skill projection cannot contain protected root: {root}")


def install_registered_skills(
    repository_root: Path | str,
    installed_root: Path | str,
    *,
    project_root: Path | str | None = None,
    optional_skills: Iterable[str] | None = None,
) -> dict[str, SkillDrift]:
    repository = Path(repository_root).resolve()
    destination = Path(installed_root).resolve()
    _validate_projection_destination(repository, destination, project_root)
    sources = resolve_skill_sources(
        repository,
        project_root=project_root,
        optional_skills=optional_skills,
    )
    if _projection_is_current(sources, destination):
        return _projection_drift(sources, destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging_parent = Path(tempfile.gettempdir()) if os.name == "nt" else destination.parent.parent
    staging_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{destination.name}-projection-",
        dir=staging_parent,
    ) as temporary:
        temporary_root = Path(temporary)
        staged = temporary_root / destination.name
        staged.mkdir()
        for skill_id, source in sources.items():
            _copy_skill_tree(source, staged / skill_id)
        staged_drift = _projection_drift(sources, staged)
        if any(not drift.clean for drift in staged_drift.values()):
            raise RuntimeError("Staged skill projection differs from canonical sources")
        backup = temporary_root / f"{destination.name}.backup"
        _publish_projection(staged, destination, backup)
        try:
            results = _projection_drift(sources, destination)
            installed_ids = {path.name for path in destination.iterdir() if path.is_dir()}
            if installed_ids != set(sources) or any(not drift.clean for drift in results.values()):
                raise RuntimeError("Installed skill projection differs from selected sources")
            return results
        except Exception:
            _restore_projection(destination, backup)
            raise
