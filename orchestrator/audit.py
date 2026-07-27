from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal


Severity = Literal["info", "low", "medium", "high", "critical"]
NORMATIVE_RE = re.compile(r"^\s*NORMATIVE\s+([A-Za-z0-9_.-]+)\s*=\s*(.+?)\s*$")
EXPECT_TEST_RE = re.compile(r"^\s*AUDIT_EXPECT_TEST\s*:\s*([A-Za-z0-9_.-]+)\s*$")
SKILL_REFERENCE_RE = re.compile(r"^\s*skill:\s*([A-Za-z0-9_.-]+)\s*$", re.MULTILINE)
WORKFLOW_REFERENCE_RE = re.compile(r"^\s*workflow:\s*([A-Za-z0-9_.-]+)\s*$", re.MULTILINE)
STEP_ID_RE = re.compile(r"^\s*-\s+id:\s*([A-Za-z0-9_.-]+)\s*$", re.MULTILINE)
DEPENDENCY_RE = re.compile(r"^\s*(?:depends_on|on_failure):\s*(.+?)\s*$", re.MULTILINE)
SKILL_NAME_RE = re.compile(r"(?m)^name:\s*([A-Za-z0-9_.-]+)\s*$")


@dataclass(frozen=True)
class AuditFinding:
    code: str
    severity: Severity
    message: str
    evidence: tuple[str, ...]
    proposal: str
    fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AuditReport:
    findings: tuple[AuditFinding, ...]

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, "findings": [item.to_dict() for item in self.findings]}


def _finding(code: str, severity: Severity, message: str, evidence: Iterable[str], proposal: str) -> AuditFinding:
    pointers = tuple(sorted(set(evidence)))
    if not pointers:
        raise ValueError("Audit finding requires evidence")
    digest = hashlib.sha256(
        json.dumps([code, message, pointers], ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return AuditFinding(code, severity, message, pointers, proposal, digest)


def audit_repository(root: Path | str, *, known_fingerprints: Iterable[str] = ()) -> AuditReport:
    project = Path(root).resolve()
    known = set(known_fingerprints)
    findings: list[AuditFinding] = []
    normative: dict[str, tuple[str, str]] = {}
    expected_tests: list[tuple[str, str]] = []

    for document in sorted((project / "docs").rglob("*.md")) if (project / "docs").exists() else []:
        relative = document.relative_to(project).as_posix()
        for number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
            match = NORMATIVE_RE.match(line)
            if match:
                key, value = match.groups()
                pointer = f"{relative}:{number}"
                previous = normative.get(key)
                if previous and previous[0] != value:
                    findings.append(
                        _finding(
                            "CONTRADICTORY_RULE",
                            "high",
                            f"Normative rule {key} has conflicting values.",
                            (previous[1], pointer),
                            "Choose one canonical value and update every dependent contract.",
                        )
                    )
                else:
                    normative[key] = (value, pointer)
            expected = EXPECT_TEST_RE.match(line)
            if expected:
                expected_tests.append((expected.group(1), f"{relative}:{number}"))

    skill_registry = project / "registries/skills.json"
    registered_skills: set[str] = set()
    if skill_registry.exists():
        payload = json.loads(skill_registry.read_text(encoding="utf-8"))
        skill_entries = payload.get("entries", [])
        ids = [str(entry.get("id")) for entry in skill_entries if isinstance(entry, dict)]
        paths = [str(entry.get("path")) for entry in skill_entries if isinstance(entry, dict)]
        for duplicate in sorted({item for item in ids if ids.count(item) > 1}):
            findings.append(
                _finding(
                    "DUPLICATE_SKILL_ID",
                    "high",
                    f"Skill id {duplicate} is registered more than once.",
                    (f"registries/skills.json#{duplicate}",),
                    "Keep one canonical registry entry for the skill id.",
                )
            )
        for duplicate in sorted({item for item in paths if paths.count(item) > 1}):
            findings.append(
                _finding(
                    "DUPLICATE_SKILL_PATH",
                    "medium",
                    f"Skill path {duplicate} is registered more than once.",
                    (f"registries/skills.json#{duplicate}",),
                    "Keep one logical owner for the canonical skill path.",
                )
            )
        for entry in skill_entries:
            if not isinstance(entry, dict):
                continue
            skill_id = str(entry.get("id"))
            registered_skills.add(skill_id)
            target = project / str(entry.get("path"))
            if not target.is_file():
                findings.append(
                    _finding(
                        "MISSING_SKILL",
                        "high",
                        f"Registered skill {skill_id} does not exist.",
                        (f"registries/skills.json#{skill_id}",),
                        "Restore the canonical skill or remove its registry entry through an approved task.",
                    )
                )
                continue
            name = SKILL_NAME_RE.search(target.read_text(encoding="utf-8"))
            if not name or name.group(1) != skill_id:
                findings.append(
                    _finding(
                        "SKILL_ID_MISMATCH",
                        "high",
                        f"Registered skill {skill_id} disagrees with its frontmatter name.",
                        (target.relative_to(project).as_posix(), f"registries/skills.json#{skill_id}"),
                        "Make the registry id, directory ownership and skill frontmatter name identical.",
                    )
                )
        canonical_skills = project / "skills"
        if canonical_skills.exists():
            for skill_file in sorted(canonical_skills.rglob("SKILL.md")):
                relative = skill_file.relative_to(project).as_posix()
                name = SKILL_NAME_RE.search(skill_file.read_text(encoding="utf-8"))
                if name and name.group(1) not in registered_skills:
                    findings.append(
                        _finding(
                            "UNREGISTERED_SKILL",
                            "medium",
                            f"Canonical skill {name.group(1)} is not registered.",
                            (relative,),
                            "Register the skill or remove it from the canonical skills directory.",
                        )
                    )

    workflow_registry = project / "registries/workflows.json"
    registered_workflows: set[str] = set()
    if workflow_registry.exists():
        payload = json.loads(workflow_registry.read_text(encoding="utf-8"))
        registered_workflows = {
            str(entry.get("id"))
            for entry in payload.get("entries", [])
            if isinstance(entry, dict)
        }
        for entry in payload.get("entries", []):
            target = project / entry["path"]
            if not target.is_file():
                findings.append(
                    _finding(
                        "DEAD_WORKFLOW",
                        "high",
                        f"Registered workflow {entry['id']} does not exist.",
                        (f"registries/workflows.json#{entry['id']}",),
                        "Restore the workflow or remove its registry entry through an approved task.",
                    )
                )
                continue
            workflow_text = target.read_text(encoding="utf-8")
            pointer = target.relative_to(project).as_posix()
            for skill in SKILL_REFERENCE_RE.findall(workflow_text):
                if skill not in registered_skills:
                    findings.append(
                        _finding(
                            "DANGLING_SKILL_REFERENCE",
                            "high",
                            f"Workflow {entry['id']} references unknown skill {skill}.",
                            (pointer,),
                            "Register the skill or update the workflow reference.",
                        )
                    )
            for workflow in WORKFLOW_REFERENCE_RE.findall(workflow_text):
                if workflow not in registered_workflows:
                    findings.append(
                        _finding(
                            "DANGLING_WORKFLOW_REFERENCE",
                            "high",
                            f"Workflow {entry['id']} references unknown workflow {workflow}.",
                            (pointer,),
                            "Register the nested workflow or update the reference.",
                        )
                    )
            step_ids = STEP_ID_RE.findall(workflow_text)
            for duplicate in sorted({item for item in step_ids if step_ids.count(item) > 1}):
                findings.append(
                    _finding(
                        "DUPLICATE_WORKFLOW_STEP",
                        "high",
                        f"Workflow {entry['id']} repeats step id {duplicate}.",
                        (pointer,),
                        "Give every workflow step a unique id.",
                    )
                )
            for raw_dependencies in DEPENDENCY_RE.findall(workflow_text):
                dependencies = [
                    item.strip().strip("'\"")
                    for item in raw_dependencies.strip("[]").split(",")
                    if item.strip()
                ]
                for dependency in dependencies:
                    if dependency not in step_ids:
                        findings.append(
                            _finding(
                                "DANGLING_WORKFLOW_STEP",
                                "high",
                                f"Workflow {entry['id']} references unknown step {dependency}.",
                                (pointer,),
                                "Fix the dependency or failure target to reference an existing step.",
                            )
                        )

    tests_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted((project / "tests").rglob("test_*.py"))
    ) if (project / "tests").exists() else ""
    for subject, pointer in expected_tests:
        if subject not in tests_text:
            findings.append(
                _finding(
                    "MISSING_TEST",
                    "medium",
                    f"Expected test subject {subject} has no test reference.",
                    (pointer,),
                    f"Add an executable test that references {subject}.",
                )
            )

    orchestrator_root = project / "orchestrator"
    if orchestrator_root.exists() and (project / "tests").exists():
        for module in sorted(orchestrator_root.glob("*.py")):
            if module.name in {"__init__.py", "__main__.py"}:
                continue
            if module.stem not in tests_text:
                findings.append(
                    _finding(
                        "UNTESTED_RUNTIME_MODULE",
                        "medium",
                        f"Runtime module {module.stem} has no direct test reference.",
                        (module.relative_to(project).as_posix(),),
                        f"Add a focused test that exercises orchestrator.{module.stem}.",
                    )
                )

    schemas_root = project / "config/schemas"
    if schemas_root.exists():
        for schema_path in sorted(schemas_root.glob("*.json")):
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                findings.append(
                    _finding(
                        "SCHEMA_DRAFT_DRIFT",
                        "high",
                        f"Schema {schema_path.name} does not declare Draft 2020-12.",
                        (schema_path.relative_to(project).as_posix(),),
                        "Migrate the schema explicitly and update contract fixtures.",
                    )
                )

    unique: dict[str, AuditFinding] = {}
    for finding in findings:
        if finding.fingerprint not in known:
            unique[finding.fingerprint] = finding
    return AuditReport(tuple(sorted(unique.values(), key=lambda item: (item.severity, item.code, item.fingerprint))))
