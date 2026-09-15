"""Deterministic preview/apply onboarding for a target project."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


ONBOARDING_VERSION = "0.1.1"
PLAN_SCHEMA_VERSION = 2
BEGIN = "<!-- orchestrator:begin -->"
END = "<!-- orchestrator:end -->"
IGNORE_BEGIN = "# orchestrator:begin"
IGNORE_END = "# orchestrator:end"
OWNED_PATHS = {
    ".orchestrator/project.json",
    ".orchestrator/project-context.md",
    "AGENTS.md",
    ".gitignore",
}


class OnboardingError(Exception):
    """An onboarding plan cannot be safely built or applied."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _core_fingerprint(root: Path) -> str:
    """Return a deterministic fingerprint of the usable core contents."""
    excluded = {".git", ".orchestrator", ".tmp", ".venv", "__pycache__", "build", "dist"}
    records: list[bytes] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in excluded for part in relative.parts):
            continue
        if path.is_symlink():
            raise OnboardingError(f"Символическая ссылка в ядре: {relative.as_posix()}")
        if not path.is_file():
            continue
        data = path.read_bytes()
        records.append(relative.as_posix().encode("utf-8") + b"\0" + _digest(data).encode("ascii") + b"\n")
    return _digest(b"".join(records))


def _safe_target(root: Path, relative: str) -> Path:
    if relative not in OWNED_PATHS:
        raise OnboardingError(f"Путь не принадлежит онбордингу: {relative}")
    path = root / relative
    if not path.resolve(strict=False).is_relative_to(root):
        raise OnboardingError(f"Путь выходит за пределы проекта: {relative}")
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise OnboardingError(f"Символическая ссылка в целевом пути: {relative}")
    return path


def _existing(root: Path, relative: str) -> bytes | None:
    path = _safe_target(root, relative)
    if not path.exists():
        return None
    if not path.is_file():
        raise OnboardingError(f"Ожидался файл: {relative}")
    return path.read_bytes()


def _utf8(data: bytes | None, relative: str) -> str:
    if data is None:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OnboardingError(f"Файл не в UTF-8: {relative}") from exc


def _validate_answers(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise OnboardingError("Сведения о проекте должны быть объектом JSON")
    for key in ("project_name", "summary"):
        if not isinstance(raw.get(key), str) or not raw[key].strip():
            raise OnboardingError(f"Требуется непустая строка {key}")
    for key in ("test_commands", "constraints"):
        value = raw.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise OnboardingError(f"{key} должен быть списком непустых строк")
    return {key: raw[key] for key in ("project_name", "summary", "test_commands", "constraints")}


def _context(answers: dict[str, Any]) -> str:
    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "- Не указаны"

    return (
        f"# Контекст проекта: {answers['project_name']}\n\n"
        f"## Назначение\n\n{answers['summary']}\n\n"
        f"## Команды проверок\n\n{bullets(answers['test_commands'])}\n\n"
        f"## Ограничения\n\n{bullets(answers['constraints'])}\n"
    )


def _append_block(existing: str, block: str, relative: str, *, begin: str = BEGIN, end: str = END) -> str:
    if (
        existing.count(begin) != existing.count(end)
        or existing.count(begin) > 1
        or (begin in existing and existing.index(end) < existing.index(begin))
    ):
        raise OnboardingError(f"Некорректные маркеры в {relative}")
    if begin in existing:
        start = existing.index(begin)
        finish = existing.index(end, start) + len(end)
        return existing[:start] + block.rstrip("\n") + existing[finish:]
    separator = "" if not existing else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + separator + block


def _is_exact_block(existing: str, body: str, *, begin: str, end: str, relative: str) -> bool:
    """Check whether a managed marker pair contains exactly the expected body."""
    if begin not in existing and end not in existing:
        return False
    if (
        existing.count(begin) != 1
        or existing.count(end) != 1
        or existing.index(end) < existing.index(begin)
    ):
        raise OnboardingError(f"Некорректные маркеры в {relative}")
    start = existing.index(begin) + len(begin)
    finish = existing.index(end, start)
    return existing[start:finish].strip() == body.strip()


def _change(root: Path, relative: str, content: str, *, create_only: bool = False) -> dict[str, Any] | None:
    before = _existing(root, relative)
    after = content.encode("utf-8")
    if before == after:
        return None
    if create_only and before is not None:
        raise OnboardingError(f"Уже существует файл проекта с другим содержимым: {relative}")
    return {
        "path": relative,
        "before_sha256": _digest(before) if before is not None else None,
        "after_sha256": _digest(after),
        "content": content,
    }


def build_plan(target: Path, core: Path, answers: dict[str, Any]) -> dict[str, Any]:
    target = target.resolve(strict=True)
    core = core.resolve(strict=True)
    if not target.is_dir() or not core.is_dir():
        raise OnboardingError("Целевой проект и ядро должны быть каталогами")
    if not core.is_relative_to(target):
        raise OnboardingError("Ядро должно находиться внутри целевого проекта")
    if not (core / "README.md").is_file() or not (core / "docs").is_dir():
        raise OnboardingError("Указан неполный каталог ядра")
    answers = _validate_answers(answers)
    core_path = core.relative_to(target).as_posix() or "."
    if core_path == ".":
        mode = "self-hosted"
    elif core_path == "tools/orchestrator":
        mode = "attached"
        if not (core / ".agents/skills/orchestrator-task-manager/SKILL.md").is_file():
            raise OnboardingError("В подключённом ядре отсутствует skill Task Manager Service")
    else:
        raise OnboardingError("Внешнее ядро должно находиться в tools/orchestrator")

    project_config = {
        "schema_version": 1,
        "core_path": core_path,
        "mode": mode,
        "context_path": ".orchestrator/project-context.md",
    }
    desired = [
        (".orchestrator/project.json", json.dumps(project_config, ensure_ascii=False, indent=2) + "\n", True),
        (".orchestrator/project-context.md", _context(answers), True),
    ]
    if mode == "attached":
        old = _utf8(_existing(target, "AGENTS.md"), "AGENTS.md")
        block = (
            f"{BEGIN}\n"
            f"Для работы с Orchestrator используй `{core_path}/docs/README.md` и "
            "`.orchestrator/project-context.md`.\n"
            f"Для работы с задачами прочитай `{core_path}/.agents/skills/orchestrator-task-manager/SKILL.md`.\n"
            f"{END}\n"
        )
        desired.append(("AGENTS.md", _append_block(old, block, "AGENTS.md"), False))

    old_ignore = _utf8(_existing(target, ".gitignore"), ".gitignore")
    if any(line.strip() in {".orchestrator/", ".orchestrator"} for line in old_ignore.splitlines()):
        raise OnboardingError(
            "Правило .orchestrator/ скрывает версионируемую конфигурацию; "
            "сначала согласуйте изменение .gitignore"
        )
    legacy_ignore_block = _is_exact_block(
        old_ignore,
        ".orchestrator/state/",
        begin=BEGIN,
        end=END,
        relative=".gitignore",
    )
    if ".orchestrator/state/" not in old_ignore.splitlines() or legacy_ignore_block:
        ignore_block = f"{IGNORE_BEGIN}\n.orchestrator/state/\n{IGNORE_END}\n"
        if legacy_ignore_block:
            old_ignore = _append_block(
                old_ignore,
                ignore_block,
                ".gitignore",
                begin=BEGIN,
                end=END,
            )
        desired.append((
            ".gitignore",
            _append_block(old_ignore, ignore_block, ".gitignore", begin=IGNORE_BEGIN, end=IGNORE_END),
            False,
        ))

    changes = []
    for relative, content, create_only in desired:
        change = _change(target, relative, content, create_only=create_only)
        if change is not None:
            changes.append(change)
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "onboarding_version": ONBOARDING_VERSION,
        "target_root": str(target),
        "core_root": str(core),
        "core_fingerprint": _core_fingerprint(core),
        "changes": changes,
    }
    plan["plan_hash"] = _digest(_canonical(plan))
    return plan


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply_plan(plan: dict[str, Any], approved_hash: str) -> list[str]:
    if not isinstance(plan, dict) or plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise OnboardingError("Неизвестная версия плана")
    if plan.get("onboarding_version") != ONBOARDING_VERSION:
        raise OnboardingError("План создан другой версией onboarding")
    payload = {key: value for key, value in plan.items() if key != "plan_hash"}
    calculated = _digest(_canonical(payload))
    if calculated != plan.get("plan_hash") or calculated != approved_hash:
        raise OnboardingError("Хеш плана не совпадает с подтверждённым")
    target = Path(plan["target_root"]).resolve(strict=True)
    core = Path(plan["core_root"]).resolve(strict=True)
    if not core.is_relative_to(target) or not (core / "README.md").is_file():
        raise OnboardingError("Путь ядра изменился")
    if plan.get("core_fingerprint") != _core_fingerprint(core):
        raise OnboardingError("Содержимое ядра изменилось после preview")
    changes = plan.get("changes")
    if not isinstance(changes, list):
        raise OnboardingError("Некорректный список изменений")
    originals: dict[str, bytes | None] = {}
    destinations: dict[str, Path] = {}
    for change in changes:
        if not isinstance(change, dict) or not isinstance(change.get("content"), str):
            raise OnboardingError("Некорректное изменение в плане")
        relative = change.get("path")
        if not isinstance(relative, str) or relative in originals:
            raise OnboardingError("Повторный или некорректный путь в плане")
        destinations[relative] = _safe_target(target, relative)
        before = _existing(target, relative)
        if (_digest(before) if before is not None else None) != change.get("before_sha256"):
            raise OnboardingError(f"Файл изменился после preview: {relative}")
        if _digest(change["content"].encode("utf-8")) != change.get("after_sha256"):
            raise OnboardingError(f"Некорректное содержимое в плане: {relative}")
        originals[relative] = before

    written: list[str] = []
    try:
        for change in changes:
            relative = change["path"]
            _atomic_write(destinations[relative], change["content"].encode("utf-8"))
            written.append(relative)
        project_config = json.loads((target / ".orchestrator/project.json").read_text(encoding="utf-8"))
        if project_config.get("schema_version") != 1 or project_config.get("core_path") != core.relative_to(target).as_posix():
            raise OnboardingError("Проверка конфигурации после записи не прошла")
        if not (target / ".orchestrator/project-context.md").is_file():
            raise OnboardingError("Контекст проекта не создан")
    except (OSError, ValueError, OnboardingError) as exc:
        for relative in reversed(written):
            original = originals[relative]
            if original is None:
                destinations[relative].unlink(missing_ok=True)
            else:
                _atomic_write(destinations[relative], original)
        raise OnboardingError(f"Применение не удалось; записанные файлы восстановлены: {exc}") from exc
    return written


def _print_preview(plan: dict[str, Any], target: Path) -> None:
    print(f"План: {plan['plan_hash']}")
    print(f"Изменяемых файлов: {len(plan['changes'])}")
    for change in plan["changes"]:
        relative = change["path"]
        before = _utf8(_existing(target, relative), relative)
        diff = difflib.unified_diff(
            before.splitlines(keepends=True),
            change["content"].splitlines(keepends=True),
            fromfile=f"a/{relative}",
            tofile=f"b/{relative}",
        )
        print("".join(diff), end="")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Настройка проекта для Orchestrator")
    commands = parser.add_subparsers(dest="command", required=True)
    preview = commands.add_parser("preview", help="Построить план без изменения проекта")
    preview.add_argument("--target", type=Path, required=True)
    preview.add_argument("--core", type=Path, required=True)
    preview.add_argument("--answers", type=Path, required=True)
    preview.add_argument("--output", type=Path, required=True)
    apply = commands.add_parser("apply", help="Применить подтверждённый план")
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--approved-hash", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "preview":
            answers = json.loads(args.answers.read_text(encoding="utf-8"))
            plan = build_plan(args.target, args.core, answers)
            if args.output.exists():
                raise OnboardingError(f"Файл плана уже существует: {args.output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(args.output, (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            _print_preview(plan, Path(plan["target_root"]))
        else:
            plan = json.loads(args.plan.read_text(encoding="utf-8"))
            written = apply_plan(plan, args.approved_hash)
            print(f"Настройка завершена; изменено файлов: {len(written)}")
        return 0
    except (OSError, ValueError, OnboardingError) as exc:
        parser.exit(2, f"Ошибка онбординга: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
