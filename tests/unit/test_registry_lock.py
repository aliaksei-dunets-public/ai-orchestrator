from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from orchestrator.registry_lock import RegistryLock, RegistryLockError


class RegistryLockTests(unittest.TestCase):
    def test_contention_and_owner_checked_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = RegistryLock(temporary, owner_token="first")
            second = RegistryLock(temporary, owner_token="second")
            first.acquire()
            self.assertEqual(second.inspect().status, "live")
            with self.assertRaises(RegistryLockError):
                second.acquire(timeout_seconds=0)
            first.release()
            second.acquire(timeout_seconds=0)
            second.release()

    def test_dead_stale_lock_is_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lock = RegistryLock(
                temporary,
                owner_token="replacement",
                stale_after_seconds=0.01,
            )
            lock.path.parent.mkdir(parents=True)
            lock.path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "owner_token": "stale",
                        "pid": max(os.getpid() + 1_000_000, 999_999),
                        "hostname": "test",
                        "created_at": time.time() - 60,
                    }
                ),
                encoding="utf-8",
            )
            lock.acquire(timeout_seconds=0)
            self.assertEqual(lock.inspect().owner_token, "replacement")
            lock.release()

    def test_invalid_metadata_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lock = RegistryLock(temporary)
            lock.path.parent.mkdir(parents=True)
            lock.path.write_text("{", encoding="utf-8")
            with self.assertRaises(RegistryLockError):
                lock.acquire(timeout_seconds=0)
