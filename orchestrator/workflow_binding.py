"""Доверенные источники и immutable binding определения workflow."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .artifact_repository import ArtifactRepository
from .workflow_builder import ComponentLibrary, ResolvedWorkflow, WorkflowBuilder, canonical, digest


@dataclass(frozen=True)
class WorkflowSource:
    """Пути задаёт host, не Execution Package. При load файлы читаются заново."""

    definition: Path
    libraries: tuple[Path, ...]
    overlay: Path | None = None

    def __post_init__(self):
        object.__setattr__(self, "definition", Path(self.definition).resolve())
        object.__setattr__(self, "libraries", tuple(Path(p).resolve() for p in self.libraries))
        object.__setattr__(self, "overlay", Path(self.overlay).resolve() if self.overlay else None)

    def to_dict(self):
        return {"definition": str(self.definition), "libraries": [str(p) for p in self.libraries],
                "overlay": str(self.overlay) if self.overlay else None}

    def load(self) -> ResolvedWorkflow:
        return WorkflowBuilder(ComponentLibrary(self.libraries)).load(self.definition, overlay=self.overlay)


def publish_binding(repository: ArtifactRepository, ref: str, source: WorkflowSource):
    resolved = source.load()
    snapshot = resolved.to_dict()
    if len(canonical(snapshot)) > 2 * 1024 * 1024:
        raise ValueError("Workflow snapshot превышает 2 MiB")
    record = repository.put_json(ref, "workflow_definition", "v1", snapshot,
                                 contract="workflow-definition/v1")
    return {"digest": snapshot["digest"], "snapshot": record.to_dict(), "source": source.to_dict()}


def read_binding(repository: ArtifactRepository, binding: dict) -> ResolvedWorkflow:
    """Чтение только immutable record; никакие пути из source не исполняются/читаются."""
    if not isinstance(binding, dict) or set(binding) != {"digest", "snapshot", "source"}:
        raise ValueError("Неверный workflow binding")
    record = binding["snapshot"]
    stored = repository.get(record["ref"], "workflow_definition", record["version"], max_bytes=2 * 1024 * 1024)
    if stored.record.to_dict() != record or record["contract"] != "workflow-definition/v1":
        raise ValueError("Неверные metadata workflow snapshot")
    snapshot = json.loads(stored.content)
    expected = snapshot.pop("digest")
    if expected != binding["digest"] or expected != "workflow/v1:" + digest(snapshot):
        raise ValueError("Неверный digest workflow snapshot")
    snapshot["digest"] = expected
    # Graph восстанавливается из проверенного immutable snapshot конструктора.
    from .runtime_contracts import Graph, Node
    data = snapshot["graph"]
    graph = Graph(data["graph_id"], data["version"], data["entry_node"],
                  {key: Node(**value) for key, value in data["nodes"].items()})
    return ResolvedWorkflow(graph, stored.content)


__all__ = ["WorkflowSource"]
