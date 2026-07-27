#!/usr/bin/env python3
"""Install optimizer into a repository path used by a supported platform."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

TARGETS = {
    "codex": Path(".agents/skills/optimizer"),
    "google-antigravity": Path(".agent/skills/optimizer"),
    "github-copilot-vscode": Path(".github/skills/optimizer"),
    "claude-vscode": Path(".claude/skills/optimizer"),
}
EXCLUDES = {"__pycache__", ".git", "runs"}


def ignored(_path: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDES or name.endswith((".pyc", ".zip"))}


def install(source: Path, repo: Path, platform: str, mode: str, force: bool, dry_run: bool) -> Path:
    target = (repo / TARGETS[platform]).resolve()
    source = source.resolve()
    if target == source:
        return target
    if source in target.parents:
        raise ValueError("target cannot be inside the optimizer source directory")
    if target.exists() and not force:
        raise FileExistsError(f"target exists: {target}; use --force to replace it")
    if dry_run:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    if mode == "symlink":
        target.symlink_to(source, target_is_directory=True)
    else:
        shutil.copytree(source, target, ignore=ignored)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--platform", choices=[*TARGETS, "all"], required=True)
    parser.add_argument("--mode", choices=["copy", "symlink"], default="copy")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = Path(__file__).resolve().parents[1]
    repo = args.repo.resolve()
    platforms = list(TARGETS) if args.platform == "all" else [args.platform]
    try:
        for platform in platforms:
            target = install(source, repo, platform, args.mode, args.force, args.dry_run)
            verb = "would install" if args.dry_run else "installed"
            print(f"{platform}: {verb} -> {target}")
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
