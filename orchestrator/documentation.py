from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)")


@dataclass(frozen=True)
class DocumentationImpact:
    document: str
    owner: str
    reason: str


def load_documentation_map(path: Path | str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("rules"), list):
        raise ValueError("Invalid documentation map")
    return payload


def documentation_impact(
    changed_paths: Sequence[str],
    mapping: Mapping[str, object],
) -> list[DocumentationImpact]:
    impacts: dict[str, DocumentationImpact] = {}
    for rule in mapping.get("rules", []):
        if not isinstance(rule, dict):
            continue
        prefixes = rule.get("path_prefixes", [])
        if any(
            changed.replace("\\", "/").startswith(str(prefix).replace("\\", "/"))
            for changed in changed_paths
            for prefix in prefixes
        ):
            for document in rule.get("documents", []):
                impacts[str(document)] = DocumentationImpact(
                    str(document),
                    str(rule.get("owner", "unknown")),
                    str(rule.get("reason", "Document impacted by changed contract.")),
                )
    return sorted(impacts.values(), key=lambda item: item.document)


def broken_local_links(markdown_path: Path | str, *, root: Path | str) -> list[str]:
    path = Path(markdown_path)
    repository = Path(root).resolve()
    broken: list[str] = []
    text = path.read_text(encoding="utf-8")
    for raw_target in MARKDOWN_LINK_RE.findall(text):
        target = raw_target.split("#", 1)[0].strip("<>")
        if not target:
            continue
        candidate = (path.parent / target).resolve()
        try:
            candidate.relative_to(repository)
        except ValueError:
            broken.append(raw_target)
            continue
        if not candidate.exists():
            broken.append(raw_target)
    return broken
