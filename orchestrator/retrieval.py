from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable, Sequence

from .knowledge import KnowledgeEdge, KnowledgeNode, effective_graph
from .memory import ENTRIES_PATH, EVENTS_PATH, MemoryEntry, effective_entries
from .session_report import redact


TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_./-]+")
EPOCH = "1970-01-01T00:00:00+00:00"


class RetrievalError(ValueError):
    pass


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def serialize_context_pack(pack: dict[str, object]) -> str:
    return _canonical(pack) + "\n"


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _tokens(values: Iterable[str]) -> tuple[str, ...]:
    result = {
        match.group(0).casefold()
        for value in values
        for match in TOKEN_RE.finditer(value)
        if len(match.group(0)) > 1
    }
    return tuple(sorted(result))


def _score(text: str, terms: Sequence[str]) -> int:
    lowered = text.casefold()
    return sum(lowered.count(term) for term in terms)


def _resolved_source(root: Path, source: str) -> Path | None:
    candidate = Path(source)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        candidate = candidate.resolve()
        candidate.relative_to(root)
    except (OSError, ValueError):
        return None
    return candidate


def _fresh(root: Path, source: str, expected_digest: str | None) -> bool:
    path = _resolved_source(root, source)
    if path is None or not path.is_file():
        return False
    if expected_digest is None:
        return True  # schema-version-1 graph compatibility
    return hashlib.sha256(path.read_bytes()).hexdigest() == expected_digest


def _record_size(payload: dict[str, object]) -> int:
    return len(_canonical(payload))


def _store_digest(root: Path) -> str:
    paths = (
        root / ENTRIES_PATH,
        root / EVENTS_PATH,
        root / ".orchestrator/knowledge/nodes.jsonl",
        root / ".orchestrator/knowledge/edges.jsonl",
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        if path.exists():
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _safe_memory(root: Path) -> list[MemoryEntry]:
    result: list[MemoryEntry] = []
    for entry in effective_entries(root):
        if redact(entry.content) != entry.content:
            continue
        if _fresh(root, entry.source, entry.source_digest):
            result.append(entry)
    return result


def _safe_graph(root: Path) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
    nodes_path = root / ".orchestrator/knowledge/nodes.jsonl"
    edges_path = root / ".orchestrator/knowledge/edges.jsonl"
    nodes, edges = effective_graph(nodes_path, edges_path)
    safe_nodes = [
        node
        for node in nodes
        if redact(node.label) == node.label
        and _fresh(root, node.source, node.source_digest)
    ]
    safe_ids = {node.id for node in safe_nodes}
    safe_edges = [
        edge
        for edge in edges
        if edge.source_node in safe_ids
        and edge.target_node in safe_ids
        and _fresh(root, edge.source, edge.source_digest)
    ]
    return safe_nodes, safe_edges


def _expanded_node_ids(
    ranked: list[tuple[int, KnowledgeNode]],
    edges: list[KnowledgeEdge],
    *,
    depth: int,
) -> set[str]:
    selected = {node.id for score, node in ranked if score > 0}
    frontier = set(selected)
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.source_node, set()).add(edge.target_node)
        adjacency.setdefault(edge.target_node, set()).add(edge.source_node)
    for _ in range(max(0, depth)):
        next_frontier: set[str] = set()
        for node_id in sorted(frontier):
            next_frontier.update(adjacency.get(node_id, set()))
        next_frontier -= selected
        if not next_frontier:
            break
        selected.update(next_frontier)
        frontier = next_frontier
    return selected


def build_context_pack(
    project_root: Path | str,
    *,
    task_context: str = "",
    affected_paths: Sequence[str] = (),
    terms: Sequence[str] = (),
    budget_chars: int = 6144,
    max_records: int = 32,
    graph_depth: int = 2,
) -> dict[str, object]:
    if budget_chars < 0 or max_records < 0 or graph_depth < 0:
        raise RetrievalError("retrieval limits must be non-negative")
    root = Path(project_root).resolve()
    query_terms = _tokens((task_context, *affected_paths, *terms))
    query = {
        "task_context": task_context,
        "affected_paths": sorted(set(affected_paths)),
        "terms": sorted(set(terms)),
    }
    memory = _safe_memory(root)
    nodes, edges = _safe_graph(root)
    ranked_memory = sorted(
        (
            (
                _score(
                    " ".join((entry.kind, entry.content, entry.source)),
                    query_terms,
                ),
                entry,
            )
            for entry in memory
        ),
        key=lambda item: (-item[0], item[1].id),
    )
    ranked_nodes = sorted(
        (
            (
                _score(
                    " ".join((node.kind, node.label, node.source)),
                    query_terms,
                ),
                node,
            )
            for node in nodes
        ),
        key=lambda item: (-item[0], item[1].id),
    )
    expanded_ids = _expanded_node_ids(ranked_nodes, edges, depth=graph_depth)

    selected_memory: list[dict[str, object]] = []
    selected_nodes: list[dict[str, object]] = []
    selected_edges: list[dict[str, object]] = []
    used = 0
    count = 0

    candidates: list[tuple[int, str, str, dict[str, object]]] = []
    for score, entry in ranked_memory:
        if score > 0:
            candidates.append((score, "memory", entry.id, entry.to_dict()))
    node_scores = {node.id: score for score, node in ranked_nodes}
    for node in nodes:
        if node.id in expanded_ids:
            candidates.append((max(1, node_scores[node.id]), "node", node.id, node.to_dict()))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))

    for _, category, _, payload in candidates:
        size = _record_size(payload)
        if count >= max_records or used + size > budget_chars:
            continue
        if category == "memory":
            selected_memory.append(payload)
        else:
            selected_nodes.append(payload)
        used += size
        count += 1

    selected_node_ids = {str(item["id"]) for item in selected_nodes}
    for edge in sorted(edges, key=lambda item: item.id):
        if edge.source_node not in selected_node_ids or edge.target_node not in selected_node_ids:
            continue
        payload = edge.to_dict()
        size = _record_size(payload)
        if count >= max_records or used + size > budget_chars:
            continue
        selected_edges.append(payload)
        used += size
        count += 1

    timestamps = [
        str(item["timestamp"])
        for item in selected_memory
        if isinstance(item.get("timestamp"), str)
    ]
    return {
        "schema_version": 1,
        "query_digest": _digest(query),
        "store_digest": _store_digest(root),
        "generated_at": max(timestamps, default=EPOCH),
        "budget_chars": budget_chars,
        "used_chars": used,
        "memory": sorted(selected_memory, key=lambda item: str(item["id"])),
        "nodes": sorted(selected_nodes, key=lambda item: str(item["id"])),
        "edges": sorted(selected_edges, key=lambda item: str(item["id"])),
    }
