"""AgentExecution: явные work units и guards, без executor callback/LLM."""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import uuid
from dataclasses import dataclass,field
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Mapping

from orchestrator_task_manager import TaskManagerService

from .agent_preparation import _AgentSession
from .agent_runtime import AgentGraphRuntime,_UNSET,_json_copy
from .execution_preflight import ExecutionPreflight,ExecutionError,revision
from .knowledge_contracts import CorpusPolicy
from .knowledge_snapshot import canonical_json,safe_relative,allowed_parts
from .preparation_primitives import PreparationPrimitives,PreparationError,_text,_strings,_json_bytes
from .task_effects import TaskEffectSync,_locked
from .workflow_runtime import Graph,Node,NodeResult,WaitState


@dataclass
class _ExecutionSession(_AgentSession):
    binding: dict = field(default_factory=dict)
    checkpoint: Any = None
    completed: list[str] = field(default_factory=list)
    worker_ref: str = ""
    claim_ref: str | None = None
    lease_seconds: int = 900
    effect_phase: str = "starting"
    run_id: str = ""


def _graph():
    transitions={"success":"work_unit","handoff":"succeeded","needs_input":"work_unit",
                 "blocked":"work_unit","failure":"failed"}
    return Graph("agent-work-units-v1",1,"work_unit",{
        "work_unit":Node("work_unit","work-unit-request/v1","work-unit-result/v1",tuple(transitions),transitions)})


class AgentExecution(TaskEffectSync,PreparationPrimitives):
    """Одна in-memory сессия; physical edits выполняет агент, не facade."""

    def __init__(self,project_root: Path,*,policy: CorpusPolicy | None=None,max_results: int=200):
        if type(max_results) is not int or max_results < 1:
            raise ExecutionError("contract_violation","max_results должен быть положительным целым")
        self.preflight=ExecutionPreflight(project_root,policy=policy)
        self.repository=self.preflight.repository
        self.service=self.preflight.service
        self.runtime=AgentGraphRuntime()
        self.max_results=max_results
        self._sessions={}
        self._lock=threading.RLock()

    def source_revision(self):
        return self.preflight.source_revision()

    @_locked
    def start(self,task_id: str,*,expected_task_version: int,worker_ref: str,lease_seconds: int=900):
        _text(worker_ref,"worker_ref")
        if type(lease_seconds) is not int or not 30 <= lease_seconds <= 86400:
            raise ExecutionError("contract_violation","lease_seconds должен быть 30..86400")
        checked=self.preflight.check(task_id,expected_task_version=expected_task_version)
        snapshot=self.preflight.source_snapshot()
        if revision(snapshot) != checked["source_revision"]:
            raise ExecutionError("source_drift","Source изменился после preflight")
        run=self.runtime.create_run(_graph(),{"preflight":checked["source_revision"]},task_ref=task_id,
            task_definition_version=checked["task"]["definition_version"],phase="execution",max_results=self.max_results)
        session=_ExecutionSession(checked["task"],{},checked["source_revision"],"EXEC-"+uuid.uuid4().hex,
            binding=checked["binding"],checkpoint=snapshot,worker_ref=worker_ref,lease_seconds=lease_seconds,run_id=run.run_id)
        self._sessions[run.run_id]=session
        artifact=self._artifact(session,"execution_preflight","v1",checked)
        self._effects(session,[lambda:self._publish(session,artifact),lambda:self._claim(session),
            lambda:self._call(session,"link_workflow_run",run_ref=run.run_id,relation="active")],phase="starting")
        try:
            self.synchronize(run.run_id)
        except Exception as exc:
            if isinstance(exc,PreparationError):
                exc.details["run_id"]=run.run_id
                raise
            raise ExecutionError("sync_failed","Execution start pending",run_id=run.run_id) from exc
        return self.runtime.inspect_run(run.run_id)

    @staticmethod
    def _effects(session,actions,*,phase="working"):
        session.actions,session.cursor,session.pending=actions,0,True
        session.effect_phase=phase

    @staticmethod
    def _artifact(session,role,version,value):
        content=_json_bytes(value)
        if len(content)>2*1024*1024:
            raise ExecutionError("contract_violation","Artifact превышает 2 MiB")
        return {"ref":session.ref,"role":role,"version":version,"contract":
            "execution-preflight/v1" if role=="execution_preflight" else "work-unit-result/v1",
            "sha256":hashlib.sha256(content).hexdigest(),"media_type":"application/json","value":value}

    def _claim(self,session):
        self._call(session,"claim_task",worker_ref=session.worker_ref,lease_seconds=session.lease_seconds)
        session.claim_ref=session.task["active_claim"]["ref"]

    def _lease(self,session,task):
        claim=task["active_claim"]
        if (not claim or claim["ref"]!=session.claim_ref or claim["worker_ref"]!=session.worker_ref
                or claim["execution_package_ref"]!=task["artifacts"]["execution_package"]["ref"]):
            raise ExecutionError("claim_conflict","Execution claim чужой/отсутствует")
        now=self.service.clock()
        if now.tzinfo is None:
            now=now.replace(tzinfo=timezone.utc)
        if datetime.fromisoformat(claim["lease_until"]) <= now.astimezone(timezone.utc):
            raise ExecutionError("claim_expired","Execution lease истёк")

    def _integrity(self,session,task):
        if task["definition_version"]!=session.task["definition_version"]:
            raise ExecutionError("stale_execution","Task definition изменилась")
        if self.preflight.bindings(task)!=session.binding:
            raise ExecutionError("stale_package","Preparation bindings изменились")

    def _checkpoint(self,session):
        current=self.preflight.source_snapshot()
        if current.digest!=session.checkpoint.digest:
            raise ExecutionError("source_drift","Source изменился вне принятого work-unit result")
        return current

    def _guard(self,run_id,expected_revision,expected_task_version,*,checkpoint=True):
        session=self._session(run_id)
        if session.pending:
            raise ExecutionError("sync_pending","Сначала завершите принятые effects")
        # Submit проверяет физические изменения как delta результата, не как
        # внешнее изменение прежнего checkpoint до разбора envelope.
        TaskEffectSync._assert_version(self,session)
        self._task_guard(session.task,expected_task_version)
        run=self.runtime.inspect_run(run_id)
        if type(expected_revision) is not int or run.revision!=expected_revision:
            raise ExecutionError("run_revision_conflict","Нужна текущая process revision")
        task=session.task
        self._integrity(session,task)
        if task["status"]!="active" or task["active_run_ref"]!=run_id:
            raise ExecutionError("invalid_state","Нужна active task с owned run")
        self._lease(session,task)
        if any(b["blocking"] and b["status"]=="open" for b in task["blockers"]):
            raise ExecutionError("invalid_state","Открытый blocker запрещает work")
        if checkpoint:
            self._checkpoint(session)
        return session,run

    def _assert_version(self,session):
        super()._assert_version(session)
        # Во время recovered эффекта актуальная карточка ещё не adopted.
        task=session.recovered["task"] if session.recovered else session.task
        if session.effect_phase=="cleanup":
            if task["active_run_ref"] not in {None,session.run_id} or (task["active_claim"] and task["active_claim"]["ref"]!=session.claim_ref):
                raise ExecutionError("claim_conflict","Cleanup не может закрыть чужой claim/run")
            return
        self._integrity(session,task)
        self._checkpoint(session)
        if task["active_run_ref"] not in {None,session.run_id}:
            raise ExecutionError("claim_conflict","Pipeline run изменён")
        if task["active_claim"] and task["active_claim"]["ref"]!=session.claim_ref:
            # recovered claim ещё не прошёл closure adoption.
            if not (session.recovered and session.recovered["method"]=="claim_task"):
                raise ExecutionError("claim_conflict","Pipeline claim изменён")
        if session.effect_phase in {"working","renewing","handoff"}:
            closing_recovered=(session.effect_phase=="handoff" and session.recovered
                and session.recovered["method"]=="link_workflow_run"
                and session.recovered["kwargs"]=={"run_ref":session.run_id,"relation":"finished"}
                and task["active_run_ref"] is None)
            if task["status"]!="active" or (task["active_run_ref"]!=session.run_id and not closing_recovered):
                raise ExecutionError("invalid_state","Work effects требуют active owned run")
            self._lease(session,task)
        elif session.effect_phase in {"starting","resuming"} and task["status"]=="active" and not session.recovered:
            self._lease(session,task)

    @_locked
    def inspect(self,run_id):
        result=super().inspect(run_id)
        session=self._session(run_id)
        result.update(unknown_effect=copy.deepcopy(session.uncertain),completed_units=list(session.completed),
            checkpoint_revision=revision(session.checkpoint),claim_ref=session.claim_ref)
        return result

    def _available_units(self,session):
        return [copy.deepcopy(u) for u in session.binding["work_units"] if u["id"] not in session.completed
                and set(u.get("depends_on",[])).issubset(session.completed)]

    @_locked
    def request(self,run_id):
        session=self._session(run_id)
        run=self.runtime.inspect_run(run_id)
        actions=self.runtime.available_actions(run_id)
        if session.pending:
            actions["actions"]=["reconcile_effect"] if session.uncertain else ["synchronize","reconcile","cancel"]
        elif "submit_result" in actions["actions"]:
            self._guard(run_id,run.revision,session.task["version"])
            actions["actions"]=["submit","renew_claim","cancel"]
        return {"contract":"work-unit-request/v1","actions":actions,"task":self.service.get_task(session.task["id"]),
            "available_units":self._available_units(session),"completed_units":list(session.completed),
            "source_before":revision(session.checkpoint),"binding":copy.deepcopy(session.binding),
            "resumed_wait":copy.deepcopy(run.resumed_wait),"limitations":["code-only checkpoint; agent edits/semantic validation вне facade"]}

    @_locked
    def available_actions(self,run_id):
        return self.request(run_id)["actions"]

    @_locked
    def submit(self,run_id,envelope: Mapping,*,expected_revision: int,expected_task_version: int):
        session,run=self._guard(run_id,expected_revision,expected_task_version,checkpoint=False)
        if "submit_result" not in self.runtime.available_actions(run_id)["actions"]:
            raise ExecutionError("invalid_state","Submit недоступен")
        if not isinstance(envelope,Mapping):
            raise ExecutionError("contract_violation","Envelope должен быть объектом")
        raw=_json_copy(dict(envelope))
        if len(_json_bytes(raw))>65536 or set(raw)-{"outcome","payload","question","reason"}:
            raise ExecutionError("contract_violation","Envelope shape/64 KiB limit неверны")
        outcome=raw.get("outcome")
        if not isinstance(outcome,str) or outcome not in _graph().nodes["work_unit"].outcomes:
            raise ExecutionError("unknown_outcome","Outcome не объявлен")
        if outcome=="success":
            if set(raw)!={"outcome","payload"}:
                raise ExecutionError("contract_violation","Success envelope требует только outcome/payload")
            payload=raw.get("payload")
            if not isinstance(payload,dict) or set(payload)!={"unit_id","summary","source_before","source_after","changed_files","evidence_refs","validation","unresolved"}:
                raise ExecutionError("contract_violation","Неверный success payload")
            unit=next((u for u in self._available_units(session) if u["id"]==payload["unit_id"]),None)
            if unit is None:
                raise ExecutionError("unit_not_available","Unknown/completed/dependency-blocked unit")
            _text(payload["summary"],"summary")
            _strings(payload["evidence_refs"],"evidence_refs",nonempty=True)
            changed=_strings(payload["changed_files"],"changed_files")
            for path in changed:
                safe_relative(path)
                if not allowed_parts(Path(path)) or not any(path==p or path.startswith(p+"/") for p in unit["files_objects"]):
                    raise ExecutionError("scope_violation","Change вне declared work-unit scope")
            validation=payload["validation"]
            if (not isinstance(validation,dict) or set(validation)!={"status","checks_run","failed"}
                    or validation["status"]!="passed" or validation["failed"]!=[] or payload["unresolved"]!=[]):
                raise ExecutionError("contract_violation","Success требует passed validation и пустые failed/unresolved")
            _strings(validation["checks_run"],"checks_run",nonempty=True)
            after=self.preflight.source_snapshot()
            beforefiles={f.path:(f.sha256,f.size) for f in session.checkpoint.files}
            afterfiles={f.path:(f.sha256,f.size) for f in after.files}
            delta={p for p in beforefiles.keys()|afterfiles.keys() if beforefiles.get(p)!=afterfiles.get(p)}
            if (payload["source_before"]!=revision(session.checkpoint) or payload["source_after"]!=revision(after)
                    or len(changed)!=len(set(changed)) or set(changed)!=delta):
                raise ExecutionError("source_drift","Before/after revision или observed code delta неверны")
            value={"contract":"work-unit-result/v1","task_ref":session.task["id"],"definition_version":session.task["definition_version"],
                "package":session.binding["package"],"result":payload,"completed_units":session.completed+[unit["id"]]}
            artifact=self._artifact(session,"implementation","v"+str(run.revision),value)
            result=NodeResult("work_unit","success",artifacts={"implementation":artifact},data={"unit_id":unit["id"]})
        else:
            self._checkpoint(session)
            if outcome=="handoff":
                if raw!={"outcome":"handoff"} or len(session.completed)!=len(session.binding["work_units"]):
                    raise ExecutionError("unit_not_available","Handoff только после всех work units")
                result=NodeResult("work_unit","handoff",data={"completed_units":list(session.completed),"next":"execution-gates"})
            else:
                field="question" if outcome=="needs_input" else "reason"
                if set(raw)!={"outcome",field}:
                    raise ExecutionError("contract_violation","Stop envelope требует только outcome и reason/question")
                reason=_text(raw.get(field),field)
                wait=None if outcome=="failure" else WaitState("WAIT-"+uuid.uuid4().hex,"work_unit",
                    "user_input" if outcome=="needs_input" else "blocker",question=reason if outcome=="needs_input" else None,
                    reason=reason if outcome=="blocked" else None)
                result=NodeResult("work_unit",outcome,data={"reason":reason},wait=wait)
        accepted=self.runtime.submit_result(run_id,result,expected_revision=expected_revision,
            task_definition_version=session.task["definition_version"])
        if outcome=="success":
            session.checkpoint=after
            session.completed.append(unit["id"])
            def publish():
                self._publish(session,artifact)
            def attach():
                record=session.records["implementation"]
                self._call(session,"attach_artifact",role="implementation",ref=f"{record.ref}:implementation:{record.version}",
                    metadata={"status":"implemented","repository":record.to_dict(),"completed_units":list(session.completed),
                              "source_revision":revision(session.checkpoint)})
            actions=[publish,attach]
        elif outcome=="handoff":
            actions=[lambda:self._call(session,"link_workflow_run",run_ref=run_id,relation="finished")]
        else:
            if outcome=="needs_input":
                actions=[lambda:self._call(session,"transition_status",to="awaiting_input",reason=reason)]
            else:
                def block():
                    self._call(session,"add_blocker",blocker_type="execution",summary=reason)
                    session.blocker=session.task["blockers"][-1]["id"]
                actions=[block]
            actions += [lambda:self._call(session,"link_workflow_run",run_ref=run_id,relation="finished"),
                lambda:self._call(session,"release_claim",claim_ref=session.claim_ref,
                    target_status=session.task["status"],reason="Execution pause/stop")]
        self._effects(session,actions,phase="working" if outcome=="success" else "handoff" if outcome=="handoff" else "pausing")
        self.synchronize(run_id)
        return accepted

    @_locked
    def resume_wait(self,run_id,*,expected_revision,expected_task_version,wait_id,node_id,answer=_UNSET,resolution=None):
        session=self._session(run_id); self._before_step(session)
        self._task_guard(session.task,expected_task_version)
        self._integrity(session,session.task); self._checkpoint(session)
        run=self.runtime.inspect_run(run_id)
        if run.wait is None or session.task["status"]!=("awaiting_input" if run.wait.kind=="user_input" else "blocked") or session.task["active_claim"] or session.task["active_run_ref"]:
            raise ExecutionError("invalid_state","Нужна owned pause без claim/run")
        accepted=self.runtime.resume_wait(run_id,expected_revision=expected_revision,task_definition_version=session.task["definition_version"],
            wait_id=wait_id,node_id=node_id,answer=answer,resolution=resolution)
        if run.wait.kind=="user_input":
            actions=[lambda:self._call(session,"record_user_decision",decision_type="clarification",value=_json_bytes(accepted.resumed_wait["answer"]).decode())]
        else:
            actions=[lambda:self._call(session,"resolve_blocker",blocker_ref=session.blocker,resolution=resolution)]
        actions += [lambda:self._call(session,"transition_status",to="ready",reason="Execution resume checkpoint"),
            lambda:self._claim(session),lambda:self._call(session,"link_workflow_run",run_ref=run_id,relation="active")]
        self._effects(session,actions,phase="resuming"); self.synchronize(run_id)
        return accepted

    @_locked
    def renew_claim(self,run_id,*,expected_revision,expected_task_version,lease_seconds=900):
        session,_=self._guard(run_id,expected_revision,expected_task_version)
        if type(lease_seconds) is not int or not 30<=lease_seconds<=86400:
            raise ExecutionError("contract_violation","lease_seconds должен быть 30..86400")
        self._effects(session,[lambda:self._call(session,"renew_claim",claim_ref=session.claim_ref,lease_seconds=lease_seconds)],phase="renewing")
        self.synchronize(run_id)

    @_locked
    def reconcile(self,run_id,*,expected_version):
        session=self._session(run_id)
        if session.uncertain or session.recovered:
            raise ExecutionError("effect_outcome_unknown","Сначала reconcile_effect/synchronize")
        task=self.service.get_task(session.task["id"]); self._task_guard(task,expected_version)
        self._integrity(session,task); self._checkpoint(session)
        if task["active_run_ref"] not in {None,run_id} or (task["active_claim"] and task["active_claim"]["ref"]!=session.claim_ref):
            raise ExecutionError("claim_conflict","Нельзя adopt чужой process/claim")
        if task["status"] not in {"ready","active","blocked","awaiting_input"}:
            raise ExecutionError("invalid_state","Task state несовместимо")
        session.task=task

    def _expected_event(self,intent):
        method,args,before=intent["method"],intent["kwargs"],intent["before"]
        if method=="claim_task":
            actual=self.service.get_task(before["id"])
            claim=actual["active_claim"]
            if not claim or claim["worker_ref"]!=args["worker_ref"] or claim["execution_package_ref"]!=before["artifacts"]["execution_package"]["ref"]:
                raise ExecutionError("effect_evidence_mismatch","Нет claimed successor")
            return "task_claimed",{"from":"ready","to":"active","claim_ref":claim["ref"],"worker_ref":args["worker_ref"]}
        if method=="release_claim":
            return "claim_released",{"claim_ref":args["claim_ref"],"to":args["target_status"],"reason":args["reason"]}
        if method=="renew_claim":
            actual=self.service.get_task(before["id"]); claim=actual["active_claim"]
            if not claim or claim["ref"]!=args["claim_ref"] or {k:v for k,v in claim.items() if k!="lease_until"}!={k:v for k,v in before["active_claim"].items() if k!="lease_until"}:
                raise ExecutionError("effect_evidence_mismatch","Нет renewal successor")
            return "claim_renewed",{"claim_ref":args["claim_ref"],"lease_until":claim["lease_until"]}
        return super()._expected_event(intent)

    @_locked
    def cancel(self,run_id,*,expected_revision,expected_task_version,reason):
        session=self._session(run_id)
        if session.uncertain or session.recovered:
            raise ExecutionError("effect_outcome_unknown","Сначала сверка/adoption неизвестного эффекта")
        task=self.service.get_task(session.task["id"]); self._task_guard(task,expected_task_version)
        if task["active_run_ref"] not in {None,run_id} or (task["active_claim"] and task["active_claim"]["ref"]!=session.claim_ref):
            raise ExecutionError("claim_conflict","Нельзя отменять чужой claim/run")
        run=self.runtime.inspect_run(run_id)
        accepted=self.runtime.cancel(run_id,reason,expected_revision=expected_revision,task_definition_version=run.task_definition_version)
        session.task=task
        # Cleanup не подтверждает свежесть/успех; не требует lease/source/package.
        actions=[]
        if task["active_run_ref"]==run_id:
            actions.append(lambda:self._call(session,"link_workflow_run",run_ref=run_id,relation="finished"))
        if task["active_claim"]:
            actions.append(lambda:self._call(session,"release_claim",claim_ref=session.claim_ref,
                target_status="preparing" if task["status"]=="active" else task["status"],reason=reason))
        self._effects(session,actions,phase="cleanup")
        self.synchronize(run_id)
        return accepted

    @_locked
    def synchronize(self,run_id):
        return super().synchronize(run_id)

    @staticmethod
    def _task_guard(task,expected):
        return ExecutionPreflight.task_guard(task,expected)


__all__=["AgentExecution"]
