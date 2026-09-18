"""Безопасное локальное хранилище версионируемых артефактов Orchestrator."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
import threading
import stat
from functools import wraps
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.IGNORECASE)


class ArtifactError(Exception):
    """Структурированная ошибка Artifact Repository."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = copy.deepcopy(self.details)
        return result


def _identifier(value: Any, field: str) -> str:
    if (not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None
            or value.endswith(".") or _RESERVED.match(value)):
        raise ArtifactError(
            "validation_failed",
            f"{field} должен быть безопасным одноуровневым идентификатором",
            field=field,
        )
    return value


def _filesystem_errors(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except OSError as exc:
            raise ArtifactError("repository_failure", "Файловая операция repository не выполнена",
                                operation=method.__name__) from exc
    return wrapped


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(ord(char) < 32 for char in value):
        raise ArtifactError("validation_failed", f"{field} должен быть непустой строкой", field=field)
    return value


def _content_bytes(content: bytes | bytearray | memoryview | str, field: str = "content") -> bytes:
    if isinstance(content, str):
        return content.encode("utf-8")
    if isinstance(content, (bytes, bytearray, memoryview)):
        return bytes(content)
    raise ArtifactError("validation_failed", f"{field} должен быть bytes или UTF-8 строкой", field=field)


@dataclass(frozen=True)
class ArtifactRecord:
    """Метаданные опубликованной версии артефакта."""

    ref: str
    role: str
    version: str
    contract: str
    media_type: str
    sha256: str
    size: int
    path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "role": self.role,
            "version": self.version,
            "contract": self.contract,
            "media_type": self.media_type,
            "sha256": self.sha256,
            "size": self.size,
            "path": self.path,
        }


@dataclass(frozen=True)
class StoredArtifact:
    """Проверенный payload и его immutable metadata record."""

    record: ArtifactRecord
    content: bytes


class ArtifactRepository:
    """Filesystem repository под фиксированным ``.orchestrator/artifacts``.

    Репозиторий не знает о задачах, workflow runs или SQLite. Внутри одного
    процесса запись сериализуется; публикация payload и manifest выполняется
    во временном каталоге и единым атомарным переименованием всей версии.
    """

    _write_guard = threading.RLock()

    @_filesystem_errors
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        if not self.project_root.is_dir():
            raise ArtifactError("validation_failed", "project_root должен быть существующим каталогом")
        self.root = self.project_root / ".orchestrator" / "artifacts"

    @_filesystem_errors
    def put(
        self,
        ref: str,
        role: str,
        version: str,
        content: bytes | bytearray | memoryview | str,
        *,
        contract: str = "opaque/v1",
        media_type: str = "application/octet-stream",
    ) -> ArtifactRecord:
        ref = _identifier(ref, "ref")
        role = _identifier(role, "role")
        version = _identifier(version, "version")
        contract = _text(contract, "contract")
        media_type = _text(media_type, "media_type")
        payload = _content_bytes(content)
        digest = hashlib.sha256(payload).hexdigest()
        with self._write_guard:
            entry_dir = self._entry_dir(ref, role, version)
            payload_path = entry_dir / "payload.bin"
            manifest_path = entry_dir / "manifest.json"
            self._safe_path(payload_path)
            self._safe_path(manifest_path)
            record = ArtifactRecord(ref, role, version, contract, media_type, digest, len(payload),
                                    self._relative(payload_path))
            if entry_dir.exists():
                existing = self._read_record(manifest_path, ref=ref, role=role, version=version)
                if existing == record and self._read_verified_payload(existing, payload_path) == payload:
                    return existing
                raise ArtifactError("artifact_exists", "Версия артефакта уже существует", ref=ref, version=version)
            entry_dir.parent.mkdir(parents=True, exist_ok=True)
            self._safe_path(entry_dir)
            # Ни один читатель не видит версию до публикации обоих файлов.
            with tempfile.TemporaryDirectory(dir=entry_dir.parent, prefix=".staging-") as stage_name:
                stage = Path(stage_name)
                self._publish(stage / "payload.bin", payload)
                self._publish(stage / "manifest.json", self._manifest_bytes(record))
                self._safe_path(entry_dir)
                if entry_dir.exists():
                    raise ArtifactError("artifact_exists", "Версия артефакта уже существует", ref=ref, version=version)
                os.rename(stage, entry_dir)
        return record

    def put_json(
        self,
        ref: str,
        role: str,
        version: str,
        value: Any,
        *,
        contract: str = "json/v1",
    ) -> ArtifactRecord:
        try:
            content = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ArtifactError("validation_failed", "value нельзя сериализовать в canonical JSON") from exc
        return self.put(ref, role, version, content, contract=contract, media_type="application/json")

    @_filesystem_errors
    def get(self, ref: str, role: str, version: str, *, max_bytes: int | None = None) -> StoredArtifact:
        if max_bytes is not None and (type(max_bytes) is not int or max_bytes < 1):
            raise ArtifactError("validation_failed", "max_bytes должен быть положительным целым")
        ref = _identifier(ref, "ref")
        role = _identifier(role, "role")
        version = _identifier(version, "version")
        with self._write_guard:
            entry_dir = self._entry_dir(ref, role, version)
            manifest_path = entry_dir / "manifest.json"
            payload_path = entry_dir / "payload.bin"
            self._safe_path(manifest_path)
            self._safe_path(payload_path)
            if not entry_dir.exists():
                raise ArtifactError("artifact_not_found", "Версия артефакта не найдена", ref=ref, version=version)
            record = self._read_record(manifest_path, ref=ref, role=role, version=version)
            content = self._read_verified_payload(record, payload_path, max_bytes=max_bytes)
        return StoredArtifact(record=record, content=content)

    def verify(self, ref: str, role: str, version: str, *, max_bytes: int | None = None) -> ArtifactRecord:
        return self.get(ref, role, version, max_bytes=max_bytes).record

    @_filesystem_errors
    def list(self, *, ref: str | None = None, role: str | None = None) -> tuple[ArtifactRecord, ...]:
        if ref is not None:
            ref = _identifier(ref, "ref")
        if role is not None:
            role = _identifier(role, "role")
        with self._write_guard:
            self._safe_path(self.root)
            if not self.root.exists():
                return ()
            records: list[ArtifactRecord] = []
            for ref_dir in self._directories(self.root):
                if ref is not None and ref_dir.name != ref:
                    continue
                for role_dir in self._directories(ref_dir):
                    if role is not None and role_dir.name != role:
                        continue
                    for version_dir in self._directories(role_dir, staging=True):
                        records.append(self._read_record(
                            version_dir / "manifest.json", ref=ref_dir.name, role=role_dir.name,
                            version=version_dir.name,
                        ))
        return tuple(sorted(records, key=lambda item: (item.version, item.role, item.ref)))

    def _directories(self, parent: Path, *, staging: bool = False) -> tuple[Path, ...]:
        result = []
        seen = set()
        for child in sorted(parent.iterdir()):
            self._safe_path(child)
            if staging and child.name.startswith(".staging-"):
                continue
            if not child.is_dir():
                raise ArtifactError("integrity_error", "Неожиданный файл в структуре repository", path=str(child))
            try:
                _identifier(child.name, "directory")
            except ArtifactError as exc:
                raise ArtifactError("integrity_error", "Некорректный сегмент каталога repository", path=str(child)) from exc
            if child.name.casefold() in seen:
                raise ArtifactError("integrity_error", "Коллизия регистра идентификаторов", path=str(child))
            seen.add(child.name.casefold())
            result.append(child)
        return tuple(result)

    def _entry_dir(self, ref: str, role: str, version: str) -> Path:
        candidate = self.root / ref / role / version
        self._safe_path(candidate)
        parent = self.root
        for segment in (ref, role, version):
            if parent.exists():
                for child in parent.iterdir():
                    if child.name.casefold() == segment.casefold() and child.name != segment:
                        raise ArtifactError("validation_failed", "Идентификатор имеет alias другого регистра", field=segment)
            parent = parent / segment
        return candidate

    def _safe_path(self, candidate: Path) -> None:
        relative = candidate.relative_to(self.project_root)
        current = self.project_root
        for part in relative.parts:
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise ArtifactError("validation_failed", "Symlink/junction в пути repository запрещён", path=str(current))
        if not candidate.resolve(strict=False).is_relative_to(self.project_root):
            raise ArtifactError("validation_failed", "Путь repository выходит за project_root", path=str(candidate))

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.project_root).as_posix()

    @staticmethod
    def _manifest_bytes(record: ArtifactRecord) -> bytes:
        manifest = {
            "format_version": 1,
            "ref": record.ref,
            "role": record.role,
            "version": record.version,
            "contract": record.contract,
            "media_type": record.media_type,
            "sha256": record.sha256,
            "size": record.size,
            "payload": "payload.bin",
        }
        return (json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

    @staticmethod
    def _publish(target: Path, content: bytes) -> None:
        if target.exists():
            raise ArtifactError("artifact_exists", "Целевой файл артефакта уже существует", path=str(target))
        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp", delete=False) as handle:
                temp_name = handle.name
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if target.exists():
                raise ArtifactError("artifact_exists", "Целевой файл артефакта уже существует", path=str(target))
            os.replace(temp_name, target)
            temp_name = None
        except ArtifactError:
            raise
        except OSError as exc:
            raise ArtifactError("repository_failure", "Не удалось атомарно опубликовать файл", path=str(target)) from exc
        finally:
            if temp_name:
                try:
                    Path(temp_name).unlink(missing_ok=True)
                except OSError:
                    pass

    def _read_record(self, manifest_path: Path, *, ref: str, role: str, version: str) -> ArtifactRecord:
        self._safe_path(manifest_path)
        try:
            if not stat.S_ISREG(manifest_path.stat().st_mode):
                raise ArtifactError("integrity_error", "Манифест не является обычным файлом")
            with manifest_path.open("rb") as stream:
                content = stream.read(65537)
            if len(content) > 65536:
                raise ArtifactError("integrity_error", "Манифест превышает 64 KiB")
            raw = json.loads(content)
        except (FileNotFoundError, IsADirectoryError, UnicodeError, json.JSONDecodeError) as exc:
            raise ArtifactError("integrity_error", "Манифест артефакта повреждён", path=str(manifest_path)) from exc
        if (not isinstance(raw, dict) or type(raw.get("format_version")) is not int
                or raw.get("format_version") != 1 or raw.get("payload") != "payload.bin"):
            raise ArtifactError("integrity_error", "Манифест артефакта имеет неизвестную форму", path=str(manifest_path))
        if raw.get("ref") != ref or raw.get("role") != role or raw.get("version") != version:
            raise ArtifactError("integrity_error", "Манифест не соответствует пути артефакта", path=str(manifest_path))
        try:
            _identifier(ref, "ref")
            _identifier(role, "role")
            _identifier(version, "version")
            contract = _text(raw.get("contract"), "contract")
            media_type = _text(raw.get("media_type"), "media_type")
        except ArtifactError as exc:
            raise ArtifactError("integrity_error", "Некорректные поля манифеста", path=str(manifest_path)) from exc
        digest = raw.get("sha256")
        size = raw.get("size")
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise ArtifactError("integrity_error", "Манифест содержит некорректный sha256", path=str(manifest_path))
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ArtifactError("integrity_error", "Манифест содержит некорректный size", path=str(manifest_path))
        return ArtifactRecord(ref, role, version, contract, media_type, digest, size,
                              self._relative(manifest_path.parent / "payload.bin"))

    def _read_verified_payload(self, record: ArtifactRecord, payload_path: Path, *, max_bytes: int | None = None) -> bytes:
        self._safe_path(payload_path)
        try:
            if max_bytes is not None and record.size > max_bytes:
                raise ArtifactError("artifact_size_limit", "Payload превышает заданный byte budget")
            if not stat.S_ISREG(payload_path.stat().st_mode):
                raise ArtifactError("integrity_error", "Payload не является обычным файлом")
            with payload_path.open("rb") as stream:
                content = stream.read((max_bytes if max_bytes is not None else record.size) + 1)
            if max_bytes is not None and len(content) > max_bytes:
                raise ArtifactError("artifact_size_limit", "Payload превышает заданный byte budget")
        except (FileNotFoundError, IsADirectoryError) as exc:
            raise ArtifactError("integrity_error", "Payload артефакта отсутствует или недоступен", path=str(payload_path)) from exc
        digest = hashlib.sha256(content).hexdigest()
        if len(content) != record.size or digest != record.sha256:
            raise ArtifactError("integrity_error", "SHA-256 или размер артефакта не совпадает", ref=record.ref,
                                version=record.version, expected=record.sha256, actual=digest)
        return content


__all__ = ["ArtifactError", "ArtifactRecord", "ArtifactRepository", "StoredArtifact"]
