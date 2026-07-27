from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"
CORE_ROOT = next(
    parent.parent
    for parent in Path(__file__).resolve().parents
    if parent.name == "skills"
)
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from orchestrator.onboarding_workflow import (  # noqa: E402
    OnboardingError,
    apply_onboarding,
    inspect_onboarding,
    plan_onboarding,
    rollback_onboarding,
)


def _answers(args: argparse.Namespace) -> dict[str, object]:
    if args.answers and args.answers_json:
        raise OnboardingError("use either --answers or --answers-json")
    if args.answers:
        try:
            payload = json.loads(Path(args.answers).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise OnboardingError(f"cannot read answers: {exc}") from exc
    elif args.answers_json:
        try:
            payload = json.loads(args.answers_json)
        except json.JSONDecodeError as exc:
            raise OnboardingError(f"invalid --answers-json: {exc}") from exc
    else:
        payload = {}
    if not isinstance(payload, dict):
        raise OnboardingError("answers must be a JSON object")
    if "schema_version" in payload:
        if payload["schema_version"] != 1:
            raise OnboardingError("answers schema_version must equal 1")
        payload = {
            key: value
            for key, value in payload.items()
            if key != "schema_version"
        }
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic agent-facing project onboarding operations."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "plan", "apply"):
        command = commands.add_parser(name)
        command.add_argument("--target", type=Path, required=True)
        command.add_argument("--answers", type=Path)
        command.add_argument("--answers-json")
        if name == "apply":
            command.add_argument("--approved-plan-hash", required=True)
    rollback = commands.add_parser("rollback")
    rollback.add_argument("--target", type=Path, required=True)
    rollback.add_argument("--session", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_onboarding(SKILL_PATH, args.target, _answers(args))
        elif args.command == "plan":
            result = plan_onboarding(SKILL_PATH, args.target, _answers(args))
        elif args.command == "apply":
            result = apply_onboarding(
                SKILL_PATH,
                args.target,
                _answers(args),
                approved_plan_hash=args.approved_plan_hash,
            )
        else:
            result = rollback_onboarding(
                args.target,
                session_path=args.session,
            )
        print(
            json.dumps(
                result.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except OnboardingError as exc:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "blocked",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "blocked",
                    "error": (
                        "unexpected onboarding failure: "
                        f"{type(exc).__name__}"
                    ),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
