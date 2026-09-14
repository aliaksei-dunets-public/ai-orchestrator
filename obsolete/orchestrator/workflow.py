from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


TaskMode = Literal["quick", "standard", "deep"]
RiskLevel = Literal["low", "medium", "high", "critical"]
SecurityDepth = Literal["deterministic", "semantic"]


@dataclass(frozen=True)
class ExecutionPolicy:
    mode: TaskMode
    risk: RiskLevel
    security_sensitive: bool = False
    test_design_required: bool = False
    approval_required: bool = False
    documentation_impact: bool = False

    def __post_init__(self) -> None:
        if self.mode not in {"quick", "standard", "deep"}:
            raise ValueError(f"Unsupported task mode: {self.mode}")
        if self.risk not in {"low", "medium", "high", "critical"}:
            raise ValueError(f"Unsupported risk level: {self.risk}")


@dataclass(frozen=True)
class SelectedExecutionRoute:
    steps: tuple[str, ...]
    security_depth: SecurityDepth
    independent_review: bool


def select_execution_route(policy: ExecutionPolicy) -> SelectedExecutionRoute:
    steps = ["freshness", "implement"]
    if policy.mode != "quick" or policy.test_design_required:
        steps.append("design-tests")
    steps.append("run-tests")

    if policy.mode != "quick":
        steps.append("task-review")
    semantic_code_review = (
        policy.mode != "quick"
        or policy.security_sensitive
        or policy.risk in {"high", "critical"}
    )
    if semantic_code_review:
        steps.append("code-review")

    independent_review = (
        policy.mode == "deep"
        or policy.security_sensitive
        or policy.risk in {"high", "critical"}
    )
    if independent_review:
        steps.append("independent-review")

    security_depth: SecurityDepth = (
        "semantic"
        if policy.mode == "deep"
        or policy.security_sensitive
        or policy.risk in {"high", "critical"}
        else "deterministic"
    )
    steps.append("security-review")

    if policy.approval_required:
        steps.append("approvals")
    if policy.documentation_impact:
        steps.append("documentation")
    return SelectedExecutionRoute(tuple(steps), security_depth, independent_review)
