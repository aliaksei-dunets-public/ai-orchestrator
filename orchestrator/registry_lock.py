from __future__ import annotations

import json
import os
import socket
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


class RegistryLockError(RuntimeError):
    pass


@dataclass(frozen=True)
class LockState:
    status: str
    owner_token: str | None
    pid: int | None
    created_at: float | None


def _process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class RegistryLock:
    """Bounded, process-aware lock for Task Registry mutations."""

    def __init__(
        self,
        tasks_root: Path | str,
        *,
        owner_token: str | None = None,
        stale_after_seconds: float = 300,
    ) -> None:
        if stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        self.tasks_root = Path(tasks_root).resolve()
        self.path = self.tasks_root / "checkpoints" / "registry.lock"
        self.owner_token = owner_token or uuid.uuid4().hex
        self.stale_after_seconds = stale_after_seconds
        self.acquired = False

    def _read(self) -> dict[str, object] | None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RegistryLockError(f"registry lock metadata is invalid: {exc}") from exc
        if not isinstance(payload, dict):
            raise RegistryLockError("registry lock metadata must be an object")
        return payload

    def inspect(self) -> LockState:
        payload = self._read()
        if payload is None:
            return LockState("unlocked", None, None, None)
        token = payload.get("owner_token")
        pid = payload.get("pid")
        created_at = payload.get("created_at")
        if (
            not isinstance(token, str)
            or not token
            or not isinstance(pid, int)
            or isinstance(pid, bool)
            or not isinstance(created_at, (int, float))
            or isinstance(created_at, bool)
        ):
            return LockState("invalid", None, None, None)
        age = max(0.0, time.time() - float(created_at))
        status = (
            "stale"
            if age >= self.stale_after_seconds and not _process_is_alive(pid)
            else "live"
        )
        return LockState(status, token, pid, float(created_at))

    def _remove_stale(self, state: LockState) -> bool:
        if state.status != "stale" or state.owner_token is None:
            return False
        current = self._read()
        if current is None or current.get("owner_token") != state.owner_token:
            return False
        try:
            self.path.unlink()
        except FileNotFoundError:
            return True
        return True

    def acquire(self, *, timeout_seconds: float = 5, poll_seconds: float = 0.05) -> None:
        if timeout_seconds < 0 or poll_seconds <= 0:
            raise ValueError("lock timeout must be non-negative and poll interval positive")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout_seconds
        payload = {
            "schema_version": 1,
            "owner_token": self.owner_token,
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "created_at": time.time(),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        while True:
            try:
                descriptor = os.open(
                    self.path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
            except FileExistsError:
                state = self.inspect()
                if state.status == "invalid":
                    raise RegistryLockError("registry lock metadata is invalid")
                if self._remove_stale(state):
                    continue
                if time.monotonic() >= deadline:
                    raise RegistryLockError(
                        f"registry lock is held by {state.owner_token or 'unknown owner'}"
                    )
                time.sleep(min(poll_seconds, max(0.0, deadline - time.monotonic())))
                continue
            try:
                os.write(descriptor, encoded)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            self.acquired = True
            return

    def release(self) -> None:
        if not self.acquired:
            return
        payload = self._read()
        if payload is None:
            self.acquired = False
            return
        if payload.get("owner_token") != self.owner_token:
            raise RegistryLockError("registry lock ownership changed before release")
        self.path.unlink()
        self.acquired = False

    def __enter__(self) -> RegistryLock:
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()
