from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


class TechnologyProfileError(ValueError):
    pass


@dataclass(frozen=True)
class Detection:
    profile_id: str
    confidence: float
    evidence: tuple[str, ...]


def load_technology_profile(path: Path | str) -> dict[str, object]:
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"schema_version", "id", "precedence", "detection", "commands"}
    missing = required - set(profile)
    if missing or profile.get("schema_version") != 1:
        raise TechnologyProfileError(f"Invalid technology profile, missing={sorted(missing)}")
    commands = profile["commands"]
    if not isinstance(commands, dict):
        raise TechnologyProfileError("commands must be an object")
    for name, command in commands.items():
        if not isinstance(command, dict) or not command.get("argv") or command.get("approval") not in {"allowlisted", "required"}:
            raise TechnologyProfileError(f"Invalid command declaration: {name}")
    return profile


def detect_technology(root: Path | str, profile: Mapping[str, object]) -> Detection:
    project = Path(root)
    detection = profile.get("detection", {})
    markers = detection.get("markers", []) if isinstance(detection, Mapping) else []
    extensions = detection.get("extensions", []) if isinstance(detection, Mapping) else []
    evidence: list[str] = []
    for marker in markers:
        if (project / str(marker)).exists():
            evidence.append(f"marker:{marker}")
    for extension in extensions:
        match = next(project.rglob(f"*{extension}"), None)
        if match:
            evidence.append(f"extension:{extension}:{match.relative_to(project).as_posix()}")
    total_signals = max(1, len(markers) + len(extensions))
    confidence = min(1.0, len(evidence) / total_signals)
    return Detection(str(profile["id"]), confidence, tuple(evidence))


def merge_profiles(profiles: Sequence[Mapping[str, object]]) -> dict[str, object]:
    ordered = sorted(profiles, key=lambda item: (int(item["precedence"]), str(item["id"])))
    result: dict[str, object] = {"profiles": [str(item["id"]) for item in ordered], "commands": {}, "directories": {}}
    owners: dict[tuple[str, str], str] = {}
    for profile in ordered:
        for section in ("commands", "directories"):
            values = profile.get(section, {})
            if not isinstance(values, Mapping):
                continue
            target = result[section]
            assert isinstance(target, dict)
            for key, value in values.items():
                marker = (section, str(key))
                if marker in owners and target[str(key)] != value:
                    raise TechnologyProfileError(
                        f"Conflicting {section}.{key}: {owners[marker]} vs {profile['id']}"
                    )
                target[str(key)] = value
                owners[marker] = str(profile["id"])
    return result


def command_is_automatic(command: Mapping[str, object]) -> bool:
    return command.get("approval") == "allowlisted"
