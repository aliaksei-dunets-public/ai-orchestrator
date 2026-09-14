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


@dataclass(frozen=True)
class DocumentationGateEvidence:
    document: str
    owner: str
    status: str
    reason: str
    evidence_ref: str

    def to_dict(self) -> dict[str, str]:
        return {
            "document": self.document,
            "owner": self.owner,
            "status": self.status,
            "reason": self.reason,
            "evidence_ref": self.evidence_ref,
        }


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


def evaluate_documentation_gate(
    root: Path | str,
    changed_paths: Sequence[str],
    dispositions: Sequence[Mapping[str, object]],
    *,
    mapping_path: Path | str = "config/documentation-map.json",
) -> tuple[DocumentationGateEvidence, ...]:
    repository = Path(root).resolve()
    mapping = Path(mapping_path)
    if not mapping.is_absolute():
        mapping = repository / mapping
    impacts = documentation_impact(changed_paths, load_documentation_map(mapping))
    by_document: dict[str, Mapping[str, object]] = {}
    for disposition in dispositions:
        if not isinstance(disposition, Mapping):
            raise ValueError("documentation disposition must be an object")
        document = str(disposition.get("document", "")).replace("\\", "/").strip()
        if not document:
            raise ValueError("documentation disposition requires a document")
        if document in by_document:
            raise ValueError(f"duplicate documentation disposition: {document}")
        by_document[document] = disposition
    expected = {impact.document for impact in impacts}
    unknown = sorted(set(by_document) - expected)
    if unknown:
        raise ValueError(f"documentation dispositions have no matching impact: {unknown}")
    changed = {value.replace("\\", "/") for value in changed_paths}
    evidence: list[DocumentationGateEvidence] = []
    for impact in impacts:
        disposition = by_document.get(impact.document)
        if disposition is None:
            raise ValueError(
                f"missing documentation disposition for {impact.document}"
            )
        status = str(disposition.get("status", ""))
        reason = str(disposition.get("reason", "")).strip()
        evidence_ref = str(disposition.get("evidence_ref", "")).strip()
        if status not in {"updated", "not_applicable"}:
            raise ValueError(
                f"invalid documentation disposition for {impact.document}: {status}"
            )
        if status == "updated" and impact.document not in changed:
            raise ValueError(
                f"documentation marked updated but is absent from changed paths: {impact.document}"
            )
        if status == "not_applicable" and not reason:
            raise ValueError(
                f"documentation not_applicable requires a reason: {impact.document}"
            )
        document_path = (repository / impact.document).resolve()
        try:
            document_path.relative_to(repository)
        except ValueError as exc:
            raise ValueError(
                f"documentation path escapes repository: {impact.document}"
            ) from exc
        if not document_path.is_file():
            raise ValueError(f"documentation file does not exist: {impact.document}")
        if document_path.suffix.lower() == ".md":
            broken = broken_local_links(document_path, root=repository)
            if broken:
                raise ValueError(
                    f"broken local links in {impact.document}: {sorted(broken)}"
                )
        evidence.append(
            DocumentationGateEvidence(
                impact.document,
                impact.owner,
                status,
                reason,
                evidence_ref,
            )
        )
    return tuple(evidence)
