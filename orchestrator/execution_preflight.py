"""Read-only проверка approved package и code corpus перед execution claim."""
from __future__ import annotations

import json
import re
import stat
from pathlib import Path

from orchestrator_task_manager import TaskManagerService

from .artifact_repository import ArtifactRepository
from .knowledge_contracts import CorpusPolicy
from .knowledge_snapshot import checked_path, safe_relative, snapshot_sources, canonical_json,allowed_parts
from .preparation_primitives import PreparationError, _text, _strings


class ExecutionError(PreparationError):
    """Rejected execution action, не свидетельство rollback agent edits."""


def revision(snapshot):
    return "code-corpus/v1:" + snapshot.digest


class ExecutionPreflight:
    max_artifact_bytes = 2 * 1024 * 1024

    def __init__(self, project_root: Path, *, policy: CorpusPolicy | None = None):
        root = Path(project_root).absolute()
        checked_path(Path(root.anchor),root)
        self.repository = ArtifactRepository(root)
        self.root = self.repository.project_root
        self.service = TaskManagerService(self.root)
        self.policy = policy or CorpusPolicy()

    def source_snapshot(self):
        return snapshot_sources(self.root,self.policy)

    def source_revision(self):
        return revision(self.source_snapshot())

    @staticmethod
    def task_guard(task,expected):
        if type(expected) is not int or task["version"] != expected:
            raise ExecutionError("task_version_conflict","Нужна прочитанная task version")

    def _stored(self,record,role):
        if not isinstance(record,dict) or record.get("role") != role:
            raise ExecutionError("stale_package","Неверный immutable record")
        stored=self.repository.get(record["ref"],role,record["version"],max_bytes=self.max_artifact_bytes)
        if stored.record.to_dict() != record or stored.record.contract != role.replace("_","-")+"/v1":
            raise ExecutionError("stale_package","Immutable metadata/contract неверны")
        return stored.content

    def bindings(self,task):
        """Проверяет immutable bindings; не требует исходного baseline после own work."""
        try:
            artifacts=task["artifacts"]
            plan=artifacts["plan"]; review=artifacts["plan_review"]; package=artifacts["execution_package"]
            parts=package["ref"].split(":")
            if len(parts)!=3 or parts[1]!="execution_package":
                raise ExecutionError("unsupported_package","Нужен immutable package от AgentPreparation; reprepare")
            stored=self.repository.get(parts[0],parts[1],parts[2],max_bytes=self.max_artifact_bytes)
            if stored.record.contract != "execution-package/v1":
                raise ExecutionError("stale_package","Неверный package contract")
            value=json.loads(stored.content)
            if (not isinstance(value,dict) or value.get("task_ref") != task["id"]
                    or type(value.get("definition_version")) is not int
                    or value["definition_version"] != task["definition_version"]
                    or value.get("entrypoint") != "execution_preflight"):
                raise ExecutionError("stale_package","Package task/definition/entrypoint неверны")
            if (value["plan"] != plan["metadata"]["repository"]
                    or value["plan_review"] != review["metadata"]["repository"]
                    or plan["sha256"] != value["plan"]["sha256"]
                    or plan["metadata"].get("definition_version") != task["definition_version"]
                    or review["metadata"].get("status") != "approved"
                    or review["metadata"].get("definition_version") != task["definition_version"]
                    or review["metadata"].get("plan_sha256") != plan["sha256"]
                    or package["metadata"].get("plan_sha256") != plan["sha256"]
                    or value["prepared_source_revision"] != task["prepared_source_revision"]
                    or package["metadata"].get("prepared_source_revision") != task["prepared_source_revision"]):
                raise ExecutionError("stale_package","Plan/Review/Package binding неверен")
            content=self._stored(value["plan"],"plan")
            # Проверенная проекция, не произвольный Markdown parser.
            projection=checked_path(self.root,self.root/plan["path"])
            if not projection.is_relative_to(self.root/".orchestrator"/"tasks"/task["id"]):
                raise ExecutionError("stale_package","Plan projection вне каталога задачи")
            if not stat.S_ISREG(projection.stat().st_mode):
                raise ExecutionError("integrity_error","Plan projection не обычный файл")
            with projection.open("rb") as stream:
                projected=stream.read(self.max_artifact_bytes+1)
            if projected != content:
                raise ExecutionError("integrity_error","Plan projection отличается от immutable payload")
            prefix="# План "+task["id"]+"\n\n"+chr(96)*3+"json\n"
            suffix="\n"+chr(96)*3+"\n"
            document=content.decode("utf-8")
            if not document.startswith(prefix) or not document.endswith(suffix):
                raise ExecutionError("unsupported_plan","Нужен structured plan/v1 от preparation")
            payload=json.loads(document[len(prefix):-len(suffix)])
            approved=json.loads(self._stored(value["plan_review"],"plan_review"))
            if (not isinstance(approved,dict) or approved.get("approved_binding") !=
                    {"plan_sha256":plan["sha256"],"definition_version":task["definition_version"]}
                    or approved.get("zero_context_executable") is not True
                    or set(_strings(approved.get("criterion_ids"),"criterion_ids",nonempty=True)) !=
                       {entry["id"] for entry in task["acceptance_criteria"]}):
                raise ExecutionError("stale_package","Review payload не подтверждает binding/coverage")
            findings=approved.get("findings")
            if (not isinstance(findings,list) or any(not isinstance(f,dict) or
                    (f.get("severity","minor") in {"major","critical"} and f.get("status","open")=="open")
                    for f in findings)):
                raise ExecutionError("stale_package","Review содержит незакрытые major/critical findings")
            units=payload.get("work_units") if isinstance(payload,dict) else None
            if not isinstance(units,list) or not 1 <= len(units) <= 100:
                raise ExecutionError("unsupported_plan","Нужны 1..100 work_units")
            ids=set()
            for unit in units:
                if not isinstance(unit,dict):
                    raise ExecutionError("unsupported_plan","Work unit должен быть объектом")
                uid=_text(unit.get("id"),"unit_id")
                if uid in ids:
                    raise ExecutionError("unsupported_plan","Duplicate unit_id")
                ids.add(uid)
                _text(unit.get("goal"),"goal")
                for field in ("files_objects","expected_result","validation"):
                    _strings(unit.get(field),field,nonempty=True)
                for path in unit["files_objects"]:
                    safe_relative(path)
                    if path=="." or not allowed_parts(Path(path)):
                        raise ExecutionError("unsupported_plan","Scope '.' слишком широк")
                _strings(unit.get("depends_on",[]),"depends_on")
            done=set(); remaining={u["id"]:set(u.get("depends_on",[])) for u in units}
            while remaining:
                ready={uid for uid,deps in remaining.items() if deps.issubset(done)}
                if not ready:
                    raise ExecutionError("unsupported_plan","Цикл/неизвестная зависимость work units")
                done.update(ready); remaining={uid:deps for uid,deps in remaining.items() if uid not in ready}
            return {"package":stored.record.to_dict(),"plan":value["plan"],"plan_review":value["plan_review"],
                    "prepared_source_revision":value["prepared_source_revision"],"work_units":units}
        except (KeyError,TypeError,ValueError,UnicodeError) as exc:
            raise ExecutionError("stale_package","Невалидный immutable preparation package") from exc

    def check(self,task_id: str,*,expected_task_version: int):
        task=self.service.get_task(task_id)
        self.task_guard(task,expected_task_version)
        if (task["status"] != "ready" or task["active_claim"] or task["active_run_ref"]
                or any(b["blocking"] and b["status"]=="open" for b in task["blockers"])):
            raise ExecutionError("task_not_ready","Нужна ready без claim/run/blockers")
        binding=self.bindings(task)
        if re.fullmatch(r"code-corpus/v1:[0-9a-f]{64}",binding["prepared_source_revision"]) is None:
            raise ExecutionError("unsupported_source_revision","Opaque source revision требует reprepare с fingerprint")
        snapshot=self.source_snapshot()
        if binding["prepared_source_revision"] != revision(snapshot):
            raise ExecutionError("source_drift","Code corpus изменился после preparation; нужен reprepare")
        self.task_guard(self.service.get_task(task_id),expected_task_version)
        return {"contract":"execution-preflight/v1","status":"fresh","task":task,"binding":binding,
                "source_snapshot":json.loads(canonical_json(snapshot.to_dict())),
                "source_revision":revision(snapshot),"limitations":["code-only fingerprint; docs/config/dependencies не покрыты"]}
