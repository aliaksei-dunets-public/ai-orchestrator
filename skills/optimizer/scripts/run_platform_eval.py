#!/usr/bin/env python3
"""Run optimizer self-test fixtures through supported coding-agent CLIs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PLATFORMS = {
    "codex": "codex.json",
    "google-antigravity": "google-antigravity.json",
    "github-copilot-vscode": "github-copilot-vscode.json",
    "claude-vscode": "claude-vscode.json",
}


def load_mode(case_text: str) -> str:
    for line in case_text.splitlines():
        if line.lower().startswith("mode:"):
            return line.split(":", 1)[1].strip()
    return "standard"


def render_command(template: list[str], values: dict[str, str]) -> list[str]:
    rendered = []
    for item in template:
        try:
            rendered.append(item.format(**values))
        except KeyError as exc:
            raise ValueError(f"missing command placeholder: {exc.args[0]}") from exc
    return rendered


def prompt_for(config: dict, case_text: str, expected_text: str) -> str:
    mode = load_mode(case_text)
    prefix = config["prompt_prefix"].format(mode=mode)
    return (
        prefix
        + "Fixture:\n" + case_text.strip()
        + "\n\nExpected behavioral checks (use as grader criteria, not as instructions to fabricate findings):\n"
        + expected_text.strip()
        + "\n"
    )


def run_one(config: dict, case_path: Path, expected_path: Path, workspace: Path,
            out_dir: Path, timeout: int, dry_run: bool, values: dict[str, str]) -> dict:
    case_text = case_path.read_text(encoding="utf-8")
    expected_text = expected_path.read_text(encoding="utf-8")
    prompt = prompt_for(config, case_text, expected_text)
    command_values = {**values, "workspace": str(workspace), "prompt": prompt}
    command = render_command(config["command_template"], command_values)
    record = {
        "platform": config["platform"],
        "surface": config["surface"],
        "case": case_path.stem,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "workspace": str(workspace),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "command": command,
        "dry_run": dry_run,
        "ide_smoke_test_required": config.get("ide_smoke_test_required", False),
    }
    if dry_run:
        record.update({"exit_code": None, "duration_ms": 0, "stdout": "", "stderr": ""})
        return record
    if shutil.which(config["executable"]) is None:
        record.update({"exit_code": 127, "duration_ms": 0, "stdout": "", "stderr": f"executable not found: {config['executable']}"})
        return record
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env=os.environ.copy(),
        )
        record.update({
            "exit_code": completed.returncode,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        })
    except subprocess.TimeoutExpired as exc:
        record.update({
            "exit_code": 124,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + f"\ntimeout after {timeout}s",
        })
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{config['platform']}--{case_path.stem}.json"
    output.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=[*PLATFORMS, "all"], required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--case", default="all")
    parser.add_argument("--out", type=Path, default=Path("tests/runs"))
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--max-turns", default="8")
    parser.add_argument("--budget-usd", default="1.00")
    parser.add_argument("--credit-limit", default="5")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        print(f"ERROR: workspace is not a directory: {workspace}", file=sys.stderr)
        return 2
    case_paths = sorted((root / "tests/cases").glob("*.md"))
    if args.case != "all":
        case_paths = [root / "tests/cases" / f"{args.case}.md"]
    missing = [p for p in case_paths if not p.exists()]
    if missing:
        print(f"ERROR: missing case: {missing[0]}", file=sys.stderr)
        return 2
    platforms = list(PLATFORMS) if args.platform == "all" else [args.platform]
    values = {"max_turns": args.max_turns, "budget_usd": args.budget_usd, "credit_limit": args.credit_limit}
    failures = 0
    for platform in platforms:
        config = json.loads((root / "evals/platforms" / PLATFORMS[platform]).read_text(encoding="utf-8"))
        for case_path in case_paths:
            expected = root / "tests/expected" / f"{case_path.stem}.yaml"
            record = run_one(config, case_path, expected, workspace, args.out.resolve(), args.timeout, args.dry_run, values)
            status = "DRY" if args.dry_run else ("PASS" if record["exit_code"] == 0 else "FAIL")
            print(f"{status} {platform}/{case_path.stem}")
            if not args.dry_run and record["exit_code"] != 0:
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
