from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


class KnowledgeError(ValueError):
    pass


@dataclass(frozen=True)
class KnowledgeNode:
    id: str
    kind: str
    label: str
    source: str
    supersedes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


@dataclass(frozen=True)
class KnowledgeEdge:
    id: str
    source_node: str
    target_node: str
    relation: str
    source: str

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append_unique(path: Path, payload: dict[str, object]) -> None:
    existing = _read_jsonl(path)
    same_id = [item for item in existing if item.get("id") == payload["id"]]
    if same_id:
        if same_id[0] == payload:
            return
        raise KnowledgeError(f"Conflicting knowledge id: {payload['id']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def add_node(path: Path | str, node: KnowledgeNode) -> None:
    source = Path(node.source)
    if not source.is_file():
        raise KnowledgeError(f"Node source does not exist: {source}")
    existing = _read_jsonl(Path(path))
    if node.supersedes and node.supersedes not in {item.get("id") for item in existing}:
        raise KnowledgeError("Superseded node does not exist")
    _append_unique(Path(path), node.to_dict())


def add_edge(path: Path | str, edge: KnowledgeEdge, *, nodes_path: Path | str) -> None:
    if not Path(edge.source).is_file():
        raise KnowledgeError(f"Edge source does not exist: {edge.source}")
    node_ids = {item.get("id") for item in _read_jsonl(Path(nodes_path))}
    if edge.source_node not in node_ids or edge.target_node not in node_ids:
        raise KnowledgeError("Edge references an unknown node")
    _append_unique(Path(path), edge.to_dict())


def rebuild_indexes(
    nodes_path: Path | str,
    edges_path: Path | str,
    destination: Path | str,
) -> Path:
    nodes = sorted(_read_jsonl(Path(nodes_path)), key=lambda item: str(item["id"]))
    edges = sorted(_read_jsonl(Path(edges_path)), key=lambda item: str(item["id"]))
    by_kind: dict[str, list[str]] = {}
    outgoing: dict[str, list[str]] = {}
    for node in nodes:
        by_kind.setdefault(str(node["kind"]), []).append(str(node["id"]))
    for edge in edges:
        outgoing.setdefault(str(edge["source_node"]), []).append(str(edge["id"]))
    payload = {
        "schema_version": 1,
        "node_ids_by_kind": {key: sorted(value) for key, value in sorted(by_kind.items())},
        "outgoing_edge_ids": {key: sorted(value) for key, value in sorted(outgoing.items())},
    }
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
