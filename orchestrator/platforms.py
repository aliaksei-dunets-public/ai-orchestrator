from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


VALID_CAPABILITY_MODES = {"native", "fallback", "blocked"}
VALID_MATURITY_LEVELS = {"stable", "experimental"}
VALID_VALIDATION_STATUSES = {"passed", "failed", "not_run"}


class PlatformProfileError(ValueError):
    pass


@dataclass(frozen=True)
class CapabilityResolution:
    capability: str
    mode: str
    adapter: str | None
    reason: str | None = None


def load_platform_profile(path: Path | str) -> dict[str, object]:
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "id",
        "adapter_order",
        "maturity",
        "validation",
        "capabilities",
    }
    missing = required - set(profile)
    if missing or profile.get("schema_version") != 1:
        raise PlatformProfileError(f"Invalid platform profile, missing={sorted(missing)}")
    maturity = profile["maturity"]
    if maturity not in VALID_MATURITY_LEVELS:
        raise PlatformProfileError(f"Invalid platform maturity: {maturity}")
    validation = profile["validation"]
    if not isinstance(validation, dict):
        raise PlatformProfileError("validation must be an object")
    validation_required = {"contract_matrix", "native_smoke", "evidence"}
    validation_missing = validation_required - set(validation)
    if validation_missing:
        raise PlatformProfileError(
            f"Invalid platform validation, missing={sorted(validation_missing)}"
        )
    for field in ("contract_matrix", "native_smoke"):
        if validation[field] not in VALID_VALIDATION_STATUSES:
            raise PlatformProfileError(f"Invalid validation status: {field}")
    evidence = validation["evidence"]
    if not isinstance(evidence, list) or not evidence or any(
        not isinstance(item, str) or not item.strip() for item in evidence
    ):
        raise PlatformProfileError(
            "validation evidence must be a non-empty list of non-empty strings"
        )
    if maturity == "stable" and (
        validation["contract_matrix"] != "passed"
        or validation["native_smoke"] != "passed"
        or not evidence
    ):
        raise PlatformProfileError(
            "stable platform requires passed contract matrix, passed native smoke, and evidence"
        )
    capabilities = profile["capabilities"]
    if not isinstance(capabilities, dict):
        raise PlatformProfileError("capabilities must be an object")
    for name, entry in capabilities.items():
        if not isinstance(entry, dict) or entry.get("mode") not in VALID_CAPABILITY_MODES:
            raise PlatformProfileError(f"Invalid capability {name}")
        if entry["mode"] in {"native", "fallback"} and not entry.get("adapter"):
            raise PlatformProfileError(f"Capability {name} requires an adapter")
    return profile


def resolve_capability(profile: Mapping[str, object], capability: str) -> CapabilityResolution:
    capabilities = profile.get("capabilities", {})
    entry = capabilities.get(capability) if isinstance(capabilities, Mapping) else None
    if not isinstance(entry, Mapping):
        return CapabilityResolution(capability, "blocked", None, "Capability is not declared")
    mode = str(entry.get("mode"))
    adapter = str(entry["adapter"]) if entry.get("adapter") else None
    reason = str(entry["reason"]) if entry.get("reason") else None
    return CapabilityResolution(capability, mode, adapter, reason)
