"""Request routing boundary for the graph orchestrator.

The router deliberately does not solve the request.  A platform adapter (for
example, an LLM-backed classifier or a deterministic policy) supplies the
classification and this module validates the contract used by the graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping


Route = Literal["direct_response", "managed_work"]
TaskType = Literal[
    "implementation", "analysis", "investigation", "incident", "exploration"
]

TASK_TYPES = frozenset({"implementation", "analysis", "investigation", "incident", "exploration"})
ROUTES = frozenset({"direct_response", "managed_work"})


class RoutingError(ValueError):
    """Raised when an adapter returns an invalid routing result."""


@dataclass(frozen=True)
class RoutingResult:
    """Validated result of the Request Router node."""

    route: Route
    suggested_type: TaskType | None
    confidence: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "suggested_type": self.suggested_type,
            "confidence": self.confidence,
        }


Classifier = Callable[[str, Mapping[str, Any] | None], RoutingResult | Mapping[str, Any]]


class RequestRouter:
    """Validate an adapter's classification without executing managed work."""

    def __init__(self, classifier: Classifier) -> None:
        self.classifier = classifier

    def route(self, user_request: str, *, context: Mapping[str, Any] | None = None) -> RoutingResult:
        if not isinstance(user_request, str) or not user_request.strip():
            raise RoutingError("user_request должен быть непустой строкой")
        raw = self.classifier(user_request.strip(), context)
        return self._validate(raw)

    @staticmethod
    def _validate(raw: RoutingResult | Mapping[str, Any]) -> RoutingResult:
        if isinstance(raw, RoutingResult):
            result = raw
        elif isinstance(raw, Mapping):
            result = RoutingResult(
                route=raw.get("route"),  # type: ignore[arg-type]
                suggested_type=raw.get("suggested_type"),  # type: ignore[arg-type]
                confidence=raw.get("confidence"),  # type: ignore[arg-type]
            )
        else:
            raise RoutingError("Результат Router должен быть объектом")

        if result.route not in ROUTES:
            raise RoutingError("route должен быть direct_response или managed_work")
        if not isinstance(result.confidence, str) or not result.confidence.strip():
            raise RoutingError("confidence должен быть непустой строкой")
        if result.route == "direct_response" and result.suggested_type is not None:
            raise RoutingError("Для direct_response suggested_type должен быть null")
        if result.route == "managed_work" and result.suggested_type not in TASK_TYPES:
            raise RoutingError("Для managed_work нужен поддерживаемый suggested_type")
        return result
