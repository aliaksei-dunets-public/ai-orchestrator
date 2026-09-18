from __future__ import annotations

import hashlib
import ast
import json
import os
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator import ArtifactError, ArtifactRepository


class ArtifactRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repository = ArtifactRepository(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_put_get_verify_and_list_preserve_ref_role_version_and_hash(self) -> None:
        content = b"approved plan"
        record = self.repository.put("PLAN-1", "plan", "v1", content, contract="plan/v1", media_type="text/plain")
        self.assertEqual(record.sha256, hashlib.sha256(content).hexdigest())
        self.assertEqual(record.size, len(content))
        stored = self.repository.get("PLAN-1", "plan", "v1")
        self.assertEqual(stored.content, content)
        self.assertEqual(stored.record, record)
        self.assertEqual(self.repository.verify("PLAN-1", "plan", "v1"), record)
        self.assertEqual(self.repository.list(), (record,))
        self.assertEqual(self.repository.list(role="plan"), (record,))

    def test_json_is_canonical_and_repeat_is_idempotent(self) -> None:
        first = self.repository.put_json("RESULT-1", "testing", "v1", {"z": 1, "a": "тест"})
        second = self.repository.put_json("RESULT-1", "testing", "v1", {"a": "тест", "z": 1})
        self.assertEqual(first, second)
        self.assertEqual(self.repository.get("RESULT-1", "testing", "v1").content,
                         '{"a":"тест","z":1}'.encode("utf-8"))

    def test_existing_version_rejects_different_payload_without_overwrite(self) -> None:
        self.repository.put("DOC-1", "documentation", "v1", "one")
        with self.assertRaises(ArtifactError) as caught:
            self.repository.put("DOC-1", "documentation", "v1", "two")
        self.assertEqual(caught.exception.code, "artifact_exists")
        self.assertEqual(self.repository.get("DOC-1", "documentation", "v1").content, b"one")

    def test_versions_and_roles_are_independent(self) -> None:
        v1 = self.repository.put("PLAN-2", "plan", "v1", "one")
        v2 = self.repository.put("PLAN-2", "plan", "v2", "two")
        review = self.repository.put("PLAN-2", "review", "v1", "review")
        self.assertEqual(self.repository.list(ref="PLAN-2"), (v1, review, v2))

    def test_traversal_and_absolute_identifiers_are_rejected(self) -> None:
        for value in ("../escape", "a/b", "C:\\escape", ".", "..", ""):
            with self.assertRaises(ArtifactError) as caught:
                self.repository.put(value, "plan", "v1", b"x")
            self.assertEqual(caught.exception.code, "validation_failed")
        with self.assertRaises(ArtifactError):
            self.repository.put("SAFE", "../role", "v1", b"x")
        with self.assertRaises(ArtifactError):
            self.repository.put("SAFE", "plan", "../v1", b"x")

    def test_tampered_payload_is_rejected_by_read_and_verify(self) -> None:
        self.repository.put("TAMPER-1", "testing", "v1", b"original")
        payload = self.root / ".orchestrator" / "artifacts" / "TAMPER-1" / "testing" / "v1" / "payload.bin"
        payload.write_bytes(b"tampered")
        with self.assertRaises(ArtifactError) as caught:
            self.repository.get("TAMPER-1", "testing", "v1")
        self.assertEqual(caught.exception.code, "integrity_error")

    def test_tampered_manifest_is_rejected(self) -> None:
        self.repository.put("MANIFEST-1", "plan", "v1", b"payload")
        manifest = self.root / ".orchestrator" / "artifacts" / "MANIFEST-1" / "plan" / "v1" / "manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["payload"] = "../outside"
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ArtifactError) as caught:
            self.repository.get("MANIFEST-1", "plan", "v1")
        self.assertEqual(caught.exception.code, "integrity_error")

    def test_missing_artifact_is_structured(self) -> None:
        with self.assertRaises(ArtifactError) as caught:
            self.repository.get("MISSING", "testing", "v1")
        self.assertEqual(caught.exception.code, "artifact_not_found")

    def test_repository_does_not_depend_on_task_manager_or_sqlite(self) -> None:
        source = Path(__file__).parents[1] / "orchestrator" / "artifact_repository.py"
        text = source.read_text(encoding="utf-8")
        imports = []
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any(name.startswith(("sqlite", "orchestrator_task_manager")) for name in imports))

    def test_failed_manifest_and_failed_directory_commit_leave_no_partial_version(self) -> None:
        original = ArtifactRepository._publish

        def fail_manifest(target, content):
            if target.name == "manifest.json":
                raise OSError("injected manifest failure")
            return original(target, content)

        for failure in (patch.object(ArtifactRepository, "_publish", side_effect=fail_manifest),
                        patch("orchestrator.artifact_repository.os.rename", side_effect=OSError("injected commit failure"))):
            with failure, self.assertRaises(ArtifactError) as caught:
                self.repository.put("PARTIAL", "testing", "v1", b"payload")
            self.assertEqual(caught.exception.code, "repository_failure")
            self.assertEqual(self.repository.list(), ())
            parent = self.repository.root / "PARTIAL" / "testing"
            self.assertEqual(tuple(parent.iterdir()), ())
        record = self.repository.put("PARTIAL", "testing", "v1", b"payload")
        self.assertEqual(self.repository.list(), (record,))

    def test_portable_identifiers_and_case_aliases(self) -> None:
        for value in ("trailing.", "space ", "CON", "NUL.txt", "LPT1", "com9.json"):
            with self.subTest(value=value), self.assertRaises(ArtifactError) as caught:
                self.repository.put(value, "testing", "v1", b"x")
            self.assertEqual(caught.exception.code, "validation_failed")
        record = self.repository.put("CaseRef", "Testing", "V1", b"one")
        for ref, role, version in (("caseref", "Testing", "V2"),
                                   ("CaseRef", "testing", "V2"),
                                   ("CaseRef", "Testing", "v1")):
            with self.subTest(key=(ref, role, version)), self.assertRaises(ArtifactError) as caught:
                self.repository.put(ref, role, version, b"two")
            self.assertEqual(caught.exception.code, "validation_failed")
        self.assertEqual(self.repository.list(), (record,))

    def test_malformed_manifest_fields_are_integrity_errors(self) -> None:
        self.repository.put("SCHEMA", "plan", "v1", b"x")
        manifest = self.repository.root / "SCHEMA" / "plan" / "v1" / "manifest.json"
        valid = json.loads(manifest.read_text(encoding="utf-8"))
        for field, value in (("ref", "bad ref"), ("role", "bad role"), ("version", "bad version"),
                             ("contract", ""), ("media_type", ""), ("sha256", "bad"),
                             ("size", True), ("size", -1), ("format_version", True)):
            with self.subTest(field=field, value=value):
                manifest.write_text(json.dumps({**valid, field: value}), encoding="utf-8")
                for read in (lambda: self.repository.get("SCHEMA", "plan", "v1"), self.repository.list):
                    with self.assertRaises(ArtifactError) as caught:
                        read()
                    self.assertEqual(caught.exception.code, "integrity_error")
        manifest.write_text(json.dumps(valid), encoding="utf-8")

    def test_list_rejects_invalid_directory_identifiers(self) -> None:
        record = self.repository.put("VALID", "plan", "v1", b"x")
        source = self.repository.root / record.ref
        shutil.copytree(source, self.repository.root / "bad ref")
        with self.assertRaises(ArtifactError) as caught:
            self.repository.list()
        self.assertEqual(caught.exception.code, "integrity_error")

    def test_filesystem_errors_are_structured(self) -> None:
        self.repository.put("IO", "testing", "v1", b"x")
        cases = (
            ("exists", lambda: self.repository.put("OTHER", "testing", "v1", b"x")),
            ("iterdir", self.repository.list),
            ("open", lambda: self.repository.get("IO", "testing", "v1")),
        )
        for method, action in cases:
            with self.subTest(method=method), patch.object(Path, method, side_effect=PermissionError("injected")):
                with self.assertRaises(ArtifactError) as caught:
                    action()
                self.assertEqual(caught.exception.code, "repository_failure")

    def test_missing_files_in_published_version_are_integrity_errors(self) -> None:
        for name in ("payload.bin", "manifest.json"):
            with self.subTest(name=name):
                self.repository.put(name, "testing", "v1", b"x")
                (self.repository.root / name / "testing" / "v1" / name).unlink()
                with self.assertRaises(ArtifactError) as caught:
                    self.repository.get(name, "testing", "v1")
                self.assertEqual(caught.exception.code, "integrity_error")

    def test_bounded_payload_and_manifest_reads(self) -> None:
        record = self.repository.put("BOUNDS","graph","v1",b"1234")
        self.assertEqual(self.repository.get("BOUNDS","graph","v1",max_bytes=4).content,b"1234")
        with self.assertRaises(ArtifactError) as caught:
            self.repository.verify("BOUNDS","graph","v1",max_bytes=3)
        self.assertEqual(caught.exception.code,"artifact_size_limit")
        for invalid in (True,0,-1,"4"):
            with self.assertRaises(ArtifactError):
                self.repository.get("BOUNDS","graph","v1",max_bytes=invalid)
        (self.root/record.path).write_bytes(b"123456")
        with self.assertRaises(ArtifactError) as caught:
            self.repository.get("BOUNDS","graph","v1",max_bytes=4)
        self.assertEqual(caught.exception.code,"artifact_size_limit")
        manifest=(self.root/record.path).with_name("manifest.json")
        manifest.write_bytes(b" "*65537)
        with self.assertRaises(ArtifactError) as caught:
            self.repository.get("BOUNDS","graph","v1")
        self.assertEqual(caught.exception.code,"integrity_error")

    def _directory_link(self, link: Path, target: Path) -> None:
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            result = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
                                    capture_output=True, timeout=10)
            if result.returncode:
                self.skipTest("Нет возможности создать symlink/junction")

    def test_root_junction_cannot_escape_project(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            external = Path(other)
            self._directory_link(self.repository.root, external)
            for action in (lambda: self.repository.put("OUT", "plan", "v1", b"x"),
                           self.repository.list, lambda: self.repository.get("OUT", "plan", "v1")):
                with self.assertRaises(ArtifactError) as caught:
                    action()
                self.assertEqual(caught.exception.code, "validation_failed")
            self.assertEqual(tuple(external.iterdir()), ())

    def test_entry_junction_is_rejected_by_list_and_get(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            external = Path(other)
            self._directory_link(self.repository.root / "LINK", external)
            for action in (self.repository.list, lambda: self.repository.get("LINK", "plan", "v1")):
                with self.assertRaises(ArtifactError) as caught:
                    action()
                self.assertEqual(caught.exception.code, "validation_failed")
            self.assertEqual(tuple(external.iterdir()), ())

    def test_payload_symlink_is_rejected_even_with_matching_hash(self) -> None:
        self.repository.put("LINK", "plan", "v1", b"x")
        payload = self.repository.root / "LINK" / "plan" / "v1" / "payload.bin"
        target = self.root / "outside.bin"
        target.write_bytes(b"x")
        payload.unlink()
        try:
            payload.symlink_to(target)
        except OSError:
            self.skipTest("Нет привилегий Windows для symlink файла")
        with self.assertRaises(ArtifactError) as caught:
            self.repository.get("LINK", "plan", "v1")
        self.assertEqual(caught.exception.code, "validation_failed")

    def test_repository_plan_requires_projection_for_task_manager(self) -> None:
        from orchestrator_task_manager import TaskError, TaskManagerService

        service = TaskManagerService(self.root)
        task = service.create_task(title="Test", task_type="implementation", original_request="Test",
                                   objective="Test", acceptance_criteria=["Test"])
        record = self.repository.put(task["id"], "plan", "v1", b"# Plan\n")
        with self.assertRaises(TaskError) as caught:
            service.attach_artifact(task["id"], task["version"], role="plan", ref=record.ref,
                                    path=record.path, sha256=record.sha256)
        self.assertEqual(caught.exception.code, "validation_failed")
        projection = self.root / ".orchestrator" / "tasks" / task["id"] / "plan.md"
        projection.parent.mkdir(parents=True)
        projection.write_bytes(self.repository.get(record.ref, record.role, record.version).content)
        attached = service.attach_artifact(task["id"], task["version"], role="plan", ref=record.ref,
                                           path=projection.relative_to(self.root).as_posix(),
                                           sha256=record.sha256, metadata={"repository": record.to_dict()})
        self.assertEqual(attached["artifacts"]["plan"]["metadata"]["repository"]["version"], "v1")


if __name__ == "__main__":
    unittest.main()
