from __future__ import annotations

import argparse
import fnmatch
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any


CYRILLIC_RE = re.compile(r"[\u0410-\u044f\u0401\u0451]")
LATIN_RE = re.compile(r"[A-Za-z]")
POLICY_PATH = Path("config/language-policy.json")


class LanguagePolicyError(ValueError):
    pass


@dataclass(frozen=True)
class LanguagePolicy:
    schema_version: int
    default_language: str
    languages: tuple[str, ...]
    graph_source_languages: tuple[str, ...]
    excluded_path_prefixes: tuple[str, ...]
    generated_path_prefixes: tuple[str, ...]
    russian_companion_patterns: tuple[str, ...]
    legacy_russian_patterns: tuple[str, ...]
    user_canonical_patterns: tuple[str, ...]
    document_classes: dict[str, dict[str, bool]]


@dataclass(frozen=True)
class LanguageDecision:
    path: str
    language: str
    document_class: str
    canonical: bool
    graph_eligible: bool
    excluded: bool
    translation_of: str | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class InventoryItem:
    path: str
    language: str
    document_class: str
    canonical: bool
    graph_eligible: bool
    excluded: bool
    translation_of: str | None
    error: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _as_patterns(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    values = payload.get(key)
    if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
        raise LanguagePolicyError(f"{key} must be a non-empty string array")
    return tuple(values)


def load_policy(project_root: Path | str) -> LanguagePolicy:
    root = Path(project_root).resolve()
    path = root / POLICY_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LanguagePolicyError(f"cannot read language policy: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise LanguagePolicyError("language policy schema_version must equal 1")
    languages = _as_patterns(payload, "languages")
    for key in ("default_language",):
        if not isinstance(payload.get(key), str) or not payload[key]:
            raise LanguagePolicyError(f"{key} must be a non-empty string")
    if payload["default_language"] not in languages:
        raise LanguagePolicyError("default_language must be listed in languages")
    graph_languages = _as_patterns(payload, "graph_source_languages")
    if not set(graph_languages).issubset(set(languages)):
        raise LanguagePolicyError("graph_source_languages must be listed in languages")
    classes = payload.get("document_classes")
    if not isinstance(classes, dict) or not classes:
        raise LanguagePolicyError("document_classes must be a non-empty object")
    normalized_classes: dict[str, dict[str, bool]] = {}
    for name, value in classes.items():
        if not isinstance(name, str) or not isinstance(value, dict):
            raise LanguagePolicyError("document_classes entries must be objects")
        normalized_classes[name] = {
            "canonical": bool(value.get("canonical", False)),
            "graph_eligible": bool(value.get("graph_eligible", False)),
        }
    return LanguagePolicy(
        schema_version=1,
        default_language=payload["default_language"],
        languages=languages,
        graph_source_languages=graph_languages,
        excluded_path_prefixes=_as_patterns(payload, "excluded_path_prefixes"),
        generated_path_prefixes=_as_patterns(payload, "generated_path_prefixes"),
        russian_companion_patterns=_as_patterns(payload, "russian_companion_patterns"),
        legacy_russian_patterns=_as_patterns(payload, "legacy_russian_patterns"),
        user_canonical_patterns=_as_patterns(payload, "user_canonical_patterns"),
        document_classes=normalized_classes,
    )


def _relative_path(root: Path, source: Path | str) -> tuple[Path, str]:
    root = root.resolve()
    path = Path(source)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise LanguagePolicyError("source is outside the project root") from exc
    return path, PurePosixPath(relative.as_posix()).as_posix()


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _prefix_matches(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def _derived_artifact(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return "__pycache__" in parts or path.endswith((".pyc", ".pyo"))


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    result: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("\"'")
    return result


def _translation_target(path: str) -> str | None:
    if path == "README.ru.md":
        return "README.md"
    if path.endswith(".ru.md"):
        return path[:-6] + ".md"
    if path.endswith("-ru.md"):
        return path[:-6] + ".md"
    return None


def _language(path: str, text: str, metadata: dict[str, str], policy: LanguagePolicy) -> tuple[str, str]:
    if PurePosixPath(path).name == "VERSION":
        return "en", "machine-readable version metadata"
    declared = metadata.get("language")
    if declared and declared not in {"en", "ru"}:
        return "unknown", "unsupported language metadata"
    if _matches(path, policy.russian_companion_patterns) or _matches(path, policy.legacy_russian_patterns):
        if declared and declared != "ru":
            return "mixed", "Russian path pattern conflicts with language metadata"
        # A Russian companion may contain Latin technical identifiers, paths,
        # and commands. The path class is the explicit boundary that keeps it
        # out of canonical graph sources; do not misclassify those identifiers
        # as a single-file bilingual document.
        return "ru", "Russian companion or legacy baseline path"
    has_cyrillic = bool(CYRILLIC_RE.search(text))
    has_latin = bool(LATIN_RE.search(text))
    if declared:
        if declared == "ru" and has_latin and has_cyrillic:
            return "mixed", "Russian metadata with mixed-language content"
        if declared == "en" and has_cyrillic:
            return "mixed", "English metadata with Cyrillic content"
        return declared, "declared language metadata"
    if has_cyrillic and has_latin:
        return "mixed", "mixed-language content contains both Cyrillic and Latin text"
    if has_cyrillic:
        return "ru", "content contains Cyrillic text"
    if has_latin:
        return "en", "content contains Latin text"
    return "unknown", "content has no detectable language"


def classify_path(
    project_root: Path | str,
    source: Path | str,
    *,
    policy: LanguagePolicy | None = None,
) -> LanguageDecision:
    root = Path(project_root).resolve()
    path, relative = _relative_path(root, Path(source))
    if not path.is_file():
        raise LanguagePolicyError(f"source does not exist: {relative}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise LanguagePolicyError(f"source is not valid UTF-8: {relative}") from exc
    selected = policy or load_policy(root)
    if _derived_artifact(relative) or _prefix_matches(relative, selected.excluded_path_prefixes):
        document_class = "excluded"
        language = "unknown"
        reason = "path is excluded from repository language inventory"
        translation_of = None
    elif _prefix_matches(relative, selected.generated_path_prefixes):
        document_class = "generated"
        language, reason = _language(relative, text, {}, selected)
        translation_of = None
    elif _matches(relative, selected.russian_companion_patterns):
        document_class = "user_companion"
        language, reason = _language(relative, text, _frontmatter(text), selected)
        translation_of = _translation_target(relative)
    elif _matches(relative, selected.legacy_russian_patterns):
        document_class = "legacy_russian"
        language, reason = _language(relative, text, _frontmatter(text), selected)
        translation_of = _translation_target(relative)
    elif _matches(relative, selected.user_canonical_patterns):
        document_class = "user_canonical"
        language, reason = _language(relative, text, _frontmatter(text), selected)
        translation_of = None
    else:
        document_class = "canonical"
        language, reason = _language(relative, text, _frontmatter(text), selected)
        translation_of = None
    class_policy = selected.document_classes[document_class]
    error: str | None = None
    if not _derived_artifact(relative) and not _prefix_matches(relative, selected.excluded_path_prefixes):
        if language in {"mixed", "unknown"}:
            error = f"{reason}; graph source is not eligible"
        elif language == "ru" and document_class not in {"user_companion", "legacy_russian"}:
            error = "unclassified Russian document; graph source is not eligible"
        elif class_policy["canonical"] and language not in {"en"}:
            error = "canonical source must be English"
    graph_eligible = (
        not _derived_artifact(relative)
        and not _prefix_matches(relative, selected.excluded_path_prefixes)
        and class_policy["graph_eligible"]
        and language in selected.graph_source_languages
        and error is None
    )
    return LanguageDecision(
        path=relative,
        language=language,
        document_class=document_class,
        canonical=class_policy["canonical"],
        graph_eligible=graph_eligible,
        excluded=document_class == "excluded",
        translation_of=translation_of,
        reason=error or reason,
    )


def inventory_repository(
    project_root: Path | str,
    *,
    policy: LanguagePolicy | None = None,
) -> list[InventoryItem]:
    root = Path(project_root).resolve()
    selected = policy or load_policy(root)
    items: list[InventoryItem] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if _derived_artifact(relative) or _prefix_matches(relative, selected.excluded_path_prefixes):
            continue
        try:
            decision = classify_path(root, path, policy=selected)
        except LanguagePolicyError as exc:
            items.append(InventoryItem(relative, "unknown", "unknown", False, False, False, None, str(exc)))
            continue
        error: str | None = None
        if decision.document_class not in {"generated", "excluded"}:
            if decision.language in {"mixed", "unknown"}:
                error = decision.reason
            elif decision.language == "ru" and decision.document_class not in {"user_companion", "legacy_russian"}:
                error = decision.reason
            elif decision.canonical and decision.language != "en":
                error = decision.reason
        items.append(
            InventoryItem(
                path=decision.path,
                language=decision.language,
                document_class=decision.document_class,
                canonical=decision.canonical,
                graph_eligible=decision.graph_eligible,
                excluded=decision.excluded,
                translation_of=decision.translation_of,
                error=error,
            )
        )
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="orchestrator-language-policy")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-errors", action="store_true")
    args = parser.parse_args(argv)
    items = inventory_repository(args.root)
    payload = {"ok": not any(item.error for item in items), "items": [item.to_dict() for item in items]}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in items:
            suffix = f" ERROR: {item.error}" if item.error else ""
            print(f"{item.path} [{item.language}/{item.document_class}] graph={item.graph_eligible}{suffix}")
    return 1 if args.fail_on_errors and not payload["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
