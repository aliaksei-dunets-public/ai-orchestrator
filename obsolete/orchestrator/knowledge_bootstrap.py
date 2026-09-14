from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .knowledge import (
    KnowledgeEdge,
    KnowledgeError,
    KnowledgeNode,
    _edge_from_dict,
    _node_from_dict,
    _project_provenance,
    _read_jsonl,
    effective_graph,
)
from .ontology import Ontology
from .session_report import redact


_NODE_KEYS = {"id", "kind", "label", "source", "supersedes", "enabled"}
_EDGE_KEYS = {"id", "source_node", "target_node", "relation", "source", "enabled"}


@dataclass(frozen=True)
class GraphUpdate:
    nodes_content: str
    edges_content: str
    effective_node_ids: tuple[str, ...]
    effective_edge_ids: tuple[str, ...]


def apply_graph_update(
    nodes_path: Path | str,
    edges_path: Path | str,
    update: GraphUpdate,
) -> None:
    """Apply a prepared two-file graph update with rollback on replacement failure."""
    targets = (
        (Path(nodes_path), update.nodes_content),
        (Path(edges_path), update.edges_content),
    )
    originals: dict[Path, bytes | None] = {
        path: path.read_bytes() if path.exists() else None for path, _ in targets
    }
    temporary: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for path, content in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            candidate = path.with_name(f"{path.name}.{os.getpid()}.tmp")
            with candidate.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary[path] = candidate
        for path, _ in targets:
            os.replace(temporary[path], path)
            replaced.append(path)
    except Exception:
        for path in reversed(replaced):
            original = originals[path]
            if original is None:
                path.unlink(missing_ok=True)
            else:
                rollback = path.with_name(f"{path.name}.{os.getpid()}.rollback")
                rollback.write_bytes(original)
                os.replace(rollback, path)
        raise
    finally:
        for candidate in temporary.values():
            candidate.unlink(missing_ok=True)


def _jsonl(records: list[dict[str, object]]) -> str:
    return "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for record in records
    )


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeError(f"knowledge proposal field {field} is required")
    return value.strip()


def _optional_bool(value: object, field: str) -> bool:
    if value is None:
        return True
    if not isinstance(value, bool):
        raise KnowledgeError(f"knowledge proposal field {field} must be boolean")
    return value


def _proposal_nodes(payload: Mapping[str, object]) -> list[KnowledgeNode]:
    raw_nodes = payload.get("nodes", [])
    if not isinstance(raw_nodes, list):
        raise KnowledgeError("knowledge proposal nodes must be an array")
    result: list[KnowledgeNode] = []
    for raw in raw_nodes:
        if not isinstance(raw, Mapping):
            raise KnowledgeError("knowledge proposal node must be an object")
        if "source_digest" in raw:
            raise KnowledgeError("knowledge proposal must not provide source_digest")
        unknown = set(raw) - _NODE_KEYS
        if unknown:
            raise KnowledgeError(f"unknown knowledge proposal node fields: {sorted(unknown)}")
        supersedes = raw.get("supersedes")
        if supersedes is not None:
            supersedes = _required_text(supersedes, "supersedes")
        result.append(
            KnowledgeNode(
                _required_text(raw.get("id"), "id"),
                _required_text(raw.get("kind"), "kind"),
                _required_text(raw.get("label"), "label"),
                _required_text(raw.get("source"), "source"),
                supersedes,
                None,
                _optional_bool(raw.get("enabled"), "enabled"),
            )
        )
    return result


def _proposal_edges(payload: Mapping[str, object]) -> list[KnowledgeEdge]:
    raw_edges = payload.get("edges", [])
    if not isinstance(raw_edges, list):
        raise KnowledgeError("knowledge proposal edges must be an array")
    result: list[KnowledgeEdge] = []
    for raw in raw_edges:
        if not isinstance(raw, Mapping):
            raise KnowledgeError("knowledge proposal edge must be an object")
        if "source_digest" in raw:
            raise KnowledgeError("knowledge proposal must not provide source_digest")
        unknown = set(raw) - _EDGE_KEYS
        if unknown:
            raise KnowledgeError(f"unknown knowledge proposal edge fields: {sorted(unknown)}")
        result.append(
            KnowledgeEdge(
                _required_text(raw.get("id"), "id"),
                _required_text(raw.get("source_node"), "source_node"),
                _required_text(raw.get("target_node"), "target_node"),
                _required_text(raw.get("relation"), "relation"),
                _required_text(raw.get("source"), "source"),
                None,
                _optional_bool(raw.get("enabled"), "enabled"),
            )
        )
    return result


def _validate_root_payload(payload: object) -> Mapping[str, object]:
    if payload is None:
        return {"schema_version": 1, "nodes": [], "edges": []}
    if not isinstance(payload, Mapping):
        raise KnowledgeError("knowledge proposal must be an object")
    if payload.get("schema_version") != 1:
        raise KnowledgeError("knowledge proposal schema_version must equal 1")
    unknown = set(payload) - {"schema_version", "nodes", "edges"}
    if unknown:
        raise KnowledgeError(f"unknown knowledge proposal fields: {sorted(unknown)}")
    return payload


def _same_node(left: KnowledgeNode, right: KnowledgeNode) -> bool:
    return (
        left.id == right.id
        and left.kind == right.kind
        and left.label == right.label
        and left.source == right.source
        and left.supersedes == right.supersedes
        and left.enabled == right.enabled
        and left.source_digest in {None, right.source_digest}
    )


def _same_edge(left: KnowledgeEdge, right: KnowledgeEdge) -> bool:
    return (
        left.id == right.id
        and left.source_node == right.source_node
        and left.target_node == right.target_node
        and left.relation == right.relation
        and left.source == right.source
        and left.enabled == right.enabled
        and left.source_digest in {None, right.source_digest}
    )


def _merge_nodes(
    project_root: Path,
    existing: list[KnowledgeNode],
    proposal: list[KnowledgeNode],
    ontology: Ontology,
) -> list[KnowledgeNode]:
    by_id = {node.id: node for node in existing}
    if len(by_id) != len(existing):
        raise KnowledgeError("duplicate node ids")
    merged = list(existing)
    for node in sorted(proposal, key=lambda item: item.id):
        if node.kind not in ontology.node_kinds:
            raise KnowledgeError(f"node kind is not in the ontology: {node.kind}")
        if redact(node.label) != node.label:
            raise KnowledgeError("secret-like knowledge node label is rejected")
        source, digest = _project_provenance(project_root, node.source)
        persisted = KnowledgeNode(
            node.id,
            node.kind,
            node.label,
            source,
            node.supersedes,
            digest,
            node.enabled,
        )
        previous = by_id.get(node.id)
        if previous is not None:
            if not _same_node(previous, persisted):
                raise KnowledgeError(f"Conflicting knowledge id: {node.id}")
            index = next(index for index, item in enumerate(merged) if item.id == node.id)
            merged[index] = persisted
            by_id[node.id] = persisted
            continue
        by_id[node.id] = persisted
        merged.append(persisted)
    for node in merged:
        if node.supersedes and node.supersedes not in by_id:
            raise KnowledgeError("Superseded node does not exist")
    return merged


def _merge_edges(
    project_root: Path,
    existing: list[KnowledgeEdge],
    proposal: list[KnowledgeEdge],
    nodes: list[KnowledgeNode],
    ontology: Ontology,
) -> list[KnowledgeEdge]:
    by_id = {edge.id: edge for edge in existing}
    if len(by_id) != len(existing):
        raise KnowledgeError("duplicate edge ids")
    node_ids = {node.id for node in nodes}
    merged = list(existing)
    for edge in sorted(proposal, key=lambda item: item.id):
        if edge.relation not in ontology.relations:
            raise KnowledgeError(f"edge relation is not in the ontology: {edge.relation}")
        source, digest = _project_provenance(project_root, edge.source)
        persisted = KnowledgeEdge(
            edge.id,
            edge.source_node,
            edge.target_node,
            edge.relation,
            source,
            digest,
            edge.enabled,
        )
        if persisted.source_node not in node_ids or persisted.target_node not in node_ids:
            raise KnowledgeError("Edge references an unknown node")
        previous = by_id.get(edge.id)
        if previous is not None:
            if not _same_edge(previous, persisted):
                raise KnowledgeError(f"Conflicting knowledge id: {edge.id}")
            index = next(index for index, item in enumerate(merged) if item.id == edge.id)
            merged[index] = persisted
            by_id[edge.id] = persisted
            continue
        by_id[edge.id] = persisted
        merged.append(persisted)
    return merged


def prepare_graph_update(
    project_root: Path | str,
    nodes_path: Path | str,
    edges_path: Path | str,
    proposal: object,
    *,
    ontology: Ontology,
) -> GraphUpdate:
    """Validate and merge a graph proposal without writing target files."""
    payload = _validate_root_payload(proposal)
    existing_nodes = [_node_from_dict(item) for item in _read_jsonl(Path(nodes_path))]
    existing_edges = [_edge_from_dict(item) for item in _read_jsonl(Path(edges_path))]
    nodes = _merge_nodes(
        Path(project_root).resolve(),
        existing_nodes,
        _proposal_nodes(payload),
        ontology,
    )
    edges = _merge_edges(
        Path(project_root).resolve(),
        existing_edges,
        _proposal_edges(payload),
        nodes,
        ontology,
    )
    nodes_content = _jsonl([node.to_dict() for node in nodes])
    edges_content = _jsonl([edge.to_dict() for edge in edges])
    with tempfile.TemporaryDirectory(prefix="knowledge-bootstrap-") as temporary:
        root = Path(temporary)
        temporary_nodes = root / "nodes.jsonl"
        temporary_edges = root / "edges.jsonl"
        temporary_nodes.write_text(nodes_content, encoding="utf-8")
        temporary_edges.write_text(edges_content, encoding="utf-8")
        effective_nodes, effective_edges = effective_graph(temporary_nodes, temporary_edges)
    return GraphUpdate(
        nodes_content,
        edges_content,
        tuple(node.id for node in effective_nodes),
        tuple(edge.id for edge in effective_edges),
    )
