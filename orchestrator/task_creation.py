from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .retrieval import build_context_pack


MODES = {"quick", "standard", "deep"}
RISKS = {"low", "medium", "high", "critical"}


class TaskCreationError(ValueError):
    pass


@dataclass(frozen=True)
class PlanTask:
    title: str
    files: tuple[str, ...]
    steps: tuple[str, ...]
    tests: tuple[str, ...]
    acceptance: tuple[str, ...]


@dataclass(frozen=True)
class PlanReview:
    approved: bool
    issues: tuple[str, ...] = ()


@dataclass
class TaskContextDefinition:
    title: str
    task_type: str
    mode: str
    risk: str
    original_request: str
    goal: str
    in_scope: list[str]
    out_of_scope: list[str]
    acceptance_criteria: list[str]
    plan: list[str]
    open_questions: list[str] = field(default_factory=list)
    problem: str = ""
    current_behavior: str = ""
    expected_behavior: str = ""
    analysis: str = ""
    selected_approach: str = ""
    alternatives: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    plan_review: str = ""
    approach_approved: bool = False


def review_plan(tasks: Iterable[PlanTask], acceptance_criteria: Iterable[str]) -> PlanReview:
    task_list = list(tasks)
    criteria = [item.strip() for item in acceptance_criteria if item.strip()]
    issues: list[str] = []
    if not task_list:
        issues.append("plan has no tasks")
    if not criteria:
        issues.append("plan has no acceptance criteria")
    for index, task in enumerate(task_list, 1):
        if not task.files:
            issues.append(f"task {index} has no exact files")
        if not task.steps:
            issues.append(f"task {index} has no implementation steps")
        if not task.tests:
            issues.append(f"task {index} has no tests")
        if not task.acceptance:
            issues.append(f"task {index} has no local acceptance criteria")
    return PlanReview(approved=not issues, issues=tuple(issues))


def validate_definition(definition: TaskContextDefinition) -> None:
    if definition.mode not in MODES:
        raise TaskCreationError(f"Unsupported mode: {definition.mode}")
    if definition.risk not in RISKS:
        raise TaskCreationError(f"Unsupported risk: {definition.risk}")
    required = {
        "title": definition.title,
        "task_type": definition.task_type,
        "original_request": definition.original_request,
        "goal": definition.goal,
        "in_scope": definition.in_scope,
        "out_of_scope": definition.out_of_scope,
        "acceptance_criteria": definition.acceptance_criteria,
        "plan": definition.plan,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise TaskCreationError(f"Missing required task definition fields: {missing}")
    if any(question.lower().startswith(("critical:", "[critical]", "критический:")) for question in definition.open_questions):
        raise TaskCreationError("Critical open question blocks context creation")
    if definition.mode in {"standard", "deep"}:
        detailed = {
            "problem": definition.problem,
            "current_behavior": definition.current_behavior,
            "expected_behavior": definition.expected_behavior,
            "analysis": definition.analysis,
            "selected_approach": definition.selected_approach,
            "alternatives": definition.alternatives,
            "components": definition.components,
            "constraints": definition.constraints,
            "risks": definition.risks,
            "plan_review": definition.plan_review,
        }
        missing_detailed = [name for name, value in detailed.items() if not value]
        if missing_detailed:
            raise TaskCreationError(f"Missing standard/deep fields: {missing_detailed}")
    if definition.mode == "deep" and not definition.approach_approved:
        raise TaskCreationError("Deep task requires explicit approach approval")


def _bullets(items: Iterable[str]) -> str:
    values = [item.strip() for item in items if item.strip()]
    return "\n".join(f"- {item}" for item in values) if values else "- Нет."


def render_task_context(definition: TaskContextDefinition) -> str:
    validate_definition(definition)
    frontmatter = [
        "---",
        "schema_version: 1",
        "id: null",
        f"title: {definition.title}",
        f"type: {definition.task_type}",
        f"mode: {definition.mode}",
        f"risk: {definition.risk}",
        "created_by: task-creation-workflow",
    ]
    if definition.mode == "deep":
        frontmatter.append("approach_approved: true")
    frontmatter.append("---")
    sections = [
        f"# {definition.title}",
        "## Исходный запрос",
        definition.original_request,
        "## Цель",
        definition.goal,
    ]
    if definition.mode in {"standard", "deep"}:
        sections.extend(
            [
                "## Проблема или потребность",
                definition.problem,
                "## Текущее поведение",
                definition.current_behavior,
                "## Ожидаемое поведение",
                definition.expected_behavior,
                "## Анализ",
                definition.analysis,
                "## Выбранный подход",
                definition.selected_approach,
                "## Рассмотренные альтернативы",
                _bullets(definition.alternatives),
            ]
        )
    sections.extend(
        [
            "## Объём задачи",
            "### Входит в scope",
            _bullets(definition.in_scope),
            "### Не входит в scope",
            _bullets(definition.out_of_scope),
        ]
    )
    if definition.mode in {"standard", "deep"}:
        sections.extend(["## Затрагиваемые компоненты", _bullets(definition.components)])
    sections.extend(["## Критерии приёмки", _bullets(definition.acceptance_criteria)])
    if definition.mode in {"standard", "deep"}:
        sections.extend(["## Ограничения", _bullets(definition.constraints), "## Риски", _bullets(definition.risks)])
    sections.extend(["## План реализации", _bullets(definition.plan)])
    if definition.mode in {"standard", "deep"}:
        sections.extend(["## Plan Review", definition.plan_review])
    sections.extend(["## Открытые вопросы", _bullets(definition.open_questions)])
    return "\n\n".join([*frontmatter, *sections]).rstrip() + "\n"


def write_task_context(path: Path | str, definition: TaskContextDefinition) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_task_context(definition), encoding="utf-8", newline="\n")
    return destination


def retrieve_task_creation_context(
    project_root: Path | str,
    *,
    mode: str,
    request: str,
    affected_paths: Iterable[str] = (),
) -> dict[str, object]:
    if mode not in MODES:
        raise TaskCreationError(f"Unsupported mode: {mode}")
    budgets = {"quick": 2048, "standard": 6144, "deep": 12288}
    return build_context_pack(
        project_root,
        task_context=request,
        affected_paths=tuple(affected_paths),
        budget_chars=budgets[mode],
    )
