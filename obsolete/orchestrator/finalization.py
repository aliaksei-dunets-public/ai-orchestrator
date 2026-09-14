from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable as IterableABC
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Sequence

from .documentation import (
    DocumentationGateEvidence,
    evaluate_documentation_gate,
)
from .execution import baseline_hash
from .knowledge import effective_graph, rebuild_indexes
from .knowledge_bootstrap import apply_graph_update, prepare_graph_update
from .memory import (
    ENTRIES_PATH,
    MemoryProposal,
    create_proposal,
    effective_entries,
    load_approvals,
    load_entries,
    promote_proposal,
)
from .ontology import load_core_ontology, load_project_ontology, merge_ontology
from .source_authority import classify_source


RECEIPT_SCHEMA_VERSION = 1
RECEIPT_DIRNAME = "finalization"
SHA256_RE_LENGTH = 64


class FinalizationError(ValueError):
    pass


@dataclass(frozen=True)
class MemoryCandidate:
    kind: str
    content: str
    source: str
    confidence: float
    supersedes: str | None = None


@dataclass(frozen=True)
class FinalizationReceipt:
    schema_version: int
    task_id: str
    context_revision: int
    baseline_hash: str
    checkpoint_digest: str
    changed_paths_digest: str
    documentation_status: str
    documentation_evidence: tuple[dict[str, str], ...]
    knowledge_status: str
    knowledge_store_digest: str
    memory_status: str
    memory_proposal_hashes: tuple[str, ...]
    memory_entry_ids: tuple[str, ...]
    pending_approval_hashes: tuple[str, ...]
    ready_for_completion: bool
    receipt_hash: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["documentation_evidence"] = list(self.documentation_evidence)
        payload["memory_proposal_hashes"] = list(self.memory_proposal_hashes)
        payload["memory_entry_ids"] = list(self.memory_entry_ids)
        payload["pending_approval_hashes"] = list(self.pending_approval_hashes)
        return payload


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_context_revision(text: str) -> int:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise FinalizationError("Task Context has no frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise FinalizationError("Task Context frontmatter is not closed") from exc
    for line in lines[1:end]:
        if line.startswith("revision:"):
            try:
                revision = int(line.split(":", 1)[1].strip())
            except ValueError as exc:
                raise FinalizationError("Task Context revision must be an integer") from exc
            if revision < 1:
                raise FinalizationError("Task Context revision must be positive")
            return revision
    raise FinalizationError("Task Context has no revision")


def normalize_changed_paths(paths: Iterable[str]) -> tuple[str, ...]:
    normalized: set[str] = set()
    for raw in paths:
        if not isinstance(raw, str) or not raw.strip():
            raise FinalizationError("changed paths must be non-empty strings")
        value = raw.replace("\\", "/").strip()
        pure = PurePosixPath(value)
        if (
            pure.as_posix() == "."
            or not pure.parts
            or pure.is_absolute()
            or ".." in pure.parts
            or value.startswith("/")
            or ":" in pure.parts[0]
        ):
            raise FinalizationError(f"changed path escapes the project root: {raw}")
        normalized.add(pure.as_posix())
    return tuple(sorted(normalized))


def changed_paths_digest(paths: Iterable[str]) -> str:
    return _digest({"paths": list(normalize_changed_paths(paths))})


def _load_completed_checkpoint(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FinalizationError(f"Cannot read execution checkpoint: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("status") != "completed":
        raise FinalizationError("Execution checkpoint is not completed")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise FinalizationError("Execution checkpoint has no evidence records")
    for record in records:
        if (
            not isinstance(record, dict)
            or record.get("status") != "completed"
            or not isinstance(record.get("evidence"), list)
            or not record["evidence"]
        ):
            raise FinalizationError("Execution checkpoint contains incomplete evidence")
    return _file_digest(path)


def _knowledge_digest(nodes_path: Path, edges_path: Path) -> str:
    return hashlib.sha256(nodes_path.read_bytes() + b"\0" + edges_path.read_bytes()).hexdigest()


def _validate_memory_candidates(
    values: Sequence[MemoryCandidate | Mapping[str, object]],
) -> tuple[MemoryCandidate, ...]:
    result: list[MemoryCandidate] = []
    for value in values:
        if isinstance(value, MemoryCandidate):
            candidate = value
        elif isinstance(value, Mapping):
            unknown = set(value) - {
                "kind",
                "content",
                "source",
                "confidence",
                "supersedes",
            }
            if unknown:
                raise FinalizationError(
                    f"unknown memory candidate fields: {sorted(unknown)}"
                )
            try:
                candidate = MemoryCandidate(
                    kind=str(value["kind"]),
                    content=str(value["content"]),
                    source=str(value["source"]),
                    confidence=float(value["confidence"]),
                    supersedes=(
                        str(value["supersedes"])
                        if value.get("supersedes") is not None
                        else None
                    ),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise FinalizationError(f"invalid memory candidate: {exc}") from exc
        else:
            raise FinalizationError("memory candidate must be an object")
        if candidate.kind not in {"observation", "decision", "lesson", "instruction"}:
            raise FinalizationError(f"unsupported memory kind: {candidate.kind}")
        result.append(candidate)
    return tuple(result)


def _receipt_payload(
    *,
    task_id: str,
    context_revision: int,
    context_baseline_hash: str,
    checkpoint_digest: str,
    paths_digest: str,
    documentation_status: str,
    documentation_evidence: tuple[dict[str, str], ...],
    knowledge_status: str,
    knowledge_store_digest: str,
    memory_status: str,
    memory_proposal_hashes: tuple[str, ...],
    memory_entry_ids: tuple[str, ...],
    pending_approval_hashes: tuple[str, ...],
    ready_for_completion: bool,
) -> dict[str, object]:
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "task_id": task_id,
        "context_revision": context_revision,
        "baseline_hash": context_baseline_hash,
        "checkpoint_digest": checkpoint_digest,
        "changed_paths_digest": paths_digest,
        "documentation_status": documentation_status,
        "documentation_evidence": list(documentation_evidence),
        "knowledge_status": knowledge_status,
        "knowledge_store_digest": knowledge_store_digest,
        "memory_status": memory_status,
        "memory_proposal_hashes": list(memory_proposal_hashes),
        "memory_entry_ids": list(memory_entry_ids),
        "pending_approval_hashes": list(pending_approval_hashes),
        "ready_for_completion": ready_for_completion,
    }


def _receipt_from_payload(payload: Mapping[str, object]) -> FinalizationReceipt:
    expected = {
        "schema_version",
        "task_id",
        "context_revision",
        "baseline_hash",
        "checkpoint_digest",
        "changed_paths_digest",
        "documentation_status",
        "documentation_evidence",
        "knowledge_status",
        "knowledge_store_digest",
        "memory_status",
        "memory_proposal_hashes",
        "memory_entry_ids",
        "pending_approval_hashes",
        "ready_for_completion",
        "receipt_hash",
    }
    if set(payload) != expected:
        raise FinalizationError("finalization receipt has invalid fields")
    if payload.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise FinalizationError("unsupported finalization receipt schema")
    if (
        not isinstance(payload.get("task_id"), str)
        or not re.fullmatch(r"TASK-[0-9]{4,}", str(payload["task_id"]))
    ):
        raise FinalizationError("finalization receipt contains an invalid task id")
    revision = payload.get("context_revision")
    if (
        not isinstance(revision, int)
        or isinstance(revision, bool)
        or revision < 1
    ):
        raise FinalizationError("finalization receipt contains an invalid revision")
    if not isinstance(payload.get("ready_for_completion"), bool):
        raise FinalizationError("finalization receipt ready flag must be boolean")
    hash_fields = (
        "baseline_hash",
        "checkpoint_digest",
        "changed_paths_digest",
        "knowledge_store_digest",
        "receipt_hash",
    )
    if any(
        not isinstance(payload.get(field), str)
        or len(str(payload[field])) != SHA256_RE_LENGTH
        for field in hash_fields
    ):
        raise FinalizationError("finalization receipt contains an invalid digest")
    if payload.get("documentation_status") != "completed":
        raise FinalizationError("documentation finalization is not completed")
    if payload.get("knowledge_status") not in {"empty", "applied"}:
        raise FinalizationError("knowledge finalization is not completed")
    if payload.get("memory_status") not in {"completed", "waiting_user"}:
        raise FinalizationError("invalid memory finalization status")
    for field in (
        "documentation_evidence",
        "memory_proposal_hashes",
        "memory_entry_ids",
        "pending_approval_hashes",
    ):
        if not isinstance(payload.get(field), list):
            raise FinalizationError(f"finalization receipt field {field} must be an array")
    documentation_raw = payload["documentation_evidence"]
    if not all(
        isinstance(item, Mapping)
        and set(item)
        == {"document", "owner", "status", "reason", "evidence_ref"}
        and item.get("status") in {"updated", "not_applicable"}
        and all(isinstance(value, str) for value in item.values())
        for item in documentation_raw
    ):
        raise FinalizationError("finalization receipt has invalid documentation evidence")
    for field in ("memory_proposal_hashes", "pending_approval_hashes"):
        values = payload[field]
        if (
            not all(
                isinstance(value, str)
                and re.fullmatch(r"[0-9a-f]{64}", value)
                for value in values
            )
            or len(values) != len(set(values))
        ):
            raise FinalizationError(f"finalization receipt has invalid {field}")
    entry_ids = payload["memory_entry_ids"]
    if (
        not all(
            isinstance(value, str)
            and re.fullmatch(r"MEM-[0-9]{4,}", value)
            for value in entry_ids
        )
        or len(entry_ids) != len(set(entry_ids))
    ):
        raise FinalizationError("finalization receipt has invalid memory_entry_ids")
    pending = payload["pending_approval_hashes"]
    ready = payload["ready_for_completion"]
    memory_status = payload["memory_status"]
    if memory_status == "waiting_user" and (ready or not pending):
        raise FinalizationError("waiting memory finalization must contain pending approvals")
    if memory_status == "completed" and (pending or not ready):
        raise FinalizationError("completed memory finalization has inconsistent readiness")
    unsigned = dict(payload)
    receipt_hash = str(unsigned.pop("receipt_hash"))
    if _digest(unsigned) != receipt_hash:
        raise FinalizationError("finalization receipt hash is stale or invalid")
    return FinalizationReceipt(
        schema_version=RECEIPT_SCHEMA_VERSION,
        task_id=str(payload["task_id"]),
        context_revision=revision,
        baseline_hash=str(payload["baseline_hash"]),
        checkpoint_digest=str(payload["checkpoint_digest"]),
        changed_paths_digest=str(payload["changed_paths_digest"]),
        documentation_status=str(payload["documentation_status"]),
        documentation_evidence=tuple(dict(item) for item in documentation_raw),
        knowledge_status=str(payload["knowledge_status"]),
        knowledge_store_digest=str(payload["knowledge_store_digest"]),
        memory_status=str(payload["memory_status"]),
        memory_proposal_hashes=tuple(str(item) for item in payload["memory_proposal_hashes"]),
        memory_entry_ids=tuple(str(item) for item in payload["memory_entry_ids"]),
        pending_approval_hashes=tuple(str(item) for item in payload["pending_approval_hashes"]),
        ready_for_completion=ready,
        receipt_hash=receipt_hash,
    )


def load_receipt(path: Path | str) -> FinalizationReceipt:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FinalizationError(f"Cannot read finalization receipt: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise FinalizationError("finalization receipt must be an object")
    return _receipt_from_payload(payload)


def write_receipt(path: Path | str, receipt: FinalizationReceipt) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    data = json.dumps(receipt.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def verify_completion_receipt(
    receipt: FinalizationReceipt,
    *,
    task_id: str,
    context_path: Path | str,
    checkpoint_path: Path | str | None = None,
) -> None:
    context = Path(context_path)
    text = context.read_text(encoding="utf-8")
    if receipt.task_id != task_id:
        raise FinalizationError("finalization receipt belongs to another task")
    if receipt.context_revision != _parse_context_revision(text):
        raise FinalizationError("finalization receipt has a stale context revision")
    if receipt.baseline_hash != baseline_hash(text):
        raise FinalizationError("finalization receipt has a stale context baseline")
    if (
        checkpoint_path is not None
        and receipt.checkpoint_digest
        != _load_completed_checkpoint(Path(checkpoint_path))
    ):
        raise FinalizationError("finalization receipt has a stale checkpoint")
    if not receipt.ready_for_completion or receipt.pending_approval_hashes:
        raise FinalizationError("finalization receipt is not ready for completion")


def finalize_task(
    *,
    project_root: Path | str,
    task_id: str,
    context_path: Path | str,
    checkpoint_path: Path | str,
    changed_paths: Iterable[str],
    documentation_dispositions: Sequence[Mapping[str, object]] = (),
    knowledge_proposal: object,
    memory_candidates: Sequence[MemoryCandidate | Mapping[str, object]] = (),
) -> FinalizationReceipt:
    root = Path(project_root).resolve()
    if not isinstance(task_id, str) or not re.fullmatch(r"TASK-[0-9]{4,}", task_id):
        raise FinalizationError("task_id must match TASK-NNNN")
    if (
        isinstance(changed_paths, (str, bytes))
        or not isinstance(changed_paths, IterableABC)
    ):
        raise FinalizationError("changed_paths must be an array")
    if (
        isinstance(documentation_dispositions, (str, bytes))
        or not isinstance(documentation_dispositions, Sequence)
    ):
        raise FinalizationError("documentation_dispositions must be an array")
    if (
        isinstance(memory_candidates, (str, bytes))
        or not isinstance(memory_candidates, Sequence)
    ):
        raise FinalizationError("memory_candidates must be an array")
    context = Path(context_path).resolve()
    checkpoint = Path(checkpoint_path).resolve()
    for label, path in (("Task Context", context), ("checkpoint", checkpoint)):
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise FinalizationError(f"{label} is outside the project root") from exc
    text = context.read_text(encoding="utf-8")
    context_revision = _parse_context_revision(text)
    context_baseline_hash = baseline_hash(text)
    checkpoint_digest = _load_completed_checkpoint(checkpoint)
    normalized_paths = normalize_changed_paths(changed_paths)
    paths_digest = changed_paths_digest(normalized_paths)

    documentation = evaluate_documentation_gate(
        root,
        normalized_paths,
        documentation_dispositions,
    )
    documentation_evidence = tuple(item.to_dict() for item in documentation)

    knowledge_root = root / ".orchestrator" / "knowledge"
    nodes_path = knowledge_root / "nodes.jsonl"
    edges_path = knowledge_root / "edges.jsonl"
    ontology = merge_ontology(
        load_core_ontology(root / "config" / "knowledge-ontology.json"),
        load_project_ontology(knowledge_root / "ontology.json"),
    )
    if not isinstance(knowledge_proposal, Mapping):
        raise FinalizationError("knowledge proposal must be an explicit object")
    graph_update = prepare_graph_update(
        root,
        nodes_path,
        edges_path,
        knowledge_proposal,
        ontology=ontology,
    )
    raw_nodes = knowledge_proposal.get("nodes", [])
    raw_edges = knowledge_proposal.get("edges", [])
    knowledge_status = "empty" if not raw_nodes and not raw_edges else "applied"

    candidates = _validate_memory_candidates(memory_candidates)
    proposals: list[MemoryProposal] = []
    pending: list[str] = []
    approvals = load_approvals(root)
    selected_approvals: dict[str, object] = {}
    rejected: set[str] = set()
    existing_entries = load_entries(root / ENTRIES_PATH)
    existing_ids = {entry.id for entry in existing_entries}
    effective_ids = {entry.id for entry in effective_entries(root)}
    proposal_hashes: set[str] = set()
    for candidate in candidates:
        proposal = create_proposal(
            root,
            kind=candidate.kind,  # type: ignore[arg-type]
            content=candidate.content,
            source=candidate.source,
            confidence=candidate.confidence,
            supersedes=candidate.supersedes,
        )
        if proposal.proposal_hash in proposal_hashes:
            raise FinalizationError("duplicate memory candidate")
        proposal_hashes.add(proposal.proposal_hash)
        proposals.append(proposal)
        previous_entry = next(
            (
                entry
                for entry in existing_entries
                if entry.proposal_hash == proposal.proposal_hash
            ),
            None,
        )
        if previous_entry is not None and previous_entry.id not in effective_ids:
            raise FinalizationError(
                "memory candidate was previously promoted to an inactive entry"
            )
        if (
            proposal.supersedes is not None
            and proposal.supersedes not in existing_ids
        ):
            raise FinalizationError(
                f"superseded memory entry does not exist: {proposal.supersedes}"
            )
        if any(
            entry.proposal_hash != proposal.proposal_hash
            and entry.kind == proposal.kind
            and entry.content == proposal.content
            and entry.source == proposal.source
            for entry in existing_entries
        ):
            raise FinalizationError(
                "memory candidate duplicates an entry from another proposal"
            )
        authority = classify_source(root, proposal.source)
        requires_approval = proposal.kind == "instruction" or not authority.authoritative
        if not requires_approval:
            continue
        approval = next(
            (
                item
                for item in approvals
                if item.proposal_hash == proposal.proposal_hash
                and item.source_digest == proposal.source_digest
            ),
            None,
        )
        if approval is None:
            pending.append(proposal.proposal_hash)
        elif approval.decision == "reject":
            rejected.add(proposal.proposal_hash)
        else:
            selected_approvals[proposal.proposal_hash] = approval

    entry_ids: list[str] = []
    if not pending:
        if knowledge_status == "applied":
            apply_graph_update(nodes_path, edges_path, graph_update)
            rebuild_indexes(
                nodes_path,
                edges_path,
                knowledge_root / "indexes" / "index.json",
            )
        else:
            effective_graph(nodes_path, edges_path)
        for proposal in proposals:
            if proposal.proposal_hash in rejected:
                continue
            approval = selected_approvals.get(proposal.proposal_hash)
            entry = promote_proposal(root, proposal, approval=approval)  # type: ignore[arg-type]
            entry_ids.append(entry.id)

    knowledge_store_digest = _knowledge_digest(nodes_path, edges_path)
    memory_status = "waiting_user" if pending else "completed"
    ready = not pending
    unsigned = _receipt_payload(
        task_id=task_id,
        context_revision=context_revision,
        context_baseline_hash=context_baseline_hash,
        checkpoint_digest=checkpoint_digest,
        paths_digest=paths_digest,
        documentation_status="completed",
        documentation_evidence=documentation_evidence,
        knowledge_status=knowledge_status,
        knowledge_store_digest=knowledge_store_digest,
        memory_status=memory_status,
        memory_proposal_hashes=tuple(item.proposal_hash for item in proposals),
        memory_entry_ids=tuple(entry_ids),
        pending_approval_hashes=tuple(sorted(pending)),
        ready_for_completion=ready,
    )
    return _receipt_from_payload({**unsigned, "receipt_hash": _digest(unsigned)})
