from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Mapping

from .health import run_health_checks
from .knowledge import effective_graph, rebuild_indexes
from .knowledge_bootstrap import prepare_graph_update
from .onboarding import ProjectFacts, collect_facts, render_project_context
from .ontology import load_core_ontology, load_project_ontology, merge_ontology
from .platforms import load_platform_profile
from .technologies import detect_technology, load_technology_profile


CORE_REQUIRED_PATHS = (
    "orchestrator",
    "config",
    "profiles",
    "registries",
    "skills",
    "workflows",
)
ALLOWED_ANSWER_KEYS = {
    "platform_profile",
    "technology_profiles",
    "external_core_path",
    "knowledge_graph",
}
CREDENTIAL_KEY_RE = re.compile(
    r"(?:credential|password|passwd|secret|token|api[_-]?key|private[_-]?key)",
    re.IGNORECASE,
)
CREDENTIAL_VALUE_RE = re.compile(
    r"(?:-----BEGIN [A-Z ]+PRIVATE KEY-----|(?:gh[opusr]_|sk-)[A-Za-z0-9_-]{12,})"
)
VERSION_RE = re.compile(r'__version__\s*=\s*["\']([^"\']+)["\']')
MANAGED_START = "<!-- ai-orchestrator:start -->"
MANAGED_END = "<!-- ai-orchestrator:end -->"
GITIGNORE_START = "# AI Orchestrator operational state: start"
GITIGNORE_END = "# AI Orchestrator operational state: end"


class OnboardingError(ValueError):
    pass


@dataclass(frozen=True)
class Choice:
    id: str
    label: str
    description: str
    recommended: bool = False

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.label.strip() or not self.description.strip():
            raise ValueError("choice id, label and description are required")


@dataclass(frozen=True)
class Question:
    id: str
    prompt: str
    choices: tuple[Choice, ...]

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.prompt.strip():
            raise ValueError("question id and prompt are required")
        if len(self.choices) < 2:
            raise ValueError("question requires at least two choices")
        identifiers = [choice.id for choice in self.choices]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("question contains duplicate choice ids")
        if sum(choice.recommended for choice in self.choices) > 1:
            raise ValueError("question has more than one recommended choice")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "choices": [asdict(choice) for choice in self.choices],
        }


@dataclass(frozen=True)
class PlannedChange:
    path: str
    before_sha256: str | None
    after_sha256: str
    diff: str
    content: str

    def to_dict(self, *, include_content: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
            "path": self.path,
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "diff": self.diff,
        }
        if include_content:
            payload["content"] = self.content
        return payload


@dataclass(frozen=True)
class OnboardingInspection:
    status: str
    core_root: str
    target_root: str
    core_version: str
    facts: ProjectFacts
    platform_profile: str | None
    technology_profiles: tuple[str, ...]
    questions: tuple[Question, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "status": self.status,
            "core_root": self.core_root,
            "target_root": self.target_root,
            "core_version": self.core_version,
            "facts": asdict(self.facts),
            "platform_profile": self.platform_profile,
            "technology_profiles": list(self.technology_profiles),
            "questions": [question.to_dict() for question in self.questions],
        }


@dataclass(frozen=True)
class OnboardingPlan:
    status: str
    core_root: str
    target_root: str
    core_path: str
    core_version: str
    platform_profile: str
    technology_profiles: tuple[str, ...]
    questions: tuple[Question, ...]
    changes: tuple[PlannedChange, ...]
    rollback_paths: tuple[str, ...]
    validation_steps: tuple[str, ...]
    target_fingerprint: str
    plan_hash: str

    def to_dict(self, *, include_content: bool = False) -> dict[str, object]:
        return {
            "schema_version": 1,
            "status": self.status,
            "core_root": self.core_root,
            "target_root": self.target_root,
            "core_path": self.core_path,
            "core_version": self.core_version,
            "platform_profile": self.platform_profile,
            "technology_profiles": list(self.technology_profiles),
            "questions": [question.to_dict() for question in self.questions],
            "changes": [
                change.to_dict(include_content=include_content)
                for change in self.changes
            ],
            "rollback_paths": list(self.rollback_paths),
            "validation_steps": list(self.validation_steps),
            "target_fingerprint": self.target_fingerprint,
            "plan_hash": self.plan_hash,
        }


@dataclass(frozen=True)
class OnboardingApplyResult:
    status: str
    plan_hash: str
    changed_paths: tuple[str, ...]
    findings: tuple[str, ...]
    report_path: str
    rollback_verified: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "status": self.status,
            "plan_hash": self.plan_hash,
            "changed_paths": list(self.changed_paths),
            "findings": list(self.findings),
            "report_path": self.report_path,
            "rollback_verified": self.rollback_verified,
        }


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _canonical_hash(payload: object) -> str:
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_text(rendered)


def resolve_core_root(skill_path: Path | str) -> Path:
    skill = Path(skill_path).resolve()
    if skill.name != "SKILL.md" or skill.parent.name != "project-onboarding":
        raise OnboardingError(
            "skill path must identify project-onboarding/SKILL.md"
        )
    skills_root = next(
        (parent for parent in skill.parents if parent.name == "skills"),
        None,
    )
    if skills_root is None:
        raise OnboardingError("skill path is not inside a skills directory")
    core = skills_root.parent
    missing = [relative for relative in CORE_REQUIRED_PATHS if not (core / relative).exists()]
    if missing:
        raise OnboardingError(f"core root is incomplete, missing={missing}")
    return core


def _core_version(core: Path) -> str:
    init = core / "orchestrator/__init__.py"
    match = VERSION_RE.search(init.read_text(encoding="utf-8"))
    if not match:
        raise OnboardingError("core version is not declared")
    return match.group(1)


def _validate_answers(answers: Mapping[str, object]) -> dict[str, object]:
    result = dict(answers)
    for key in result:
        if CREDENTIAL_KEY_RE.search(str(key)):
            raise OnboardingError(f"credential-like answer key is forbidden: {key}")

    def validate_value(value: object) -> None:
        if isinstance(value, str):
            if CREDENTIAL_VALUE_RE.search(value):
                raise OnboardingError("credential-like answer value is forbidden")
            return
        if isinstance(value, Mapping):
            for nested_key, nested_value in value.items():
                if CREDENTIAL_KEY_RE.search(str(nested_key)):
                    raise OnboardingError("credential-like answer key is forbidden")
                validate_value(nested_value)
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                validate_value(item)

    for value in result.values():
        validate_value(value)
    unknown = set(result) - ALLOWED_ANSWER_KEYS
    if unknown:
        raise OnboardingError(f"unknown onboarding answers: {sorted(unknown)}")
    return result


def _platform_profiles(core: Path) -> dict[str, dict[str, object]]:
    profiles = [
        load_platform_profile(path)
        for path in sorted((core / "profiles/platforms").glob("*.yaml"))
    ]
    return {str(profile["id"]): profile for profile in profiles}


def _technology_profiles(
    core: Path,
    target: Path,
) -> tuple[dict[str, dict[str, object]], dict[str, float]]:
    profiles: dict[str, dict[str, object]] = {}
    confidence: dict[str, float] = {}
    for path in sorted((core / "profiles/technologies").glob("*.yaml")):
        profile = load_technology_profile(path)
        profile_id = str(profile["id"])
        profiles[profile_id] = profile
        confidence[profile_id] = detect_technology(target, profile).confidence
    return profiles, confidence


def _platform_question(profiles: Mapping[str, Mapping[str, object]]) -> Question:
    ordered = sorted(
        profiles.values(),
        key=lambda item: (
            0 if item["maturity"] == "stable" else 1,
            int(item["adapter_order"]),
            str(item["id"]),
        ),
    )
    recommended = str(ordered[0]["id"]) if ordered else None
    return Question(
        "platform_profile",
        "Which platform profile should the agent activate?",
        tuple(
            Choice(
                str(profile["id"]),
                str(profile["id"]),
                (
                    f"Use the {profile['maturity']} profile with "
                    f"{profile['validation']['native_smoke']} native smoke status."
                ),
                str(profile["id"]) == recommended,
            )
            for profile in ordered
        ),
    )


def _detect_platform(
    target: Path,
    profiles: Mapping[str, Mapping[str, object]],
) -> str | None:
    candidates: list[str] = []
    for profile_id, profile in profiles.items():
        onboarding = profile.get("onboarding")
        if not isinstance(onboarding, Mapping):
            continue
        instruction_target = onboarding.get("instruction_target")
        projection_target = onboarding.get("skill_projection_target")
        evidence = False
        if isinstance(instruction_target, str):
            evidence = _safe_target(target, instruction_target).is_file()
        if not evidence and isinstance(projection_target, str):
            projection_parent = _safe_target(target, projection_target).parent
            evidence = projection_parent.is_dir()
        if evidence:
            candidates.append(profile_id)
    return candidates[0] if len(candidates) == 1 else None


def _technology_question(
    profiles: Mapping[str, Mapping[str, object]],
    confidence: Mapping[str, float],
) -> Question:
    ordered = sorted(
        profiles,
        key=lambda profile_id: (-confidence[profile_id], profile_id),
    )
    recommended = ordered[0] if ordered else None
    return Question(
        "technology_profiles",
        "Which technology profile should be activated?",
        tuple(
            Choice(
                profile_id,
                profile_id,
                f"Activate {profile_id}; detection confidence={confidence[profile_id]:.2f}.",
                profile_id == recommended,
            )
            for profile_id in ordered
        ),
    )


def _external_core_question(core: Path) -> Question:
    return Question(
        "external_core_path",
        f"Core is outside the target project at {core}. Continue with a non-portable path?",
        (
            Choice(
                "confirm",
                "Use external core",
                "Store the absolute core path; other machines may need a different path.",
                False,
            ),
            Choice(
                "cancel",
                "Cancel",
                "Do not create a non-portable project configuration.",
                True,
            ),
        ),
    )


def inspect_onboarding(
    skill_path: Path | str,
    target_root: Path | str,
    answers: Mapping[str, object] | None = None,
) -> OnboardingInspection:
    resolved_answers = _validate_answers(answers or {})
    core = resolve_core_root(skill_path)
    target = Path(target_root).resolve()
    if not target.is_dir():
        raise OnboardingError(f"target project does not exist: {target}")

    questions: list[Question] = []
    platforms = _platform_profiles(core)
    platform_answer = resolved_answers.get("platform_profile")
    platform: str | None = None
    if platform_answer is None:
        platform = _detect_platform(target, platforms)
        if platform is None:
            questions.append(_platform_question(platforms))
    elif not isinstance(platform_answer, str) or platform_answer not in platforms:
        raise OnboardingError("unknown platform profile")
    else:
        platform = platform_answer

    technologies, confidence = _technology_profiles(core, target)
    technology_answer = resolved_answers.get("technology_profiles")
    selected_technologies: tuple[str, ...]
    if technology_answer is not None:
        raw = (
            [technology_answer]
            if isinstance(technology_answer, str)
            else list(technology_answer)
            if isinstance(technology_answer, (list, tuple))
            else []
        )
        if not raw or any(not isinstance(item, str) or item not in technologies for item in raw):
            raise OnboardingError("unknown technology profiles")
        selected_technologies = tuple(dict.fromkeys(raw))
    else:
        detected = tuple(
            profile_id
            for profile_id, value in sorted(confidence.items())
            if value > 0
        )
        if len(detected) == 1:
            selected_technologies = detected
        else:
            selected_technologies = ()
            questions.append(_technology_question(technologies, confidence))

    try:
        core.relative_to(target)
    except ValueError:
        external_answer = resolved_answers.get("external_core_path")
        if external_answer is None:
            questions.append(_external_core_question(core))
        elif external_answer == "cancel":
            return OnboardingInspection(
                "cancelled",
                str(core),
                str(target),
                _core_version(core),
                collect_facts(target),
                platform,
                selected_technologies,
                (),
            )
        elif external_answer != "confirm":
            raise OnboardingError(
                f"unknown external_core_path answer: {external_answer}"
            )

    return OnboardingInspection(
        "needs_input" if questions else "ready",
        str(core),
        str(target),
        _core_version(core),
        collect_facts(target),
        platform,
        selected_technologies,
        tuple(questions),
    )


def _managed_block(existing: str, block: str) -> str:
    start = existing.find(MANAGED_START)
    end = existing.find(MANAGED_END)
    if (start < 0) != (end < 0) or (start >= 0 and end < start):
        raise OnboardingError("conflicting AI Orchestrator ownership markers")
    rendered = f"{MANAGED_START}\n{block.rstrip()}\n{MANAGED_END}"
    if start >= 0:
        return existing[:start] + rendered + existing[end + len(MANAGED_END) :]
    if not existing:
        return rendered + "\n"
    separator = "" if existing.endswith("\n\n") else "\n" if existing.endswith("\n") else "\n\n"
    return existing + separator + rendered + "\n"


def _gitignore_content(existing: str) -> str:
    block = "\n".join(
        (
            ".orchestrator/tasks/tasks.json",
            ".orchestrator/tasks/*.tmp",
            ".orchestrator/tasks/checkpoints/",
            ".orchestrator/telemetry/",
            ".orchestrator/onboarding/session.json",
            ".orchestrator/onboarding/backups/",
            ".orchestrator/memory/proposals/",
            ".orchestrator/knowledge/indexes/",
            ".orchestrator/migrations/backups/",
        )
    )
    start = existing.find(GITIGNORE_START)
    end = existing.find(GITIGNORE_END)
    if (start < 0) != (end < 0) or (start >= 0 and end < start):
        raise OnboardingError("conflicting AI Orchestrator gitignore markers")
    rendered = f"{GITIGNORE_START}\n{block}\n{GITIGNORE_END}"
    if start >= 0:
        return existing[:start] + rendered + existing[end + len(GITIGNORE_END) :]
    if not existing:
        return rendered + "\n"
    separator = "" if existing.endswith("\n\n") else "\n" if existing.endswith("\n") else "\n\n"
    return existing + separator + rendered + "\n"


def _safe_target(target: Path, relative: str) -> Path:
    candidate = (target / relative).resolve()
    try:
        candidate.relative_to(target)
    except ValueError as exc:
        raise OnboardingError(f"planned path escapes target project: {relative}") from exc
    return candidate


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except (OSError, UnicodeError) as exc:
        raise OnboardingError(f"cannot read planned file {path}: {exc}") from exc


def _change(target: Path, relative: str, content: str) -> PlannedChange:
    path = _safe_target(target, relative)
    existing = _read_text(path)
    before_hash = _sha256_bytes(path.read_bytes()) if path.exists() else None
    diff = "".join(
        difflib.unified_diff(
            existing.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=relative,
            tofile=relative,
        )
    )
    return PlannedChange(
        relative.replace("\\", "/"),
        before_hash,
        _sha256_text(content),
        diff,
        content,
    )


def _current_digest(path: Path) -> str | None:
    if not path.exists():
        return None
    if not path.is_file():
        raise OnboardingError(f"expected a file path: {path}")
    return _sha256_bytes(path.read_bytes())


def _core_path_for_config(core: Path, target: Path) -> str:
    try:
        return core.relative_to(target).as_posix()
    except ValueError:
        return str(core)


def plan_onboarding(
    skill_path: Path | str,
    target_root: Path | str,
    answers: Mapping[str, object] | None = None,
) -> OnboardingInspection | OnboardingPlan:
    resolved_answers = _validate_answers(answers or {})
    inspection = inspect_onboarding(skill_path, target_root, answers)
    if inspection.status != "ready":
        return inspection

    core = Path(inspection.core_root)
    target = Path(inspection.target_root)
    skill_relative = Path(skill_path).resolve().relative_to(core).as_posix()
    assert inspection.platform_profile is not None
    platform = _platform_profiles(core)[inspection.platform_profile]
    onboarding = platform["onboarding"]
    assert isinstance(onboarding, Mapping)
    core_path = _core_path_for_config(core, target)
    config = {
        "schema_version": 1,
        "core_path": core_path,
        "core_mode": "in_place",
        "core_version": inspection.core_version,
        "platform_profile": inspection.platform_profile,
        "technology_profiles": list(inspection.technology_profiles),
        "memory_knowledge": {
            "memory_entries": ".orchestrator/memory/entries.jsonl",
            "memory_events": ".orchestrator/memory/events.jsonl",
            "memory_approvals": ".orchestrator/memory/approvals.jsonl",
            "knowledge_ontology": ".orchestrator/knowledge/ontology.json",
            "knowledge_nodes": ".orchestrator/knowledge/nodes.jsonl",
            "knowledge_edges": ".orchestrator/knowledge/edges.jsonl",
            "index_directory": ".orchestrator/knowledge/indexes",
            "knowledge_bootstrap_schema": "config/schemas/knowledge-bootstrap.schema.json",
            "knowledge_curator_skill": "knowledge-curator",
        },
    }

    changes: list[PlannedChange] = []

    def add_change(relative: str, content: str) -> None:
        change = _change(target, relative, content)
        if change.diff or change.before_sha256 is None:
            changes.append(change)

    config_content = json.dumps(
        config,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    add_change(".orchestrator/config.json", config_content)

    context_path = _safe_target(target, ".orchestrator/project-context.md")
    existing_context = _read_text(context_path)
    context_content = render_project_context(
        inspection.facts,
        existing=existing_context,
    )
    add_change(".orchestrator/project-context.md", context_content)

    for relative in ("docs/INDEX.md", "docs/documentation-policy.md"):
        destination = _safe_target(target, relative)
        if destination.exists():
            continue
        template = core / "templates" / "documentation" / Path(relative).name
        add_change(relative, template.read_text(encoding="utf-8"))

    for relative in (
        ".orchestrator/memory/entries.jsonl",
        ".orchestrator/memory/events.jsonl",
        ".orchestrator/memory/approvals.jsonl",
    ):
        add_change(relative, _read_text(_safe_target(target, relative)))
    ontology_path = ".orchestrator/knowledge/ontology.json"
    ontology_existing = _read_text(_safe_target(target, ontology_path))
    if not ontology_existing:
        ontology_existing = json.dumps(
            {
                "schema_version": 1,
                "immutable": False,
                "node_kinds": [],
                "relations": [],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
    add_change(ontology_path, ontology_existing)

    try:
        ontology = merge_ontology(
            load_core_ontology(core / "config/knowledge-ontology.json"),
            load_project_ontology(_safe_target(target, ontology_path)),
        )
        graph_update = prepare_graph_update(
            target,
            _safe_target(target, ".orchestrator/knowledge/nodes.jsonl"),
            _safe_target(target, ".orchestrator/knowledge/edges.jsonl"),
            resolved_answers.get("knowledge_graph"),
            ontology=ontology,
        )
    except Exception as exc:
        raise OnboardingError(f"invalid knowledge graph proposal: {exc}") from exc
    add_change(
        ".orchestrator/knowledge/nodes.jsonl",
        graph_update.nodes_content,
    )
    add_change(
        ".orchestrator/knowledge/edges.jsonl",
        graph_update.edges_content,
    )

    instruction_target = onboarding["instruction_target"]
    bootstrap = "\n".join(
        (
            f"AI Orchestrator core: `{core_path}`",
            "Load `.orchestrator/config.json` before task routing.",
            f"Use `{core_path}/{skill_relative}` for onboarding.",
            "Do not edit AI Orchestrator managed blocks manually.",
        )
    )
    if isinstance(instruction_target, str):
        instruction_path = _safe_target(target, instruction_target)
        instruction_content = _managed_block(
            _read_text(instruction_path),
            bootstrap,
        )
        add_change(instruction_target, instruction_content)

    projection_target = str(onboarding["skill_projection_target"]).rstrip("/")
    projection_content = (
        "---\n"
        "name: project-onboarding\n"
        "description: Route project onboarding to the canonical in-place AI Orchestrator skill.\n"
        "---\n\n"
        f"Load and follow `{core_path}/{skill_relative}`.\n"
    )
    add_change(
        f"{projection_target}/SKILL.md",
        projection_content,
    )
    add_change(
        ".gitignore",
        _gitignore_content(_read_text(target / ".gitignore")),
    )

    fingerprint_payload = {
        "facts": asdict(inspection.facts),
        "inputs": [
            {
                "path": change.path,
                "before_sha256": change.before_sha256,
            }
            for change in changes
        ],
    }
    target_fingerprint = _canonical_hash(fingerprint_payload)
    plan_payload = {
        "core_path": core_path,
        "core_version": inspection.core_version,
        "platform_profile": inspection.platform_profile,
        "technology_profiles": list(inspection.technology_profiles),
        "target_fingerprint": target_fingerprint,
        "changes": [
            {
                "path": change.path,
                "before_sha256": change.before_sha256,
                "after_sha256": change.after_sha256,
            }
            for change in changes
        ],
        "rollback_on_error": True,
    }
    plan_hash = _canonical_hash(plan_payload)
    return OnboardingPlan(
        "preview_ready",
        str(core),
        str(target),
        core_path,
        inspection.core_version,
        inspection.platform_profile,
        inspection.technology_profiles,
        (),
        tuple(changes),
        tuple(change.path for change in changes),
        (
            "project-config",
            "managed-instructions",
            "core-health",
            "task-registry-health",
            "knowledge-graph",
            "idempotency",
        ),
        target_fingerprint,
        plan_hash,
    )


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    _atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _rebuild_target_knowledge_index(target: Path) -> None:
    rebuild_indexes(
        _safe_target(target, ".orchestrator/knowledge/nodes.jsonl"),
        _safe_target(target, ".orchestrator/knowledge/edges.jsonl"),
        _safe_target(target, ".orchestrator/knowledge/indexes/index.json"),
    )


def _create_backup(target: Path, plan: OnboardingPlan, session_id: str) -> Path:
    backup_root = target / ".orchestrator/onboarding/backups" / session_id
    manifest_path = backup_root / "manifest.json"
    entries: list[dict[str, object]] = []
    for change in plan.changes:
        source = _safe_target(target, change.path)
        backup_relative = f"files/{change.path}"
        entry: dict[str, object] = {
            "path": change.path,
            "existed": source.is_file(),
            "before_sha256": change.before_sha256,
            "after_sha256": change.after_sha256,
            "backup": backup_relative if source.is_file() else None,
        }
        if source.is_file():
            if _current_digest(source) != change.before_sha256:
                raise OnboardingError(
                    f"planned input changed before backup: {change.path}"
                )
            backup = backup_root / backup_relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
            if _current_digest(backup) != change.before_sha256:
                raise OnboardingError(
                    f"backup verification failed before apply: {change.path}"
                )
        elif change.before_sha256 is not None:
            raise OnboardingError(
                f"planned input disappeared before backup: {change.path}"
            )
        entries.append(entry)
    _write_json(
        manifest_path,
        {
            "schema_version": 1,
            "session_id": session_id,
            "target_root": str(target),
            "plan_hash": plan.plan_hash,
            "entries": entries,
        },
    )
    return manifest_path


def _restore_backup(target: Path, manifest_path: Path) -> bool:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    backup_root = manifest_path.parent
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise OnboardingError("rollback manifest entries are invalid")
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise OnboardingError("rollback manifest entry is invalid")
        destination = _safe_target(target, entry["path"])
        current = _current_digest(destination)
        allowed = {
            value
            for value in (
                entry.get("before_sha256"),
                entry.get("after_sha256"),
            )
            if isinstance(value, str)
        }
        if current is not None and current not in allowed:
            raise OnboardingError(
                f"rollback target changed since onboarding: {entry['path']}"
            )
        if current is None and entry.get("existed"):
            raise OnboardingError(
                f"rollback target disappeared since onboarding: {entry['path']}"
            )
    for entry in reversed(entries):
        destination = _safe_target(target, entry["path"])
        if entry.get("existed"):
            backup_name = entry.get("backup")
            if not isinstance(backup_name, str):
                raise OnboardingError("rollback backup path is missing")
            backup = (backup_root / backup_name).resolve()
            try:
                backup.relative_to(backup_root.resolve())
            except ValueError as exc:
                raise OnboardingError("rollback backup escapes backup root") from exc
            if not backup.is_file():
                raise OnboardingError(f"rollback backup is missing: {backup_name}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(f"{destination.name}.{os.getpid()}.tmp")
            try:
                shutil.copy2(backup, temporary)
                os.replace(temporary, destination)
            finally:
                if temporary.exists():
                    temporary.unlink()
        elif destination.exists():
            if not destination.is_file():
                raise OnboardingError(
                    f"rollback refuses to remove non-file path: {entry['path']}"
                )
            destination.unlink()

    for entry in entries:
        destination = _safe_target(target, str(entry["path"]))
        expected = entry.get("before_sha256")
        if entry.get("existed"):
            if not destination.is_file() or _sha256_bytes(destination.read_bytes()) != expected:
                return False
        elif destination.exists():
            return False
    return True


def _default_validation(
    core: Path,
    target: Path,
    plan: OnboardingPlan,
    *,
    skill_path: Path | str,
    answers: Mapping[str, object],
) -> tuple[str, ...]:
    findings: list[str] = []
    try:
        config = json.loads(
            (target / ".orchestrator/config.json").read_text(encoding="utf-8")
        )
        expected_config = {
            "schema_version": 1,
            "core_path": plan.core_path,
            "core_mode": "in_place",
            "core_version": plan.core_version,
            "platform_profile": plan.platform_profile,
            "technology_profiles": list(plan.technology_profiles),
            "memory_knowledge": {
                "memory_entries": ".orchestrator/memory/entries.jsonl",
                "memory_events": ".orchestrator/memory/events.jsonl",
                "memory_approvals": ".orchestrator/memory/approvals.jsonl",
                "knowledge_ontology": ".orchestrator/knowledge/ontology.json",
                "knowledge_nodes": ".orchestrator/knowledge/nodes.jsonl",
                "knowledge_edges": ".orchestrator/knowledge/edges.jsonl",
                "index_directory": ".orchestrator/knowledge/indexes",
                "knowledge_bootstrap_schema": "config/schemas/knowledge-bootstrap.schema.json",
                "knowledge_curator_skill": "knowledge-curator",
            },
        }
        if config != expected_config:
            findings.append("ERROR project configuration does not match approved plan")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        findings.append(f"ERROR project configuration is unreadable: {exc}")

    for relative in (
        ".orchestrator/memory/entries.jsonl",
        ".orchestrator/memory/events.jsonl",
        ".orchestrator/memory/approvals.jsonl",
        ".orchestrator/knowledge/ontology.json",
        ".orchestrator/knowledge/nodes.jsonl",
        ".orchestrator/knowledge/edges.jsonl",
    ):
        if not _safe_target(target, relative).is_file():
            findings.append(f"ERROR canonical memory/knowledge store is missing: {relative}")

    try:
        knowledge_nodes = _safe_target(target, ".orchestrator/knowledge/nodes.jsonl")
        knowledge_edges = _safe_target(target, ".orchestrator/knowledge/edges.jsonl")
        effective_graph(knowledge_nodes, knowledge_edges)
        index = _safe_target(target, ".orchestrator/knowledge/indexes/index.json")
        if not index.is_file():
            findings.append("ERROR derived knowledge index is missing")
    except Exception as exc:
        findings.append(f"ERROR knowledge graph is invalid: {exc}")

    context = target / ".orchestrator/project-context.md"
    try:
        context_text = context.read_text(encoding="utf-8")
        if "<!-- manual:start -->" not in context_text or "<!-- manual:end -->" not in context_text:
            findings.append("ERROR Project Context ownership markers are missing")
    except (OSError, UnicodeError) as exc:
        findings.append(f"ERROR Project Context is unreadable: {exc}")

    for change in plan.changes:
        if change.path.endswith(("AGENTS.md", "CLAUDE.md", "copilot-instructions.md")):
            text = _read_text(_safe_target(target, change.path))
            if MANAGED_START not in text or MANAGED_END not in text:
                findings.append(
                    f"ERROR managed instruction markers are missing: {change.path}"
                )

    for item in run_health_checks(core).findings:
        if item.severity in {"ERROR", "CRITICAL"}:
            findings.append(f"{item.severity} core health {item.code}: {item.message}")
    for item in run_health_checks(target, scope="tasks").findings:
        if item.severity in {"ERROR", "CRITICAL"}:
            findings.append(f"{item.severity} task health {item.code}: {item.message}")

    second = plan_onboarding(skill_path, target, answers)
    if not isinstance(second, OnboardingPlan) or second.changes:
        findings.append("ERROR onboarding is not idempotent")
    return tuple(findings)


def apply_onboarding(
    skill_path: Path | str,
    target_root: Path | str,
    answers: Mapping[str, object],
    *,
    approved_plan_hash: str,
    validation_hook: (
        Callable[[Path, Path, OnboardingPlan], tuple[str, ...]] | None
    ) = None,
) -> OnboardingApplyResult:
    plan = plan_onboarding(skill_path, target_root, answers)
    if not isinstance(plan, OnboardingPlan):
        raise OnboardingError(
            f"onboarding is not ready to apply: {plan.status}"
        )
    if not approved_plan_hash or approved_plan_hash != plan.plan_hash:
        raise OnboardingError(
            "stale or missing approval: approved plan hash does not match current preview"
        )

    target = Path(plan.target_root)
    core = Path(plan.core_root)
    session_id = f"{plan.plan_hash[:12]}-{uuid.uuid4().hex[:8]}"
    session_path = target / ".orchestrator/onboarding/session.json"
    manifest_path = _create_backup(target, plan, session_id)
    session: dict[str, object] = {
        "schema_version": 1,
        "session_id": session_id,
        "status": "applying",
        "target_root": str(target),
        "core_root": str(core),
        "target_fingerprint": plan.target_fingerprint,
        "plan_hash": plan.plan_hash,
        "backup_manifest": str(manifest_path.relative_to(target).as_posix()),
        "answers": _validate_answers(answers),
        "rollback_on_error": True,
        "updated_at": _timestamp(),
    }
    _write_json(session_path, session)

    findings: tuple[str, ...] = ()
    status = "completed"
    rollback_verified = False
    try:
        for change in plan.changes:
            destination = _safe_target(target, change.path)
            if _current_digest(destination) != change.before_sha256:
                raise OnboardingError(
                    f"planned input changed after approval: {change.path}"
                )
            _atomic_write_text(
                destination,
                change.content,
            )
        _rebuild_target_knowledge_index(target)
        session["status"] = "validating"
        session["updated_at"] = _timestamp()
        _write_json(session_path, session)
        if validation_hook is not None:
            findings = tuple(validation_hook(core, target, plan))
        else:
            findings = _default_validation(
                core,
                target,
                plan,
                skill_path=skill_path,
                answers=answers,
            )
        if any(
            finding.startswith(("ERROR", "CRITICAL"))
            for finding in findings
        ):
            rollback_verified = _restore_backup(target, manifest_path)
            if rollback_verified:
                _rebuild_target_knowledge_index(target)
            status = "rolled_back" if rollback_verified else "rollback_failed"
    except Exception as exc:
        findings = findings + (f"ERROR onboarding apply failed: {type(exc).__name__}: {exc}",)
        try:
            rollback_verified = _restore_backup(target, manifest_path)
            if rollback_verified:
                _rebuild_target_knowledge_index(target)
            status = "rolled_back" if rollback_verified else "rollback_failed"
        except Exception as rollback_exc:
            findings = findings + (
                f"CRITICAL rollback failed: {type(rollback_exc).__name__}: {rollback_exc}",
            )
            status = "rollback_failed"

    session["status"] = status
    session["updated_at"] = _timestamp()
    _write_json(session_path, session)
    report_path = target / ".orchestrator/onboarding/report.json"
    result = OnboardingApplyResult(
        status,
        plan.plan_hash,
        tuple(change.path for change in plan.changes),
        findings,
        report_path.relative_to(target).as_posix(),
        rollback_verified,
    )
    _write_json(report_path, result.to_dict())
    return result


def rollback_onboarding(
    target_root: Path | str,
    *,
    session_path: Path | str | None = None,
) -> OnboardingApplyResult:
    target = Path(target_root).resolve()
    session_file = (
        Path(session_path).resolve()
        if session_path is not None
        else target / ".orchestrator/onboarding/session.json"
    )
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    manifest_relative = payload.get("backup_manifest")
    if not isinstance(manifest_relative, str):
        raise OnboardingError("onboarding session has no rollback manifest")
    manifest = _safe_target(target, manifest_relative)
    verified = _restore_backup(target, manifest)
    status = "rolled_back" if verified else "rollback_failed"
    payload["status"] = status
    payload["updated_at"] = _timestamp()
    _write_json(session_file, payload)
    report_path = target / ".orchestrator/onboarding/report.json"
    result = OnboardingApplyResult(
        status,
        str(payload.get("plan_hash") or ""),
        (),
        (),
        report_path.relative_to(target).as_posix(),
        verified,
    )
    _write_json(report_path, result.to_dict())
    return result
