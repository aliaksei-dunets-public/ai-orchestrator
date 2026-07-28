from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass
from typing import Mapping, Sequence

from .review import ReviewFinding, ReviewResult
from .session_report import redact


SENSITIVE_PATH_PARTS = (
    "auth",
    "security",
    "permission",
    "credential",
    "secret",
    "token",
    "crypto",
    "payment",
    ".orchestrator/memory",
    ".orchestrator/knowledge",
    "context-pack",
)
SECRET_RE = re.compile(r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*['\"]?([^\s'\"]+)")
VULNERABILITY_RULES = (
    ("SEC_EVAL", re.compile(r"\beval\s*\("), "Dynamic evaluation may execute attacker-controlled code."),
    ("SEC_SHELL", re.compile(r"shell\s*=\s*True"), "Shell command construction increases injection risk."),
    ("SEC_TLS", re.compile(r"verify\s*=\s*False"), "TLS verification is disabled."),
)


@dataclass(frozen=True)
class SecurityRoute:
    required: bool
    reasons: tuple[str, ...]


def route_security_review(changed_paths: Sequence[str], diff_text: str) -> SecurityRoute:
    reasons: list[str] = []
    for path in changed_paths:
        normalized = path.lower().replace("\\", "/")
        if any(part in normalized for part in SENSITIVE_PATH_PARTS):
            reasons.append(f"sensitive path: {path}")
    if SECRET_RE.search(diff_text):
        reasons.append("credential-like material")
    for code, pattern, _ in VULNERABILITY_RULES:
        if pattern.search(diff_text):
            reasons.append(code)
    return SecurityRoute(bool(reasons), tuple(dict.fromkeys(reasons)))


def security_review(changed_paths: Sequence[str], diff_text: str) -> ReviewResult:
    route = route_security_review(changed_paths, diff_text)
    findings: list[ReviewFinding] = []
    for code, pattern, impact in VULNERABILITY_RULES:
        match = pattern.search(diff_text)
        if match:
            findings.append(
                ReviewFinding(
                    code=code,
                    severity="high",
                    file=changed_paths[0] if changed_paths else "diff",
                    evidence=redact(match.group(0)),
                    impact=impact,
                    remediation="Replace the unsafe construct with a constrained, validated alternative.",
                    blocking=True,
                )
            )
    if SECRET_RE.search(diff_text):
        findings.append(
            ReviewFinding(
                code="SEC_CREDENTIAL",
                severity="critical",
                file=changed_paths[0] if changed_paths else "diff",
                evidence="[REDACTED credential-like value]",
                impact="A credential may be exposed in source or logs.",
                remediation="Remove and rotate the credential, then add a secret-safe configuration path.",
                blocking=True,
            )
        )
    verdict = "blocked" if any(item.severity in {"high", "critical"} for item in findings) else "approved"
    return ReviewResult("security", verdict, (), tuple(findings), "deterministic+threat-review" if route.required else "not-triggered")


def policy_allows_override(policy: Mapping[str, object]) -> bool:
    return bool(policy.get("allow_local_bypass", False))


def memory_knowledge_security_review(
    project_root: Path | str,
    *,
    source_paths: Sequence[str] = (),
    content: str = "",
    budget_chars: int = 0,
    max_budget_chars: int = 12288,
) -> ReviewResult:
    root = Path(project_root).resolve()
    findings: list[ReviewFinding] = []
    excluded = {".git", ".env", "secrets", "credentials", "proposals", "indexes", "backups"}
    for raw in source_paths:
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        try:
            relative = path.resolve().relative_to(root)
        except ValueError:
            findings.append(
                ReviewFinding(
                    "SEC_CONTEXT_PATH_ESCAPE",
                    "critical",
                    raw,
                    "source escapes project root",
                    "Untrusted external content could enter persistent memory or agent context.",
                    "Use a project-relative, allowlisted source.",
                    True,
                )
            )
            continue
        if excluded & {part.lower() for part in relative.parts}:
            findings.append(
                ReviewFinding(
                    "SEC_CONTEXT_EXCLUDED_SOURCE",
                    "high",
                    relative.as_posix(),
                    "source belongs to an excluded operational or secret tree",
                    "Derived or sensitive state could be promoted as canonical evidence.",
                    "Use an existing canonical source outside excluded trees.",
                    True,
                )
            )
    if SECRET_RE.search(content) or redact(content) != content:
        findings.append(
            ReviewFinding(
                "SEC_CONTEXT_CREDENTIAL",
                "critical",
                "context",
                "[REDACTED credential-like value]",
                "A credential could be persisted or injected into agent context.",
                "Remove and rotate the credential before creating a proposal.",
                True,
            )
        )
    if budget_chars < 0 or budget_chars > max_budget_chars:
        findings.append(
            ReviewFinding(
                "SEC_CONTEXT_UNBOUNDED",
                "high",
                "context",
                f"budget_chars={budget_chars}",
                "An unbounded context can increase cost and amplify prompt injection.",
                f"Use a budget between 0 and {max_budget_chars}.",
                True,
            )
        )
    verdict = "blocked" if findings else "approved"
    return ReviewResult("security", verdict, (), tuple(findings), "memory-knowledge-boundary")
