from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Iterable


class ReleaseError(ValueError):
    pass


def file_checksum(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_manifest(root: Path | str, paths: Iterable[str], *, version: str) -> dict[str, object]:
    repository = Path(root).resolve()
    files: dict[str, str] = {}
    for relative in sorted(set(paths)):
        target = (repository / relative).resolve()
        try:
            target.relative_to(repository)
        except ValueError as exc:
            raise ReleaseError(f"Manifest path escapes repository: {relative}") from exc
        if not target.is_file():
            raise ReleaseError(f"Manifest file does not exist: {relative}")
        files[relative.replace("\\", "/")] = file_checksum(target)
    return {
        "schema_version": 1,
        "version": version,
        "checksum_algorithm": "sha256",
        "files": files,
    }


def verify_manifest(root: Path | str, manifest: dict[str, object]) -> list[str]:
    repository = Path(root)
    failures: list[str] = []
    files = manifest.get("files", {})
    if not isinstance(files, dict):
        return ["manifest files must be an object"]
    for relative, expected in files.items():
        target = repository / str(relative)
        if not target.is_file():
            failures.append(f"missing:{relative}")
        elif file_checksum(target) != expected:
            failures.append(f"checksum:{relative}")
    return failures


def write_artifact_manifest(
    root: Path | str,
    artifact: Path | str,
    destination: Path | str,
    *,
    version: str,
) -> Path:
    repository = Path(root).resolve()
    artifact_root = Path(artifact).resolve()
    try:
        artifact_root.relative_to(repository)
    except ValueError as exc:
        raise ReleaseError("Artifact must be inside the release repository") from exc
    paths = [
        path.relative_to(repository).as_posix()
        for path in artifact_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    ]
    manifest = build_manifest(repository, paths, version=version)
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return target


def install_artifact(
    artifact: Path | str,
    destination: Path | str,
    *,
    managed: bool,
) -> Path:
    source = Path(artifact).resolve()
    target_root = Path(destination).resolve()
    if not (source / "orchestrator/__init__.py").is_file():
        raise ReleaseError("Release artifact has no orchestrator package")
    target = target_root / ".orchestrator/core" if managed else target_root
    target.mkdir(parents=True, exist_ok=True)
    for name in ("orchestrator", "profiles", "config", "skills", "workflows", "registries", "docs"):
        source_item = source / name
        if not source_item.exists():
            continue
        destination_item = target / name
        if destination_item.exists():
            shutil.rmtree(destination_item)
        shutil.copytree(source_item, destination_item)
    for name in ("pyproject.toml", "README.md", "CHANGELOG.md", "ROADMAP.md"):
        if (source / name).is_file():
            shutil.copy2(source / name, target / name)
    return target
