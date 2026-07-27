#!/usr/bin/env python3
"""Static integrity and safety validator for the optimizer skill."""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

PLATFORM_CONFIGS = {
    "codex": "evals/platforms/codex.json",
    "google-antigravity": "evals/platforms/google-antigravity.json",
    "github-copilot-vscode": "evals/platforms/github-copilot-vscode.json",
    "claude-vscode": "evals/platforms/claude-vscode.json",
}
PLATFORM_REFERENCES = {
    "references/platforms/common.md",
    "references/platforms/codex.md",
    "references/platforms/google-antigravity.md",
    "references/platforms/github-copilot-vscode.md",
    "references/platforms/claude-vscode.md",
}
REQUIRED = {
    "SKILL.md",
    "GUIDE.md",
    "CHANGELOG.md",
    "VERSION",
    "references/index.md",
    "references/audit/instructions-context.md",
    "references/audit/orchestration-tools.md",
    "references/audit/security-trust.md",
    "references/audit/evaluation-metrics.md",
    "references/audit/output-contract.md",
    "references/patterns/context-state.md",
    "references/patterns/orchestration.md",
    "references/patterns/runtime-evaluation.md",
    "references/patterns/compact-response.md",
    "references/providers/openai/common.md",
    "references/providers/openai/gpt-5.4.md",
    "references/providers/openai/gpt-5.5.md",
    "references/providers/openai/gpt-5.6.md",
    *PLATFORM_REFERENCES,
    *PLATFORM_CONFIGS.values(),
    "evals/README.md",
    "schemas/eval-result.schema.json",
    "scripts/install_platform.py",
    "scripts/run_platform_eval.py",
    "tests/README.md",
    "tests/cases/report-language-selection.md",
    "tests/expected/report-language-selection.yaml",
}
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".py", ".txt", ".json", ""}
MAX_SKILL_LINES = 350
MAX_SKILL_BYTES = 18_000
DANGEROUS_DEFAULTS = {
    "danger-full-access",
    "dangerously-skip-permissions",
    "bypasspermissions",
    "allow-all",
    "--yes-to-all",
}


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    block = text[4:end]
    result: dict[str, str] = {}
    current = None
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            current = m.group(1)
            result[current] = m.group(2).strip()
        elif current and line.startswith("  "):
            result[current] = (result[current] + " " + line.strip()).strip()
    return result


def code_fences_balanced(text: str) -> bool:
    return len(re.findall(r"^```", text, flags=re.MULTILINE)) % 2 == 0


def referenced_paths(text: str) -> set[str]:
    refs = set()
    for value in re.findall(r"`((?:references|tests|scripts|evals|schemas)/[^`]+)`", text):
        value = value.rstrip(".,;:")
        if not any(ch in value for ch in "*<>|") and "{" not in value:
            refs.add(value)
    return refs


def validate_platform_config(root: Path, rel: str, errors: list[str]) -> dict | None:
    path = root / rel
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid platform config {rel}: {exc}")
        return None
    required = {"platform", "surface", "executable", "install_path", "prompt_prefix", "command_template", "output_format"}
    missing = required - set(data)
    if missing:
        errors.append(f"platform config {rel} missing keys: {sorted(missing)}")
    command = data.get("command_template")
    if not isinstance(command, list) or not command or not all(isinstance(v, str) for v in command):
        errors.append(f"platform config {rel} command_template must be a non-empty string array")
        command = []
    joined = " ".join(command).lower()
    for unsafe in DANGEROUS_DEFAULTS:
        if unsafe in joined:
            errors.append(f"unsafe default flag in {rel}: {unsafe}")
    if command and command[0] != data.get("executable"):
        errors.append(f"platform config {rel} executable does not match command_template[0]")
    install_path = str(data.get("install_path", ""))
    if install_path.startswith("/") or ".." in Path(install_path).parts:
        errors.append(f"platform config {rel} install_path must be repository-relative")
    if "{prompt}" not in command:
        errors.append(f"platform config {rel} does not pass the prompt placeholder")
    return data


def validate(root: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    all_files = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}

    for rel in sorted(REQUIRED - all_files):
        errors.append(f"missing required file: {rel}")

    skill = root / "SKILL.md"
    if skill.exists():
        text = skill.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if fm.get("name") != "optimizer":
            errors.append("SKILL.md frontmatter name must be optimizer")
        if not fm.get("description"):
            errors.append("SKILL.md frontmatter description is missing")
        lines = len(text.splitlines())
        size = len(text.encode("utf-8"))
        if lines > MAX_SKILL_LINES:
            errors.append(f"SKILL.md too long: {lines} lines > {MAX_SKILL_LINES}")
        if size > MAX_SKILL_BYTES:
            errors.append(f"SKILL.md too large: {size} bytes > {MAX_SKILL_BYTES}")

    case_names = {p.stem for p in (root / "tests/cases").glob("*.md")}
    expected_names = {p.stem for p in (root / "tests/expected").glob("*.yaml")}
    if case_names != expected_names:
        errors.append(f"fixture mismatch: cases={sorted(case_names)} expected={sorted(expected_names)}")
    if len(case_names) < 12:
        warnings.append(f"only {len(case_names)} behavioral fixtures")

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if "__pycache__" in path.parts or path.suffix.lower() == ".pyc":
            errors.append(f"generated Python artifact included: {rel}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            errors.append(f"unexpected binary or unsupported file: {rel}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"non-UTF-8 file: {rel}")
            continue
        if "\ufeff" in text:
            warnings.append(f"BOM found: {rel}")
        if path.suffix == ".md" and not code_fences_balanced(text):
            errors.append(f"unbalanced code fences: {rel}")
        for ref in referenced_paths(text):
            if not (root / ref).exists():
                errors.append(f"broken internal reference in {rel}: {ref}")
        if rel.startswith(("references/providers/", "references/platforms/")):
            if "checked_at:" not in text:
                errors.append(f"missing checked_at metadata: {rel}")
            if "verification_required_for:" not in text:
                errors.append(f"missing freshness policy: {rel}")
        if path.suffix == ".py":
            try:
                ast.parse(text, filename=rel)
            except SyntaxError as exc:
                errors.append(f"Python syntax error in {rel}: {exc}")
        if path.suffix == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON in {rel}: {exc}")

    configs = []
    for rel in PLATFORM_CONFIGS.values():
        if (root / rel).exists():
            data = validate_platform_config(root, rel, errors)
            if data:
                configs.append(data)
    install_paths = [c.get("install_path") for c in configs]
    if len(install_paths) != len(set(install_paths)):
        errors.append("platform install paths must be unique")

    version = (root / "VERSION").read_text(encoding="utf-8").strip() if (root / "VERSION").exists() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append(f"invalid VERSION value: {version!r}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "version": version,
            "files": len(all_files),
            "skill_lines": len(skill.read_text(encoding="utf-8").splitlines()) if skill.exists() else 0,
            "skill_bytes": len(skill.read_bytes()) if skill.exists() else 0,
            "behavioral_fixtures": len(case_names),
            "platform_profiles": len(configs),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate(args.root.resolve())
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("PASS" if result["ok"] else "FAIL")
        for item in result["errors"]:
            print(f"ERROR: {item}")
        for item in result["warnings"]:
            print(f"WARN: {item}")
        print(json.dumps(result["metrics"], indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
