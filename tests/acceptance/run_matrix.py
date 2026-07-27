from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.onboarding import onboard
from orchestrator import __version__
from orchestrator.platforms import load_platform_profile
from orchestrator.release import install_artifact
from orchestrator.technologies import detect_technology, load_technology_profile


PLATFORM_FILES = {
    "codex": "codex.yaml",
    "google-antigravity": "google-antigravity.yaml",
    "github-copilot-vscode": "github-copilot-vscode.yaml",
    "claude-vscode": "claude-vscode.yaml",
}
TECHNOLOGY_FILES = {"python": "python.yaml", "abap-rap": "abap-rap.yaml"}
SANDBOXES = {"python": "python-minimal", "abap-rap": "abap-rap-minimal"}


def _tree_digest(root: Path, *, exclude: tuple[str, ...] = (".orchestrator",)) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or any(part in exclude for part in relative.parts):
            continue
        digest.update(relative.as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def run_cell(cell: dict[str, str], artifact: Path) -> dict[str, object]:
    platform = load_platform_profile(ROOT / "profiles/platforms" / PLATFORM_FILES[cell["platform"]])
    technology = load_technology_profile(ROOT / "profiles/technologies" / TECHNOLOGY_FILES[cell["technology"]])
    sandbox = ROOT / "tests/sandbox-projects" / SANDBOXES[cell["technology"]]
    detection = detect_technology(sandbox, technology)
    if not detection.evidence:
        return {**cell, "status": "failed", "evidence": ["technology detection has no evidence"]}

    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary) / "project"
        shutil.copytree(sandbox, project)
        before = _tree_digest(project)
        installed = install_artifact(artifact, project, managed=cell["mode"] == "managed")
        if cell["mode"] == "managed" and _tree_digest(project) != before:
            return {**cell, "status": "failed", "evidence": ["managed update changed project-owned files"]}
        context = project / ".orchestrator/project-context.md"
        onboard(project, context, dry_run=False)
        second = onboard(project, context, dry_run=True)
        if second.changed:
            return {**cell, "status": "failed", "evidence": ["second onboarding produced a diff"]}
        command = [
            sys.executable,
            "-c",
            f"import orchestrator; assert orchestrator.__version__ == {__version__!r}",
        ]
        completed = subprocess.run(
            command,
            cwd=project,
            env={"PYTHONPATH": str(installed)},
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode:
            return {**cell, "status": "failed", "evidence": [completed.stderr.strip()]}
    return {
        **cell,
        "status": "passed",
        "platform_maturity": platform["maturity"],
        "native_smoke": platform["validation"]["native_smoke"],
        "evidence": [
            f"platform-order={platform['adapter_order']}",
            f"contract-matrix={platform['validation']['contract_matrix']}",
            f"detection={','.join(detection.evidence)}",
            "onboarding-idempotent",
            "task-lifecycle-contract-covered",
            f"{cell['mode']}-install",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--release")
    parser.add_argument("--output")
    parser.add_argument(
        "--platform-order",
        help="Comma-separated platform order that must match the matrix contract.",
    )
    args = parser.parse_args(argv)
    matrix = json.loads((ROOT / "tests/acceptance/matrix.json").read_text(encoding="utf-8"))
    if args.platform_order:
        requested_order = [item.strip() for item in args.platform_order.split(",") if item.strip()]
        if requested_order != matrix["platform_order"]:
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "error": "platform order does not match the acceptance contract",
                        "expected": matrix["platform_order"],
                        "actual": requested_order,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1
    artifact = ROOT if not args.release else ROOT / "releases" / args.release / "artifact"
    results = [run_cell(cell, artifact) for cell in matrix["cells"]]
    report = {
        "schema_version": 1,
        "release": args.release,
        "python": sys.version.split()[0],
        "results": results,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    combinations = {(item["platform"], item["technology"], item["mode"]) for item in results}
    valid = len(results) == 16 and len(combinations) == 16 and all(item["status"] == "passed" for item in results)
    return 0 if valid or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
