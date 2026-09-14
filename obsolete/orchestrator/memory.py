from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .approvals import MemoryApproval
from .session_report import redact
from .source_authority import SourceAuthorityError, classify_source


MemoryKind = Literal["observation", "decision", "lesson", "instruction"]
EventAction = Literal["promote", "disable", "supersede"]

MEMORY_ROOT = Path(".orchestrator/memory")
ENTRIES_PATH = MEMORY_ROOT / "entries.jsonl"
EVENTS_PATH = MEMORY_ROOT / "events.jsonl"
APPROVALS_PATH = MEMORY_ROOT / "approvals.jsonl"
PROPOSALS_PATH = MEMORY_ROOT / "proposals/proposals.jsonl"


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
    proposal_hash: str | None = None
    approval_hash: str | None = None
    source_authority: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


@dataclass(frozen=True)
class MemoryProposal:
    id: str
    kind: MemoryKind
    content: str
    source: str
    source_digest: str
    confidence: float
    proposal_hash: str
    created_at: str
    supersedes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


@dataclass(frozen=True)
class MemoryEvent:
    id: str
    action: EventAction
    subject_id: str
    timestamp: str
    reason: str
    replacement_id: str | None = None
    proposal_hash: str | None = None
    approval_hash: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


def source_digest(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    values: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MemoryError(f"invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(payload, dict):
            raise MemoryError(f"memory record must be an object at {path}:{line_number}")
        values.append(payload)
    return values


def _atomic_append(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_bytes() if path.exists() else b""
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(existing)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _next_id(prefix: str, records: list[dict[str, object]]) -> str:
    numbers: list[int] = []
    for record in records:
        value = str(record.get("id", ""))
        if value.startswith(f"{prefix}-") and value[len(prefix) + 1 :].isdigit():
            numbers.append(int(value[len(prefix) + 1 :]))
    return f"{prefix}-{max(numbers, default=0) + 1:04d}"


def _canonical_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _safe_content(content: str) -> str:
    if not content.strip():
        raise MemoryError("memory content is required")
    safe = redact(content)
    if safe != content:
        raise MemoryError("secret-like content is rejected before persistence")
    return safe


def load_entries(path: Path | str) -> list[MemoryEntry]:
    entries: list[MemoryEntry] = []
    for raw in _read_jsonl(Path(path)):
        payload = dict(raw)
        payload.pop("schema_version", None)
        try:
            entries.append(MemoryEntry(**payload))
        except TypeError as exc:
            raise MemoryError(f"invalid memory entry: {exc}") from exc
    return entries


def load_proposals(project_root: Path | str) -> list[MemoryProposal]:
    proposals: list[MemoryProposal] = []
    for raw in _read_jsonl(Path(project_root).resolve() / PROPOSALS_PATH):
        payload = dict(raw)
        payload.pop("schema_version", None)
        try:
            proposals.append(MemoryProposal(**payload))
        except TypeError as exc:
            raise MemoryError(f"invalid memory proposal: {exc}") from exc
    return proposals


def load_approvals(project_root: Path | str) -> list[MemoryApproval]:
    approvals: list[MemoryApproval] = []
    for raw in _read_jsonl(Path(project_root).resolve() / APPROVALS_PATH):
        payload = dict(raw)
        payload.pop("schema_version", None)
        try:
            approvals.append(MemoryApproval(**payload))
        except TypeError as exc:
            raise MemoryError(f"invalid memory approval: {exc}") from exc
    return approvals


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
    project_root: Path | str | None = None,
    proposal_hash: str | None = None,
    approval_hash: str | None = None,
    source_authority: str | None = None,
) -> MemoryEntry:
    if not 0 <= confidence <= 1:
        raise MemoryError("confidence must be between zero and one")
    source_path = Path(source)
    if project_root is not None and not source_path.is_absolute():
        source_path = Path(project_root) / source_path
    source_path = source_path.resolve()
    stored_source = str(source_path)
    if project_root is not None:
        try:
            stored_source = source_path.relative_to(Path(project_root).resolve()).as_posix()
        except ValueError as exc:
            raise MemoryError("memory source is outside the project root") from exc
    if not source_path.is_file():
        raise MemoryError("memory source does not exist")
    digest = source_digest(source_path)
    if expected_source_digest is not None and digest != expected_source_digest:
        raise MemoryError("memory source is stale")
    safe_content = _safe_content(content)
    if kind == "instruction" and not promoted_as_instruction:
        raise MemoryError("observations cannot become instructions automatically")

    store_path = Path(store)
    existing = load_entries(store_path)
    if any(
        item.kind == kind and item.content == content and item.source == stored_source
        for item in existing
    ):
        raise MemoryError("duplicate memory entry")
    if supersedes and supersedes not in {item.id for item in existing}:
        raise MemoryError("superseded memory entry does not exist")
    entry = MemoryEntry(
        id=_next_id("MEM", [item.to_dict() for item in existing]),
        kind=kind,
        content=safe_content,
        source=stored_source,
        source_digest=digest,
        confidence=confidence,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        supersedes=supersedes,
        proposal_hash=proposal_hash,
        approval_hash=approval_hash,
        source_authority=source_authority,
    )
    _atomic_append(store_path, entry.to_dict())
    return entry


def create_proposal(
    project_root: Path | str,
    *,
    kind: MemoryKind,
    content: str,
    source: Path | str,
    confidence: float,
    supersedes: str | None = None,
) -> MemoryProposal:
    if not 0 <= confidence <= 1:
        raise MemoryError("confidence must be between zero and one")
    root = Path(project_root).resolve()
    try:
        authority = classify_source(root, source)
    except SourceAuthorityError as exc:
        raise MemoryError(str(exc)) from exc
    safe = _safe_content(content)
    hash_input = {
        "kind": kind,
        "content": safe,
        "source": authority.source,
        "source_digest": authority.source_digest,
        "confidence": confidence,
        "supersedes": supersedes,
    }
    proposal_path = root / PROPOSALS_PATH
    existing = _read_jsonl(proposal_path)
    proposal_hash = _canonical_hash(hash_input)
    for raw in existing:
        if raw.get("proposal_hash") == proposal_hash:
            payload = dict(raw)
            payload.pop("schema_version", None)
            try:
                return MemoryProposal(**payload)
            except TypeError as exc:
                raise MemoryError(f"invalid memory proposal: {exc}") from exc
    proposal = MemoryProposal(
        id=_next_id("PROP", existing),
        proposal_hash=proposal_hash,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **hash_input,
    )
    _atomic_append(proposal_path, proposal.to_dict())
    return proposal


def _append_event(
    root: Path,
    *,
    action: EventAction,
    subject_id: str,
    reason: str,
    replacement_id: str | None = None,
    proposal_hash: str | None = None,
    approval_hash: str | None = None,
) -> MemoryEvent:
    path = root / EVENTS_PATH
    existing = _read_jsonl(path)
    event = MemoryEvent(
        id=_next_id("EVT", existing),
        action=action,
        subject_id=subject_id,
        replacement_id=replacement_id,
        proposal_hash=proposal_hash,
        approval_hash=approval_hash,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        reason=_safe_content(reason),
    )
    _atomic_append(path, event.to_dict())
    return event


def promote_proposal(
    project_root: Path | str,
    proposal: MemoryProposal,
    *,
    approval: MemoryApproval | None = None,
) -> MemoryEntry:
    root = Path(project_root).resolve()
    hash_input = {
        "kind": proposal.kind,
        "content": proposal.content,
        "source": proposal.source,
        "source_digest": proposal.source_digest,
        "confidence": proposal.confidence,
        "supersedes": proposal.supersedes,
    }
    if _canonical_hash(hash_input) != proposal.proposal_hash:
        raise MemoryError("proposal hash is stale or invalid")
    try:
        authority = classify_source(root, proposal.source)
    except SourceAuthorityError as exc:
        raise MemoryError(str(exc)) from exc
    if authority.source_digest != proposal.source_digest:
        raise MemoryError("memory source is stale")
    entries = load_entries(root / ENTRIES_PATH)
    existing = next(
        (
            entry
            for entry in entries
            if entry.proposal_hash == proposal.proposal_hash
        ),
        None,
    )
    if existing is not None:
        effective_ids = {entry.id for entry in effective_entries(root)}
        if existing.id not in effective_ids:
            raise MemoryError("proposal was previously promoted to an inactive entry")
        return existing
    requires_approval = proposal.kind == "instruction" or not authority.authoritative
    if requires_approval:
        if approval is None or approval.decision != "approve":
            raise MemoryError("explicit approval is required")
        if (
            approval.proposal_hash != proposal.proposal_hash
            or approval.source_digest != proposal.source_digest
        ):
            raise MemoryError("approval is stale for this proposal or source")
    approval_hash = approval.approval_hash if approval else None
    if approval is not None and approval.approval_hash not in {
        item.approval_hash for item in load_approvals(root)
    }:
        _atomic_append(root / APPROVALS_PATH, approval.to_dict())
    entry = append_entry(
        root / ENTRIES_PATH,
        kind=proposal.kind,
        content=proposal.content,
        source=proposal.source,
        confidence=proposal.confidence,
        expected_source_digest=proposal.source_digest,
        supersedes=proposal.supersedes,
        promoted_as_instruction=approval is not None and approval.decision == "approve",
        project_root=root,
        proposal_hash=proposal.proposal_hash,
        approval_hash=approval_hash,
        source_authority=authority.category,
    )
    _append_event(
        root,
        action="promote",
        subject_id=entry.id,
        reason="proposal promoted",
        proposal_hash=proposal.proposal_hash,
        approval_hash=approval_hash,
    )
    return entry


def disable_entry(project_root: Path | str, entry_id: str, *, reason: str) -> MemoryEvent:
    root = Path(project_root).resolve()
    if entry_id not in {entry.id for entry in load_entries(root / ENTRIES_PATH)}:
        raise MemoryError("memory entry does not exist")
    return _append_event(root, action="disable", subject_id=entry_id, reason=reason)


def supersede_entry(
    project_root: Path | str,
    entry_id: str,
    replacement_id: str,
    *,
    reason: str,
) -> MemoryEvent:
    root = Path(project_root).resolve()
    ids = {entry.id for entry in load_entries(root / ENTRIES_PATH)}
    if entry_id not in ids or replacement_id not in ids:
        raise MemoryError("supersede endpoints must exist")
    if entry_id == replacement_id:
        raise MemoryError("memory entry cannot supersede itself")
    superseded: dict[str, str] = {
        entry.supersedes: entry.id
        for entry in load_entries(root / ENTRIES_PATH)
        if entry.supersedes is not None
    }
    for raw in _read_jsonl(root / EVENTS_PATH):
        if raw.get("action") == "supersede":
            subject = str(raw.get("subject_id", ""))
            replacement = str(raw.get("replacement_id", ""))
            if subject in superseded and superseded[subject] != replacement:
                raise MemoryError("conflicting memory supersede events")
            superseded[subject] = replacement
    if entry_id in superseded and superseded[entry_id] != replacement_id:
        raise MemoryError("conflicting memory supersede events")
    current = replacement_id
    seen = {entry_id}
    while current in superseded:
        if current in seen:
            raise MemoryError("memory supersede cycle")
        seen.add(current)
        current = superseded[current]
    if current == entry_id:
        raise MemoryError("memory supersede cycle")
    return _append_event(
        root,
        action="supersede",
        subject_id=entry_id,
        replacement_id=replacement_id,
        reason=reason,
    )


def effective_entries(project_root: Path | str) -> list[MemoryEntry]:
    root = Path(project_root).resolve()
    entries = load_entries(root / ENTRIES_PATH)
    by_id = {entry.id: entry for entry in entries}
    if len(by_id) != len(entries):
        raise MemoryError("duplicate memory ids")
    disabled = {entry.id for entry in entries if not entry.enabled}
    superseded: dict[str, str] = {}
    for entry in entries:
        if entry.supersedes:
            if entry.supersedes not in by_id:
                raise MemoryError("superseded memory entry does not exist")
            superseded[entry.supersedes] = entry.id
    for raw in _read_jsonl(root / EVENTS_PATH):
        action = raw.get("action")
        subject = str(raw.get("subject_id", ""))
        if subject not in by_id:
            raise MemoryError("memory event references an unknown entry")
        if action == "disable":
            disabled.add(subject)
        elif action == "supersede":
            replacement = str(raw.get("replacement_id", ""))
            if replacement not in by_id:
                raise MemoryError("memory supersede event has an unknown replacement")
            if subject in superseded and superseded[subject] != replacement:
                raise MemoryError("conflicting memory supersede events")
            superseded[subject] = replacement
        elif action != "promote":
            raise MemoryError("unknown memory lifecycle action")

    for start in superseded:
        seen: set[str] = set()
        current = start
        while current in superseded:
            if current in seen:
                raise MemoryError("memory supersede cycle")
            seen.add(current)
            current = superseded[current]
    return sorted(
        (
            entry
            for entry in entries
            if entry.id not in disabled and entry.id not in superseded
        ),
        key=lambda item: item.id,
    )
