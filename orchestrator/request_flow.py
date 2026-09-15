"""Sequential Request Router → Task Creator flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .request_router import RequestRouter, RoutingResult
from .task_creator import TaskCreationResult, TaskCreator


@dataclass(frozen=True)
class RequestFlowResult:
    route: RoutingResult
    creation: TaskCreationResult | None = None

    def as_dict(self) -> dict[str, Any]:
        value = {"route": self.route.as_dict()}
        if self.creation is not None:
            value["creation"] = self.creation.as_dict()
        return value


class RequestFlow:
    """Execute only the first graph segment; direct responses stop at Router."""

    def __init__(self, router: RequestRouter, creator: TaskCreator) -> None:
        self.router = router
        self.creator = creator

    def handle(self, user_request: str, *, context: Mapping[str, Any] | None = None) -> RequestFlowResult:
        route = self.router.route(user_request, context=context)
        if route.route == "direct_response":
            return RequestFlowResult(route=route)
        assert route.suggested_type is not None
        return RequestFlowResult(
            route=route,
            creation=self.creator.create(user_request, route.suggested_type, context=context),
        )
