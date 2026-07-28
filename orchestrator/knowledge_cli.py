from __future__ import annotations

import argparse
from pathlib import Path

from .knowledge import (
    KnowledgeEdge,
    KnowledgeNode,
    add_edge,
    add_node,
    effective_graph,
    rebuild_indexes,
)
from .ontology import load_core_ontology, load_project_ontology, merge_ontology


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="knowledge_command", required=True)
    node = commands.add_parser("add-node")
    for name in ("id", "kind", "label", "source"):
        node.add_argument(f"--{name}", required=True)
    node.add_argument("--supersedes")
    edge = commands.add_parser("add-edge")
    for name in ("id", "source-node", "target-node", "relation", "source"):
        edge.add_argument(f"--{name}", required=True)
    commands.add_parser("rebuild")
    commands.add_parser("list")


def _ontology(root: Path):
    return merge_ontology(
        load_core_ontology(),
        load_project_ontology(root / ".orchestrator/knowledge/ontology.json"),
    )


def run(args: argparse.Namespace) -> dict[str, object]:
    root = args.root.resolve()
    nodes = root / ".orchestrator/knowledge/nodes.jsonl"
    edges = root / ".orchestrator/knowledge/edges.jsonl"
    if args.knowledge_command == "add-node":
        node = KnowledgeNode(args.id, args.kind, args.label, args.source, args.supersedes)
        add_node(nodes, node, project_root=root, ontology=_ontology(root))
        return node.to_dict()
    if args.knowledge_command == "add-edge":
        edge = KnowledgeEdge(
            args.id, args.source_node, args.target_node, args.relation, args.source
        )
        add_edge(
            edges,
            edge,
            nodes_path=nodes,
            project_root=root,
            ontology=_ontology(root),
        )
        return edge.to_dict()
    if args.knowledge_command == "rebuild":
        path = rebuild_indexes(
            nodes, edges, root / ".orchestrator/knowledge/indexes/index.json"
        )
        return {"schema_version": 1, "path": path.relative_to(root).as_posix()}
    active_nodes, active_edges = effective_graph(nodes, edges)
    return {
        "schema_version": 1,
        "nodes": [node.to_dict() for node in active_nodes],
        "edges": [edge.to_dict() for edge in active_edges],
    }
