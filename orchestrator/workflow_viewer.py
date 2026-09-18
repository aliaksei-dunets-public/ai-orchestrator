"""Локальный инспектор проверенного определения; не подключается к runtime."""
from pathlib import Path

from .workflow_builder import ResolvedWorkflow


def render_workflow(resolved: ResolvedWorkflow) -> str:
    template = (Path(__file__).parent / "assets" / "workflow-viewer.html").read_text(encoding="utf-8")
    # Даже инструкция с </script> остаётся данными, а не HTML/JavaScript.
    payload = resolved._snapshot.decode("utf-8").replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return template.replace("__WORKFLOW_DATA__", payload)
