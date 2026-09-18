"""Безопасный bounded корпус и fingerprint; не parser/graph engine."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath

from .knowledge_contracts import CorpusPolicy, KnowledgeError, SourceFile, SourceSnapshot


DENIED = {".git", ".venv", "venv", ".tmp", ".orchestrator", "obsolete", "node_modules", "__pycache__",
          "build", "dist", ".agents", ".codex", ".idea", ".vscode", "graphify-out", "releases"}
SENSITIVE = re.compile(r"(^|[._-])(secret|secrets|credential|credentials|private|token|tokens|password|passwords|api-key|apikey)([._-]|$)", re.I)


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def safe_relative(value: str) -> str:
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()
            or any(part in {"..", ""} for part in value.split("/"))):
        raise KnowledgeError("validation_failed", "Требуется безопасный project-relative путь")
    return value


def checked_path(root: Path, path: Path) -> Path:
    # Проверяем каждый сегмент, а не только конечный resolve.
    absolute = Path(os.path.abspath(path))
    if not absolute.is_relative_to(root):
        raise KnowledgeError("validation_failed", "Путь выходит за фиксированный project root")
    current = root
    for segment in absolute.relative_to(root).parts:
        current = current / segment
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise KnowledgeError("validation_failed", "Symlink/junction/reparse path запрещён")
    if not absolute.resolve(strict=False).is_relative_to(root):
        raise KnowledgeError("validation_failed", "Resolved path выходит за project root")
    return absolute


def allowed_parts(path: Path):
    return not any(part.lower() in DENIED or part.startswith(".") or SENSITIVE.search(part) for part in path.parts)


def source_bytes(root: Path, entry: SourceFile, limit: int) -> bytes:
    path = checked_path(root, root / safe_relative(entry.path))
    try:
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
    except OSError as exc:
        raise KnowledgeError("source_unavailable", "Источник недоступен", path=entry.path) from exc
    if len(data) > limit:
        raise KnowledgeError("corpus_limit_exceeded", "Исходный файл превышает лимит", path=entry.path)
    if len(data) != entry.size or hashlib.sha256(data).hexdigest() != entry.sha256:
        raise KnowledgeError("source_drift", "Источник изменился после snapshot", path=entry.path)
    return data


def snapshot_sources(root: Path, policy: CorpusPolicy) -> SourceSnapshot:
    paths = set()
    visited = 0
    for include in policy.include_roots:
        candidate = checked_path(root, root / safe_relative(include))
        relative = candidate.relative_to(root)
        if relative.parts and not allowed_parts(relative):
            raise KnowledgeError("validation_failed", "Include root запрещён corpus policy")
        if not candidate.exists():
            raise KnowledgeError("source_unavailable", "Include root отсутствует", path=include)
        stack = [candidate]
        while stack:
            path = stack.pop()
            visited += 1
            if visited > policy.max_files * 20:
                raise KnowledgeError("corpus_limit_exceeded", "Слишком много filesystem entries")
            rel = path.relative_to(root)
            if rel.parts and not allowed_parts(rel):
                continue
            checked_path(root, path)
            if path.is_dir():
                try:
                    with os.scandir(path) as children:
                        for child in children:
                            if len(stack) > policy.max_files * 20:
                                raise KnowledgeError("corpus_limit_exceeded", "Слишком много filesystem entries")
                            stack.append(Path(child.path))
                except OSError as exc:
                    raise KnowledgeError("source_unavailable", "Corpus directory недоступен") from exc
            elif path.suffix.lower() in policy.extensions:
                if not path.is_file():
                    raise KnowledgeError("validation_failed", "Corpus source должен быть обычным файлом")
                paths.add(path)
                if len(paths) > policy.max_files:
                    raise KnowledgeError("corpus_limit_exceeded", "Превышен max_files")
    files, total = [], 0
    for path in sorted(paths):
        try:
            checked_path(root, path)
            with path.open("rb") as stream:
                data = stream.read(policy.max_file_bytes + 1)
        except OSError as exc:
            raise KnowledgeError("source_unavailable", "Corpus source недоступен") from exc
        total += len(data)
        if len(data) > policy.max_file_bytes or total > policy.max_total_bytes:
            raise KnowledgeError("corpus_limit_exceeded", "Превышен byte budget корпуса")
        files.append(SourceFile(path.relative_to(root).as_posix(), hashlib.sha256(data).hexdigest(), len(data)))
    policy_digest = hashlib.sha256(canonical_json(policy.to_dict())).hexdigest()
    payload = {"policy": policy_digest, "files": [{"path": f.path, "sha256": f.sha256, "size": f.size} for f in files]}
    return SourceSnapshot(hashlib.sha256(canonical_json(payload)).hexdigest(), policy_digest, tuple(files), total)
