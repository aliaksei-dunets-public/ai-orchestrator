"""Task Creator boundary and Task Manager registration adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from orchestrator_task_manager import TaskError, TaskManagerService

from .request_router import TaskType


@dataclass(frozen=True)
class TaskCreationResult:
    """Structured result returned by the Task Creator node."""

    result: str
    task: dict[str, Any] | None = None
    artifact: dict[str, str] | None = None
    questions: tuple[str, ...] = ()
    error: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"result": self.result}
        if self.task is not None:
            value["task"] = self.task
        if self.artifact is not None:
            value["artifact"] = self.artifact
        if self.questions:
            value["questions"] = list(self.questions)
        if self.error is not None:
            value["error"] = self.error
        return value


DraftBuilder = Callable[[str, TaskType, Mapping[str, Any] | None], Mapping[str, Any]]


class TaskCreator:
    """Turn a routed request into a Task Manager task.

    The builder owns semantic reasoning.  This class only validates the
    candidate artifact, asks for missing user-owned information, and calls the
    public Task Manager API for persistence.
    """

    def __init__(self, service: TaskManagerService, builder: DraftBuilder) -> None:
        self.service = service
        self.builder = builder

    def create(
        self,
        user_request: str,
        task_type: TaskType,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> TaskCreationResult:
        if not isinstance(user_request, str) or not user_request.strip():
            return TaskCreationResult("needs_input", questions=("Какую задачу нужно выполнить?",))
        try:
            draft = self.builder(user_request.strip(), task_type, context)
            questions = self._questions(draft)
            if questions:
                return TaskCreationResult("needs_input", questions=tuple(questions))
            values = self._validated_draft(draft, task_type, user_request.strip())
            task = self.service.create_task(**values)
            return TaskCreationResult(
                "success", task=task, artifact={"type": "task", "ref": task["id"]}
            )
        except TaskError as exc:
            return TaskCreationResult("failure", error=exc.as_dict())
        except (TypeError, ValueError, KeyError) as exc:
            return TaskCreationResult(
                "failure", error={"code": "invalid_draft", "message": str(exc), "details": {}}
            )

    @staticmethod
    def _questions(draft: Mapping[str, Any]) -> list[str]:
        if not isinstance(draft, Mapping):
            raise TypeError("Черновик Task должен быть объектом")
        raw = draft.get("open_questions")
        if raw is None:
            return []
        if not isinstance(raw, list) or any(not isinstance(item, str) or not item.strip() for item in raw):
            raise ValueError("open_questions должен быть списком непустых строк")
        return [item.strip() for item in raw]

    @staticmethod
    def _validated_draft(draft: Mapping[str, Any], task_type: TaskType, user_request: str) -> dict[str, Any]:
        required = ("title", "objective", "acceptance_criteria")
        for name in required:
            if name not in draft:
                raise ValueError(f"В Task Artifact отсутствует поле {name}")
        title = draft["title"]
        objective = draft["objective"]
        criteria = draft["acceptance_criteria"]
        constraints = draft.get("constraints", [])
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title должен быть непустой строкой")
        if not isinstance(objective, str) or not objective.strip():
            raise ValueError("objective должен быть непустой строкой")
        if not isinstance(criteria, list) or not criteria or any(
            not isinstance(item, str) or not item.strip() for item in criteria
        ):
            raise ValueError("acceptance_criteria должен содержать хотя бы одну непустую строку")
        if not isinstance(constraints, list) or any(
            not isinstance(item, str) or not item.strip() for item in constraints
        ):
            raise ValueError("constraints должен быть списком строк")
        return {
            "title": title.strip(),
            "task_type": task_type,
            "objective": objective.strip(),
            "original_request": user_request,
            "acceptance_criteria": [item.strip() for item in criteria],
            "constraints": [item.strip() for item in constraints],
            "target_workflow": str(draft.get("target_workflow", "development")),
            "handoff_mode": str(draft.get("handoff_mode", "deferred")),
        }
