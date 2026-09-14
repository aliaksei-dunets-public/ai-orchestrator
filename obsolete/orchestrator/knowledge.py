from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .ontology import Ontology
from .source_authority import SourceAuthorityError, classify_source


class KnowledgeError(ValueError):
    pass


@dataclass(frozen=True)
class KnowledgeNode:
    id: str
    kind: str
    label: str
    source: str
    supersedes: str | None = None
    source_digest: str | None = None
    enabled: bool = True

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


@dataclass(frozen=True)
class KnowledgeEdge:
    id: str
    source_node: str
    target_node: str
    relation: str
    source: str
    source_digest: str | None = None
    enabled: bool = True

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise KnowledgeError(f"invalid JSONL at {path}:{number}") from exc
        if not isinstance(payload, dict):
            raise KnowledgeError(f"knowledge record must be an object at {path}:{number}")
        records.append(payload)
    return records


def _atomic_append(path: Path, payload: dict[str, object]) -> None:
    existing = path.read_bytes() if path.exists() else b""
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _append_unique(path: Path, payload: dict[str, object]) -> None:
    existing = _read_jsonl(path)
    same_id = [item for item in existing if item.get("id") == payload["id"]]
    if same_id:
        if same_id[0] == payload:
            return
        raise KnowledgeError(f"Conflicting knowledge id: {payload['id']}")
    _atomic_append(path, payload)


def _project_provenance(
    project_root: Path | str,
    source: Path | str,
) -> tuple[str, str]:
    try:
        authority = classify_source(project_root, source)
    except SourceAuthorityError as exc:
        raise KnowledgeError(str(exc)) from exc
    return authority.source, authority.source_digest


def _node_from_dict(raw: dict[str, object]) -> KnowledgeNode:
    payload = dict(raw)
    payload.pop("schema_version", None)
    try:
        return KnowledgeNode(**payload)
    except TypeError as exc:
        raise KnowledgeError(f"invalid knowledge node: {exc}") from exc


def _edge_from_dict(raw: dict[str, object]) -> KnowledgeEdge:
    payload = dict(raw)
    payload.pop("schema_version", None)
    try:
        return KnowledgeEdge(**payload)
    except TypeError as exc:
        raise KnowledgeError(f"invalid knowledge edge: {exc}") from exc


def add_node(
    path: Path | str,
    node: KnowledgeNode,
    *,
    project_root: Path | str | None = None,
    ontology: Ontology | None = None,
) -> None:
    if ontology is not None and node.kind not in ontology.node_kinds:
        raise KnowledgeError(f"node kind is not in the ontology: {node.kind}")
    source, digest = node.source, node.source_digest
    if project_root is None:
        source_path = Path(source)
        if not source_path.is_file():
            raise KnowledgeError(f"Node source does not exist: {source_path}")
    else:
        source, digest = _project_provenance(project_root, source)
    existing = _read_jsonl(Path(path))
    if node.supersedes and node.supersedes not in {item.get("id") for item in existing}:
        raise KnowledgeError("Superseded node does not exist")
    persisted = KnowledgeNode(
        node.id,
        node.kind,
        node.label,
        source,
        node.supersedes,
        digest,
        node.enabled,
    )
    _append_unique(Path(path), persisted.to_dict())


def effective_graph(
    nodes_path: Path | str,
    edges_path: Path | str,
) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
    nodes = [_node_from_dict(item) for item in _read_jsonl(Path(nodes_path))]
    edges = [_edge_from_dict(item) for item in _read_jsonl(Path(edges_path))]
    by_id = {node.id: node for node in nodes}
    if len(by_id) != len(nodes):
        raise KnowledgeError("duplicate node ids")
    superseded: dict[str, str] = {}
    for node in nodes:
        if node.supersedes:
            if node.supersedes not in by_id:
                raise KnowledgeError("Superseded node does not exist")
            if node.supersedes in superseded:
                raise KnowledgeError("conflicting node supersede links")
            superseded[node.supersedes] = node.id
    for start in superseded:
        seen: set[str] = set()
        current = start
        while current in superseded:
            if current in seen:
                raise KnowledgeError("node supersede cycle")
            seen.add(current)
            current = superseded[current]
    active_nodes = sorted(
        (node for node in nodes if node.enabled and node.id not in superseded),
        key=lambda item: item.id,
    )
    active_ids = {node.id for node in active_nodes}
    edge_ids: set[str] = set()
    active_edges: list[KnowledgeEdge] = []
    for edge in edges:
        if edge.id in edge_ids:
            raise KnowledgeError("duplicate edge ids")
        edge_ids.add(edge.id)
        if not edge.enabled:
            continue
        if edge.source_node not in by_id or edge.target_node not in by_id:
            raise KnowledgeError("edge references an unknown node")
        if edge.source_node not in active_ids or edge.target_node not in active_ids:
            raise KnowledgeError("edge references a non-effective node")
        active_edges.append(edge)
    return active_nodes, sorted(active_edges, key=lambda item: item.id)


def add_edge(
    path: Path | str,
    edge: KnowledgeEdge,
    *,
    nodes_path: Path | str,
    project_root: Path | str | None = None,
    ontology: Ontology | None = None,
) -> None:
    if ontology is not None and edge.relation not in ontology.relations:
        raise KnowledgeError(f"edge relation is not in the ontology: {edge.relation}")
    source, digest = edge.source, edge.source_digest
    if project_root is None:
        if not Path(source).is_file():
            raise KnowledgeError(f"Edge source does not exist: {source}")
        node_ids = {item.get("id") for item in _read_jsonl(Path(nodes_path))}
    else:
        source, digest = _project_provenance(project_root, source)
        node_ids = {node.id for node in effective_graph(nodes_path, path)[0]}
    if edge.source_node not in node_ids or edge.target_node not in node_ids:
        qualifier = "effective " if project_root is not None else ""
        raise KnowledgeError(f"Edge references an unknown {qualifier}node")
    persisted = KnowledgeEdge(
        edge.id,
        edge.source_node,
        edge.target_node,
        edge.relation,
        source,
        digest,
        edge.enabled,
    )
    _append_unique(Path(path), persisted.to_dict())


def _store_digest(
    nodes: list[KnowledgeNode],
    edges: list[KnowledgeEdge],
) -> str:
    payload = {
        "nodes": [node.to_dict() for node in nodes],
        "edges": [edge.to_dict() for edge in edges],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def rebuild_indexes(
    nodes_path: Path | str,
    edges_path: Path | str,
    destination: Path | str,
) -> Path:
    nodes, edges = effective_graph(nodes_path, edges_path)
    by_kind: dict[str, list[str]] = {}
    by_relation: dict[str, list[str]] = {}
    nodes_by_source: dict[str, list[str]] = {}
    edges_by_source: dict[str, list[str]] = {}
    outgoing: dict[str, list[str]] = {}
    incoming: dict[str, list[str]] = {}
    for node in nodes:
        by_kind.setdefault(node.kind, []).append(node.id)
        nodes_by_source.setdefault(node.source, []).append(node.id)
    for edge in edges:
        by_relation.setdefault(edge.relation, []).append(edge.id)
        edges_by_source.setdefault(edge.source, []).append(edge.id)
        outgoing.setdefault(edge.source_node, []).append(edge.id)
        incoming.setdefault(edge.target_node, []).append(edge.id)

    def stable(value: dict[str, list[str]]) -> dict[str, list[str]]:
        return {key: sorted(items) for key, items in sorted(value.items())}

    payload = {
        "schema_version": 1,
        "store_digest": _store_digest(nodes, edges),
        "node_ids_by_kind": stable(by_kind),
        "edge_ids_by_relation": stable(by_relation),
        "node_ids_by_source": stable(nodes_by_source),
        "edge_ids_by_source": stable(edges_by_source),
        "outgoing_edge_ids": stable(outgoing),
        "incoming_edge_ids": stable(incoming),
    }
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
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
