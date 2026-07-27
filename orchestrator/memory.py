from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .session_report import redact


MemoryKind = Literal["observation", "decision", "lesson", "instruction"]


class MemoryError(ValueError):
    pass


@dataclass(frozen=True)
class MemoryEntry:
    id: str
    kind: MemoryKind
    content: str
    source: str
    source_digest: str
    confidence: float
    timestamp: str
    supersedes: str | None = None
    enabled: bool = True

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


def source_digest(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_entries(path: Path | str) -> list[MemoryEntry]:
    store = Path(path)
    if not store.exists():
        return []
    entries: list[MemoryEntry] = []
    for line in store.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        payload.pop("schema_version", None)
        entries.append(MemoryEntry(**payload))
    return entries


def append_entry(
    store: Path | str,
    *,
    kind: MemoryKind,
    content: str,
    source: Path | str,
    confidence: float,
    expected_source_digest: str | None = None,
    supersedes: str | None = None,
    promoted_as_instruction: bool = False,
) -> MemoryEntry:
    if not 0 <= confidence <= 1:
        raise MemoryError("confidence must be between zero and one")
    source_path = Path(source).resolve()
    if not source_path.is_file():
        raise MemoryError("memory source does not exist")
    digest = source_digest(source_path)
    if expected_source_digest is not None and digest != expected_source_digest:
        raise MemoryError("memory source is stale")
    safe_content = redact(content)
    if safe_content != content:
        raise MemoryError("secret-like content is rejected before persistence")
    if kind == "instruction" and not promoted_as_instruction:
        raise MemoryError("observations cannot become instructions automatically")

    store_path = Path(store)
    existing = load_entries(store_path)
    if any(
        item.kind == kind and item.content == content and item.source == str(source_path)
        for item in existing
    ):
        raise MemoryError("duplicate memory entry")
    if supersedes and supersedes not in {item.id for item in existing}:
        raise MemoryError("superseded memory entry does not exist")
    entry = MemoryEntry(
        id=f"MEM-{len(existing) + 1:04d}",
        kind=kind,
        content=safe_content,
        source=str(source_path),
        source_digest=digest,
        confidence=confidence,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        supersedes=supersedes,
    )
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with store_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return entry
