from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence


TestStatus = Literal["passed", "failed", "blocked"]
TEST_KINDS = {"focused", "contract", "scenario", "regression"}


class TestPlanError(ValueError):
    pass


@dataclass(frozen=True)
class TestCaseSpec:
    id: str
    criteria: tuple[str, ...]
    command: tuple[str, ...]
    kind: str = "focused"

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.command:
            raise ValueError("Test id and command are required")
        if self.kind not in TEST_KINDS:
            raise ValueError(f"Unsupported test kind: {self.kind}")


@dataclass(frozen=True)
class TestEvidence:
    test_id: str
    status: TestStatus
    command: tuple[str, ...]
    exit_code: int | None
    summary: str


def validate_test_plan(
    acceptance_criteria: Sequence[str],
    cases: Sequence[TestCaseSpec],
    *,
    fixed_bug: bool = False,
) -> None:
    criteria = {criterion.strip() for criterion in acceptance_criteria if criterion.strip()}
    covered = {criterion for case in cases for criterion in case.criteria}
    missing = sorted(criteria - covered)
    unknown = sorted(covered - criteria)
    issues: list[str] = []
    if missing:
        issues.append(f"acceptance criteria without checks: {missing}")
    if unknown:
        issues.append(f"checks reference unknown criteria: {unknown}")
    has_regression = any(case.kind == "regression" for case in cases)
    if fixed_bug and not has_regression:
        issues.append("a fixed bug requires a regression test")
    if not fixed_bug and has_regression:
        issues.append("regression tests are reserved for fixed bugs")
    if issues:
        raise TestPlanError("; ".join(issues))


def _summary(stdout: str, stderr: str, *, limit: int = 1000) -> str:
    combined = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    if not combined:
        return "Command produced no output."
    return combined[-limit:]


def run_test(
    case: TestCaseSpec,
    *,
    cwd: Path | str | None = None,
    timeout_seconds: float = 60,
) -> TestEvidence:
    try:
        completed = subprocess.run(
            list(case.command),
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        return TestEvidence(case.id, "blocked", case.command, None, f"Tool unavailable: {exc.filename}")
    except subprocess.TimeoutExpired as exc:
        output = _summary(
            exc.stdout if isinstance(exc.stdout, str) else "",
            exc.stderr if isinstance(exc.stderr, str) else "",
        )
        return TestEvidence(case.id, "blocked", case.command, None, f"Timed out after {timeout_seconds}s. {output}")
    status: TestStatus = "passed" if completed.returncode == 0 else "failed"
    return TestEvidence(
        case.id,
        status,
        case.command,
        completed.returncode,
        _summary(completed.stdout, completed.stderr),
    )
