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

from orchestrator_task_manager import TaskError, TaskManagerService

from .agent_preparation import _AgentSession
from .agent_runtime import AgentGraphRuntime,_UNSET,_json_copy
from .execution_preflight import ExecutionPreflight,ExecutionError,revision
from .execution_gates import (candidate_fingerprint, execution_gates_graph,
                               validate_gate_envelope)
from .knowledge_contracts import CorpusPolicy
from .knowledge_refresh_node import KnowledgeRefreshNode, KnowledgeRefreshPolicy, KnowledgeRefreshRequest
from .knowledge_service import ProjectKnowledgeService
from .knowledge_snapshot import canonical_json,safe_relative,allowed_parts
from .preparation_primitives import PreparationPrimitives,PreparationError,_text,_strings,_json_bytes
from .task_effects import TaskEffectSync,_locked
from .runtime_contracts import Graph,Node,NodeResult,WaitState


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
    knowledge_gate: dict | None = None


@dataclass
class _GateSession:
    task: dict
    execution_run_id: str
    gate_run_id: str
    candidate_revision: str
    source_revision: str
    package_ref: str
    worker_ref: str
    knowledge_required: bool = False
    ref: str = ""
    records: dict[str, dict] = field(default_factory=dict)
    knowledge: dict | None = None


def _graph():
    transitions={"success":"work_unit","handoff":"succeeded","needs_input":"work_unit",
                 "blocked":"work_unit","failure":"failed"}
    return Graph("agent-work-units-v1",1,"work_unit",{
        "work_unit":Node("work_unit","work-unit-request/v1","work-unit-result/v1",tuple(transitions),transitions)})


class AgentExecution(TaskEffectSync,PreparationPrimitives):
    """Одна in-memory сессия; physical edits выполняет агент, не facade."""

    def __init__(self,project_root: Path,*,policy: CorpusPolicy | None=None,max_results: int=200,
                 knowledge_service: ProjectKnowledgeService | None = None, workflow_source=None):
        if type(max_results) is not int or max_results < 1:
            raise ExecutionError("contract_violation","max_results должен быть положительным целым")
        self.preflight=ExecutionPreflight(project_root,policy=policy,workflow_source=workflow_source)
        self.repository=self.preflight.repository
        self.service=self.preflight.service
        self.knowledge_service=knowledge_service
        self.runtime=AgentGraphRuntime()
        self.max_results=max_results
        self._sessions={}
        self._gate_sessions={}
        self._lock=threading.RLock()
        self._components={}

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
            checkpoint_revision=revision(session.checkpoint),claim_ref=session.claim_ref,
            knowledge_gate=copy.deepcopy(session.knowledge_gate))
        return result

    @_locked
    def precommit_gate(self,run_id,*,expected_revision,expected_task_version,
                       request: KnowledgeRefreshRequest | Mapping[str, Any] | None = None,
                       decision: Mapping[str, Any] | None = None):
        """Run the code-only knowledge gate before the agent's physical commit.

        AgentExecution owns the policy/moment of the gate, while the injected
        ProjectKnowledgeService owns Graphify refresh and immutable publication.
        This method never runs Git and reports an explicit denial whenever the
        graph cannot be proven fresh for the current candidate.
        """
        session,run=self._guard(run_id,expected_revision,expected_task_version)
        if self.knowledge_service is None:
            raise ExecutionError("knowledge_unavailable",
                "Для pre-commit gate нужен явно подключённый ProjectKnowledgeService")
        if len(session.completed)!=len(session.binding["work_units"]):
            raise ExecutionError("knowledge_gate_required",
                "Knowledge gate доступен только после завершения всех work units")
        node = KnowledgeRefreshNode(self.knowledge_service)
        node_result = node.execute(request or KnowledgeRefreshRequest(), decision=decision)
        value = node_result.data["result"]
        if node_result.wait is not None:
            value["wait"] = node_result.wait.to_dict()
        if node_result.error is not None:
            value["error"] = copy.deepcopy(node_result.error)
        value={"contract":"knowledge-precommit-gate/v1",**value,"run_id":run_id,
            "limitations":["Git commit выполняет вызывающий агент после commit_allowed=true",
                "degraded разрешён только для провалидированного full-rebuild-fallback"]}
        session.knowledge_gate=value
        return copy.deepcopy(value)

    @_locked
    def start_gates(self,run_id,*,expected_revision,expected_task_version,
                    knowledge_required=False):
        """Start the explicit post-work-unit gate graph.

        The implementation agent supplies review/testing/documentation/final
        results. This method only creates process state and binds it to the
        current task/claim/package.
        """
        session=self._session(run_id)
        if session.pending:
            raise ExecutionError("sync_pending","Сначала завершите принятые effects")
        execution=self.runtime.inspect_run(run_id)
        if execution.state!="succeeded" or len(session.completed)!=len(session.binding["work_units"]):
            raise ExecutionError("invalid_state","Gates доступны только после handoff всех work units")
        if type(knowledge_required) is not bool:
            raise ExecutionError("contract_violation","knowledge_required должен быть bool")
        actual=self.service.get_task(session.task["id"])
        self._task_guard(actual,expected_task_version)
        self._integrity(session,actual)
        if actual["status"]!="active" or actual["active_claim"] is None or actual["active_run_ref"] is not None:
            raise ExecutionError("invalid_state","Нужна active task с собственным claim без active run")
        if actual["active_claim"]["ref"]!=session.claim_ref:
            raise ExecutionError("claim_conflict","Execution claim принадлежит другой сессии")
        source=self.source_revision()
        if source!=revision(session.checkpoint):
            raise ExecutionError("source_drift","Source изменился перед gates")
        package_ref=actual["artifacts"]["execution_package"]["ref"]
        candidate=candidate_fingerprint(task_id=actual["id"],definition_version=actual["definition_version"],
                                        package_ref=package_ref,source_revision=source)
        gate=self.runtime.create_run(execution_gates_graph(),
            {"candidate_revision":candidate,"source_revision":source,"package_ref":package_ref},
            task_ref=actual["id"],task_definition_version=actual["definition_version"],phase="execution",
            max_results=10)
        gate_session=_GateSession(actual,run_id,gate.run_id,candidate,source,package_ref,session.worker_ref,
                                  knowledge_required,ref="GATE-"+uuid.uuid4().hex)
        self._gate_sessions[gate.run_id]=gate_session
        try:
            gate_session.task=self.service.link_workflow_run(actual["id"],actual["version"],
                                                             run_ref=gate.run_id,relation="active")
        except TaskError as exc:
            self._gate_sessions.pop(gate.run_id,None)
            raise ExecutionError(exc.code,str(exc),**exc.details) from exc
        return self.gate_inspect(gate.run_id)

    @_locked
    def gate_inspect(self,gate_run_id):
        gate=self._gate_session(gate_run_id)
        run=self.runtime.inspect_run(gate_run_id)
        return {"run":run.to_dict(),"task":self.service.get_task(gate.task["id"]),
                "candidate_revision":gate.candidate_revision,"source_revision":gate.source_revision,
                "knowledge_required":gate.knowledge_required,
                "artifacts":copy.deepcopy(gate.records),"knowledge":copy.deepcopy(gate.knowledge)}

    @_locked
    def gate_request(self,gate_run_id):
        gate=self._gate_session(gate_run_id)
        run=self.runtime.inspect_run(gate_run_id)
        actions=self.runtime.available_actions(gate_run_id)
        actions["actions"]=["submit_gate" if item=="submit_result" else item for item in actions["actions"]]
        if (run.current_node=="knowledge_refresh" and run.state in {"created","running","waiting_input"}
                and actions["remaining_results"] > 0):
            actions["actions"].append("refresh_knowledge")
        return {"contract":actions["node"]["input_contract"] if actions["node"] else None,
                "actions":actions,"task":self.service.get_task(gate.task["id"]),
                "candidate_revision":gate.candidate_revision,"source_revision":gate.source_revision,
                "previous":copy.deepcopy(run.results),"artifacts":copy.deepcopy(gate.records),
                "knowledge":copy.deepcopy(gate.knowledge)}

    def _gate_session(self,gate_run_id):
        gate=self._gate_sessions.get(gate_run_id)
        if gate is None:
            raise ExecutionError("run_not_found","Gate run не найден",run_id=gate_run_id)
        return gate

    def _gate_guard(self,gate_run_id,expected_revision,expected_task_version):
        gate=self._gate_session(gate_run_id)
        run=self.runtime.inspect_run(gate_run_id)
        if type(expected_revision) is not int or run.revision!=expected_revision:
            raise ExecutionError("run_revision_conflict","Нужна текущая gate process revision")
        task=self.service.get_task(gate.task["id"])
        self._task_guard(task,expected_task_version)
        if task["status"]!="active" or task["active_run_ref"]!=gate_run_id or not task["active_claim"]:
            raise ExecutionError("invalid_state","Task Manager не связан с gate run")
        original=self._session(gate.execution_run_id)
        self._integrity(original,task)
        self._lease(original,task)
        if any(b["blocking"] and b["status"]=="open" for b in task["blockers"]):
            raise ExecutionError("invalid_state","Открытый blocker запрещает gate execution")
        if task["active_claim"]["ref"]!=original.claim_ref:
            raise ExecutionError("claim_conflict","Gate claim принадлежит другой сессии")
        if self.source_revision()!=gate.source_revision:
            raise ExecutionError("source_drift","Candidate source revision устарела")
        return gate,run,task

    @_locked
    def start_component(self,gate_run_id,*,roles,executors,inputs,expected_revision,
                        expected_task_version,fallbacks=None):
        gate,run,task=self._gate_guard(gate_run_id,expected_revision,expected_task_version)
        if run.current_node not in {"code_review","testing","documentation","final_validation"}:
            raise ExecutionError("invalid_state","Knowledge gate остаётся отдельным guarded action")
        if "submit_result" not in self.runtime.available_actions(gate_run_id)["actions"]:
            raise ExecutionError("invalid_state","Компонент сейчас недоступен")
        binding=self._session(gate.execution_run_id).binding.get("workflow_binding")
        if binding is None:
            raise ExecutionError("workflow_required","Нужен workflow binding в package")
        if any(c.owner==gate_run_id and c.role.role==run.current_node
               and c.request["actions"]["revision"]==run.revision for c in self._components.values()):
            raise ExecutionError("component_exists","Для этапа уже создан компонент; продолжите или сверьте его")
        from .workflow_roles import start_role
        def guard():
            with self._lock:
                self._gate_guard(gate_run_id,expected_revision,expected_task_version)
        component=start_role(self.repository,binding,roles,run.current_node,"execution",executors,
                             inputs,guard,fallbacks,self.gate_request(gate_run_id),gate_run_id)
        self._components[id(component)]=component
        return component

    @_locked
    def submit_component(self,gate_run_id,component,*,expected_revision,expected_task_version):
        gate,run,task=self._gate_guard(gate_run_id,expected_revision,expected_task_version)
        binding=self._session(gate.execution_run_id).binding.get("workflow_binding")
        from .workflow_roles import role_envelope
        envelope=role_envelope(component,self._components,gate_run_id,run.current_node,"execution",binding)
        return self.submit_gate(gate_run_id,envelope,expected_revision=expected_revision,
                                expected_task_version=expected_task_version)

    def _publish_gate(self,gate,node_id,outcome,payload,*,role=None,version="v1"):
        role=role or node_id
        value={"contract":f"{node_id.replace('_','-')}-evidence/v1","task_ref":gate.task["id"],
               "candidate_revision":gate.candidate_revision,"source_revision":gate.source_revision,
               "outcome":outcome,"payload":copy.deepcopy(payload)}
        record=self.repository.put_json(gate.ref,role,version,value,contract=value["contract"])
        evidence={"ref":record.ref,"role":record.role,"version":record.version,"contract":record.contract,
                  "sha256":record.sha256,"value":value}
        gate.records[node_id]={**record.to_dict(),"evidence_ref":f"{record.ref}:{record.role}:{record.version}",
                              "outcome":outcome}
        return record,evidence,value

    def _attach_gate(self,gate,task,role,record,outcome):
        ref=f"{record.ref}:{record.role}:{record.version}"
        metadata={"status":outcome,"candidate_revision":gate.candidate_revision,
                  "source_revision":gate.source_revision,"repository":record.to_dict()}
        try:
            self.service.attach_artifact(task["id"],task["version"],role=role,ref=ref,metadata=metadata)
            return self.service.get_task(task["id"])
        except TaskError as exc:
            raise ExecutionError(exc.code,str(exc),**exc.details) from exc

    @_locked
    def submit_gate(self,gate_run_id,envelope,*,expected_revision,expected_task_version):
        gate,run,task=self._gate_guard(gate_run_id,expected_revision,expected_task_version)
        node=run.current_node
        if node in {None,"knowledge_refresh"}:
            raise ExecutionError("invalid_state","Для knowledge_refresh используйте refresh_knowledge")
        checked=validate_gate_envelope(node,envelope,candidate=gate.candidate_revision,source=gate.source_revision,
                                       acceptance_criteria=task["acceptance_criteria"])
        outcome,payload=checked["outcome"],checked["payload"]
        if node=="final_validation":
            if gate.knowledge is None:
                raise ExecutionError("knowledge_gate_required","Final validation требует knowledge evidence")
            if payload.get("knowledge_status")!=gate.knowledge.get("status"):
                raise ExecutionError("stale_evidence","Final validation скрывает другой knowledge status")
            if payload.get("knowledge_required") is not gate.knowledge_required:
                raise ExecutionError("stale_evidence","Final validation скрывает knowledge policy")
            docs=run.results.get("documentation",{}).get("data",{}).get("result",{})
            docs_payload=docs.get("payload",{}) if isinstance(docs,Mapping) else {}
            if docs_payload.get("source_adjacent_changed") is True:
                raise ExecutionError("not_ready","Source-adjacent docs требуют delta review до readiness")
        role="readiness" if node=="final_validation" else node
        record,evidence,value=self._publish_gate(gate,node,outcome,payload,role=role)
        if node!="final_validation":
            task=self._attach_gate(gate,task,role,record,outcome) or self.service.get_task(task["id"])
        package_record=None
        package_payload=None
        if node=="final_validation" and outcome=="ready":
            task=self._attach_gate(gate,task,"readiness",record,outcome) or self.service.get_task(task["id"])
            package_payload=dict(payload["acceptance_package"])
            package_payload.update({"contract":"acceptance-package/v1","task_ref":task["id"],
                                    "candidate_revision":gate.candidate_revision,
                                    "source_revision":gate.source_revision})
            package_record=self.repository.put_json(gate.ref,"acceptance_package","v1",package_payload,
                                                    contract="acceptance-package/v1")
            task=self._attach_gate(gate,task,"acceptance_package",package_record,outcome) or self.service.get_task(task["id"])
        result=NodeResult(node,outcome,artifacts={role:evidence},data={"result":value})
        accepted=self.runtime.submit_result(gate_run_id,result,expected_revision=expected_revision,
                                            task_definition_version=task["definition_version"])
        gate.task=task
        if node=="final_validation" and outcome=="ready":
            try:
                task=self.service.link_workflow_run(task["id"],task["version"],run_ref=gate_run_id,relation="finished")
                task=self.service.mark_awaiting_acceptance(task["id"],task["version"])
            except TaskError as exc:
                raise ExecutionError(exc.code,str(exc),**exc.details) from exc
            gate.task=task
        return accepted

    @_locked
    def refresh_knowledge(self,gate_run_id,*,expected_revision,expected_task_version,
                          request=None,decision=None):
        gate,run,task=self._gate_guard(gate_run_id,expected_revision,expected_task_version)
        if run.current_node!="knowledge_refresh" or run.state not in {"created","running","waiting_input"}:
            raise ExecutionError("invalid_state","Knowledge gate сейчас недоступен")
        if self.knowledge_service is None:
            raise ExecutionError("knowledge_unavailable","Для knowledge gate нужен ProjectKnowledgeService")
        if self.runtime.available_actions(gate_run_id)["remaining_results"] < 1:
            raise ExecutionError("result_limit_exceeded","Исчерпан budget knowledge gate")
        node=KnowledgeRefreshNode(self.knowledge_service)
        pending_request=gate.knowledge.get("request") if gate.knowledge and run.state=="waiting_input" else None
        request=node.request_from(request if request is not None else pending_request or KnowledgeRefreshRequest())
        if pending_request is not None and request.to_dict()!=pending_request:
            raise ExecutionError("stale_request","Нельзя менять request активного подтверждения")
        if decision is not None:
            if not isinstance(decision,Mapping):
                raise ExecutionError("contract_violation","Decision должен быть объектом")
            decision=_json_copy(dict(decision))
        if run.state=="waiting_input":
            if run.wait is None or decision is None:
                raise ExecutionError("wait_required","Передайте decision для продолжения knowledge gate")
            self.runtime.resume_wait(gate_run_id,expected_revision=expected_revision,
                                     task_definition_version=task["definition_version"],
                                     wait_id=run.wait.wait_id,node_id=run.wait.node_id,answer=decision)
            run=self.runtime.inspect_run(gate_run_id)
            expected_revision=run.revision
        node_result=node.execute(request,decision=decision)
        value=copy.deepcopy(node_result.data["result"])
        value.update({"candidate_revision":gate.candidate_revision,"source_revision":gate.source_revision,
                      "request":request.to_dict()})
        if node_result.wait is not None:
            value["wait"]=node_result.wait.to_dict()
        if node_result.error is not None:
            value["error"]=copy.deepcopy(node_result.error)
        status=value.get("status")
        record,evidence,stored=self._publish_gate(gate,"knowledge_refresh",node_result.outcome,value,
                                                role="knowledge_refresh",version=f"v{run.revision}")
        result=NodeResult("knowledge_refresh",node_result.outcome,artifacts={"knowledge_refresh":evidence},
                          data={"result":stored},wait=node_result.wait)
        accepted=self.runtime.submit_result(gate_run_id,result,expected_revision=expected_revision,
                                            task_definition_version=task["definition_version"])
        gate.knowledge=value
        gate.records["knowledge_refresh"]["status"]=status
        return accepted

    @_locked
    def release_gates(self,gate_run_id,*,expected_task_version,reason,target_status="preparing"):
        gate=self._gate_session(gate_run_id)
        task=self.service.get_task(gate.task["id"])
        self._task_guard(task,expected_task_version)
        if target_status not in {"preparing","ready"}:
            raise ExecutionError("contract_violation","Недопустимый target_status")
        run=self.runtime.inspect_run(gate_run_id)
        if run.state not in {"failed","blocked","cancelled"}:
            raise ExecutionError("invalid_state","Освободить можно только остановленный gate run")
        try:
            if task["active_run_ref"]==gate_run_id:
                task=self.service.link_workflow_run(task["id"],task["version"],run_ref=gate_run_id,relation="finished")
            task=self.service.release_claim(task["id"],task["version"],claim_ref=task["active_claim"]["ref"],
                                            target_status=target_status,reason=reason)
        except (TaskError,KeyError) as exc:
            if isinstance(exc,TaskError):
                raise ExecutionError(exc.code,str(exc),**exc.details) from exc
            raise ExecutionError("claim_conflict","Gate claim отсутствует") from exc
        gate.task=task
        return task

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
