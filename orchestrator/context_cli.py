from __future__ import annotations

import argparse
from pathlib import Path

from .retrieval import build_context_pack


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--task-context", default="")
    parser.add_argument("--task-context-file", type=Path)
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--term", action="append", default=[])
    parser.add_argument("--mode", choices=("quick", "standard", "deep"), default="standard")
    parser.add_argument("--budget-chars", type=int)


def run(args: argparse.Namespace) -> dict[str, object]:
    text = args.task_context
    if args.task_context_file:
        text = args.task_context_file.read_text(encoding="utf-8")
    budget = (
        args.budget_chars
        if args.budget_chars is not None
        else {"quick": 2048, "standard": 6144, "deep": 12288}[args.mode]
    )
    return build_context_pack(
        args.root,
        task_context=text,
        affected_paths=args.path,
        terms=args.term,
        budget_chars=budget,
    )
