from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator import CorpusPolicy, GraphifyProvider, KnowledgeError, ProjectKnowledgeService, ProviderCapabilities, ProviderIdentity
from orchestrator.knowledge_process import StdioMCP, bounded_run, provider_environment


class FakeProvider:
    identity=ProviderIdentity()
    capabilities=ProviderCapabilities()

    def __init__(self):
        self.calls=[]

    def index(self,corpus,output):
        self.calls.append((corpus,output))
        nodes=[]
        manifest={}
        for path in sorted(corpus.rglob("*")):
            if path.is_file():
                rel=path.relative_to(corpus).as_posix()
                nodes.append({"id":rel,"label":path.stem,"source_file":rel})
                manifest[rel]={"ast_hash":hashlib.md5(path.read_bytes(),usedforsecurity=False).hexdigest()}
        return json.dumps({"nodes":nodes,"edges":[]}).encode(),manifest

    def incremental_update(self,corpus,*,base_graph,base_manifest):
        self.calls.append(("incremental",corpus,base_manifest))
        # The real provider delegates merge/pruning to graphify update; this
        # fake keeps the service tests deterministic while exercising the same
        # validated output boundary.
        nodes=[]
        manifest={}
        for path in sorted(corpus.rglob("*")):
            if path.is_file() and "graphify-out" not in path.relative_to(corpus).parts:
                rel=path.relative_to(corpus).as_posix()
                nodes.append({"id":rel,"label":path.stem,"source_file":rel})
                manifest[rel]={"ast_hash":hashlib.md5(path.read_bytes(),usedforsecurity=False).hexdigest()}
        return json.dumps({"nodes":nodes,"edges":[]}).encode(),manifest

    def query(self,graph_path,cwd,**kwargs):
        self.calls.append((graph_path,cwd,kwargs))
        return "NODE entry [src=entry.py loc=L1 community=]\nEDGE entry --calls [EXTRACTED]--> helper\n"


class KnowledgeServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/"entry.py").write_text("def entry():\n    return 1\n",encoding="utf-8")
        self.provider=FakeProvider()
        self.service=ProjectKnowledgeService(self.root,self.provider)

    def test_missing_initial_refresh_real_artifacts_and_restart(self):
        self.assertEqual(self.service.status().state,"missing")
        self.assertEqual(self.service.query("entry").status,"degraded")
        result=self.service.refresh()
        self.assertEqual(result.status,"indexed",result.error)
        self.assertEqual(self.service.status().state,"fresh")
        restarted=ProjectKnowledgeService(self.root,FakeProvider())
        self.assertEqual(restarted.status().state,"fresh")
        query=restarted.query("entry")
        self.assertEqual(query.status,"ok")
        self.assertEqual(query.provenance,("EXTRACTED",))
        self.assertEqual(query.citations[0]["path"],"entry.py")
        self.assertEqual(query.citations[0]["validation"],"indexed-path-only")

    def test_dirty_untracked_rename_delete_stale_and_no_silent_refresh(self):
        initial=self.service.snapshot().digest
        self.service.refresh()
        (self.root/"entry.py").write_text("def changed(): return 2\n",encoding="utf-8")
        self.assertNotEqual(initial,self.service.snapshot().digest)
        count=len(self.provider.calls)
        result=self.service.query("entry")
        self.assertEqual(result.freshness,"stale")
        self.assertEqual(len(self.provider.calls),count)
        self.assertEqual(self.service.query("entry",allow_stale=True).status,"degraded")
        (self.root/"entry.py").rename(self.root/"renamed.py")
        (self.root/"untracked.tsx").write_text("export function Card(){return <div/>;}\n",encoding="utf-8")
        self.assertEqual(self.service.refresh().status,"indexed")
        indexed=self.service.status().indexed_snapshot
        self.assertEqual({f["path"] for f in indexed["files"]},{"renamed.py","untracked.tsx"})
        (self.root/"renamed.py").unlink()
        self.assertEqual(self.service.refresh().status,"indexed")
        self.assertEqual(self.service.status().state,"fresh")

    def test_incremental_refresh_tracks_changes_and_noop(self):
        self.assertEqual(self.service.refresh().mode, "full-rebuild")
        calls_before = len(self.provider.calls)
        self.assertEqual(self.service.refresh_incremental().status, "not_required")
        self.assertEqual(len(self.provider.calls), calls_before)
        (self.root/"entry.py").write_text("def changed(): return 2\n",encoding="utf-8")
        (self.root/"added.py").write_text("def added(): return 3\n",encoding="utf-8")
        result = self.service.refresh_incremental()
        self.assertEqual(result.status, "indexed", result.error)
        self.assertEqual(result.mode, "incremental")
        self.assertEqual(result.details["changed"], ["entry.py"])
        self.assertEqual(result.details["added"], ["added.py"])
        self.assertEqual(result.details["deleted"], [])
        self.assertEqual(self.service.status().state, "fresh")
        self.assertEqual(self.service._load()["mode"], "incremental")

    def test_incremental_failure_preserves_current_pointer(self):
        self.service.refresh()
        before = self.service.pointer.read_bytes()
        (self.root/"entry.py").write_text("changed=1\n",encoding="utf-8")
        with patch.object(self.provider, "incremental_update", side_effect=KnowledgeError("provider_timeout", "down")):
            result = self.service.refresh_incremental()
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.mode, "incremental")
        self.assertEqual(self.service.pointer.read_bytes(), before)
        self.assertEqual(self.service.status().state, "stale")

    def test_incremental_legacy_manifest_uses_explicit_full_fallback(self):
        self.service.refresh()
        legacy = dict(self.service._load())
        legacy.pop("manifest")
        with patch.object(self.service, "_load", return_value=legacy), patch.object(
            self.service, "refresh", return_value=type("Result", (), {"mode": "full-rebuild-fallback"})()
        ) as full:
            result = self.service.refresh_incremental()
        self.assertEqual(result.mode, "full-rebuild-fallback")
        full.assert_called_once_with(_mode="full-rebuild-fallback", _fallback_reason="manifest_missing")

    def test_incremental_strict_mode_surfaces_fallback_without_full_refresh(self):
        self.service.refresh()
        legacy = dict(self.service._load())
        legacy.pop("manifest")
        with patch.object(self.service, "_load", return_value=legacy), patch.object(self.service, "refresh") as full:
            result = self.service.refresh_incremental(allow_full_fallback=False)
        self.assertEqual(result.status, "fallback_required")
        self.assertEqual(result.mode, "incremental")
        self.assertEqual(result.details["reason"], "manifest_missing")
        full.assert_not_called()

    def test_precommit_gate_is_incremental_and_does_not_commit(self):
        self.service.refresh()
        before = self.service.pointer.read_bytes()
        result = self.service.precommit_refresh()
        self.assertEqual(result.status, "not_required")
        self.assertEqual(result.mode, "incremental")
        self.assertEqual(self.service.pointer.read_bytes(), before)

    def test_code_only_exclusions_and_policy_digest(self):
        for directory in ("obsolete",".venv",".tmp","node_modules","graphify-out","secrets"):
            path=self.root/directory
            path.mkdir()
            (path/"hidden.py").write_text("hidden=1")
        (self.root/"notes.md").write_text("Ignored")
        (self.root/"credentials.py").write_text("Ignored")
        (self.root/".secret.py").write_text("Ignored")
        self.assertEqual([f.path for f in self.service.snapshot().files],["entry.py"])
        subset=ProjectKnowledgeService(self.root,self.provider,policy=CorpusPolicy(include_roots=("entry.py",)))
        self.assertNotEqual(subset.snapshot().digest,self.service.snapshot().digest)
        self.service.refresh()
        self.assertEqual(subset.status().state,"stale")

    def test_snapshot_limits_and_invalid_paths(self):
        for policy in (CorpusPolicy(max_file_bytes=1),CorpusPolicy(max_total_bytes=1)):
            with self.assertRaises(KnowledgeError):
                ProjectKnowledgeService(self.root,self.provider,policy=policy).snapshot()
        (self.root/"two.py").write_text("x=1")
        with self.assertRaises(KnowledgeError):
            ProjectKnowledgeService(self.root,self.provider,policy=CorpusPolicy(max_files=1)).snapshot()
        for root in ("../other","C:/other","/other","obsolete",".tmp"):
            with self.assertRaises(KnowledgeError):
                ProjectKnowledgeService(self.root,self.provider,policy=CorpusPolicy(include_roots=(root,))).snapshot()
        for kwargs in ({"max_files":True},{"extensions":(".md",)},{"include_roots":["."]},{"version":"other"}):
            with self.assertRaises(KnowledgeError):
                CorpusPolicy(**kwargs)

    def test_failed_refresh_preserves_old_pointer_and_graph(self):
        self.service.refresh()
        before=self.service.pointer.read_bytes()
        graph=self.service.status().graph
        with patch.object(self.provider,"index",side_effect=KnowledgeError("provider_timeout","Timeout")):
            result=self.service.refresh()
        self.assertEqual(result.status,"failed")
        self.assertEqual(self.service.pointer.read_bytes(),before)
        self.assertEqual(self.service.status().graph,graph)
        self.assertEqual(self.service.query("entry").status,"ok")

    def test_partial_manifest_or_foreign_sources_never_publish(self):
        self.service.refresh()
        before=self.service.pointer.read_bytes()
        fixtures=(
            (b'{"nodes":[],"edges":[]}',{}),
            (b'{"nodes":[{"id":"x","source_file":"../other.py"}],"edges":[]}',{}),
            (b'{"nodes":[{"id":"x","source_file":"entry.py"}],"edges":[{"source":"missing","target":"x"}]}',{}),
            (b'[]',{}),
            (b'{"nodes":[{"id":"x","source_file":"entry.py"}],"edges":[]}',{"entry.py":{"ast_hash":"bad"}}),
        )
        for returned in fixtures:
            with self.subTest(returned=returned),patch.object(self.provider,"index",return_value=returned):
                self.assertEqual(self.service.refresh().status,"failed")
                self.assertEqual(self.service.pointer.read_bytes(),before)

    def test_source_drift_during_index_preserves_old_graph(self):
        self.service.refresh()
        before=self.service.pointer.read_bytes()
        original=self.provider.index
        def drift(corpus,output):
            result=original(corpus,output)
            (self.root/"entry.py").write_text("changed=1")
            return result
        with patch.object(self.provider,"index",side_effect=drift):
            result=self.service.refresh()
        self.assertEqual(result.error["code"],"source_drift")
        self.assertEqual(self.service.pointer.read_bytes(),before)
        self.assertEqual(self.service.status().state,"stale")

    def test_ast_placeholder_has_no_fake_source_evidence(self):
        original=self.provider.index
        def with_external(corpus,output):
            data,manifest=original(corpus,output)
            graph=json.loads(data)
            graph["nodes"].append({"id":"external","label":"Path","source_file":"","source_location":"","_origin":"ast"})
            graph["edges"].append({"source":"entry.py","target":"external"})
            graph["edges"].append({"source":"entry.py","target":"pathlib","relation":"imports", "source_file":"entry.py","_origin":"ast"})
            return json.dumps(graph).encode(),manifest
        with patch.object(self.provider,"index",side_effect=with_external):
            self.assertEqual(self.service.refresh().status,"indexed")
        self.assertEqual(self.service._load()["coverage"]["unresolved_nodes"],1)
        self.assertEqual(self.service._load()["coverage"]["external_import_edges"],1)

    def test_pointer_publication_failure_retains_old_version(self):
        self.service.refresh()
        before=self.service.pointer.read_bytes()
        with patch.object(self.service,"_publish_pointer",side_effect=OSError("disk")):
            self.assertEqual(self.service.refresh().status,"failed")
        self.assertEqual(self.service.pointer.read_bytes(),before)
        self.assertEqual(self.service.status().state,"fresh")

    def test_corrupt_graph_and_pointer_fail_closed(self):
        self.service.refresh()
        (self.root/self.service.status().graph["path"]).write_bytes(b"corrupt")
        self.assertEqual(self.service.status().state,"failed")
        self.assertEqual(self.service.query("entry").status,"degraded")
        self.assertEqual(self.service.refresh().status,"failed")
        self.service.pointer.write_text('{"ref":"other","role":"index"}')
        self.assertEqual(self.service.status().state,"failed")

    def test_writer_lock_not_deleted_if_not_owned(self):
        self.service.refresh()
        lock=self.service.folder/"refresh.lock"
        lock.write_text("other")
        self.assertEqual(self.service.refresh().error["code"],"refresh_conflict")
        self.assertEqual(lock.read_text(),"other")

    def test_hard_content_limit_and_only_indexed_citations(self):
        self.service.refresh()
        with patch.object(self.provider,"query",return_value="NODE x [src=../other.py loc=L1]\n"+"x"*10000):
            query=self.service.query("entry",max_chars=50)
        self.assertEqual(len(query.content),50)
        self.assertEqual(query.citations,())
        self.assertTrue(any("truncated" in item for item in query.limitations))

    def test_query_source_drift_and_provider_failure_are_degraded(self):
        self.service.refresh()
        def drift(*args,**kwargs):
            (self.root/"entry.py").write_text("changed=1")
            return "NODE entry [src=entry.py loc=L1]"
        with patch.object(self.provider,"query",side_effect=drift):
            self.assertEqual(self.service.query("entry").freshness,"stale")
        self.service.refresh()
        with patch.object(self.provider,"query",side_effect=KnowledgeError("provider_failure","down")):
            self.assertEqual(self.service.query("entry").status,"degraded")

    def test_query_validation_and_no_switch_or_arbitrary_tool(self):
        for kwargs in ({"question":""},{"question":"я"*1000},{"question":"x","depth":True},
                       {"question":"x","depth":7},{"question":"x","mode":"other"},
                       {"question":"x","token_budget":0},{"question":"x","max_chars":0},
                       {"question":"x","allow_stale":"yes"}):
            with self.assertRaises(KnowledgeError):
                self.service.query(**kwargs)
        with self.assertRaises(TypeError):
            self.service.query("x",project_path="other")
        with self.assertRaises(TypeError):
            self.service.query("x",tool="list_prs")

    def test_project_isolation_and_provider_profile_mismatch(self):
        self.service.refresh()
        with tempfile.TemporaryDirectory() as folder:
            other=ProjectKnowledgeService(Path(folder),self.provider)
            self.assertEqual(other.status().state,"missing")
        other_provider=FakeProvider()
        other_provider.identity=ProviderIdentity(version="other")
        self.assertEqual(ProjectKnowledgeService(self.root,other_provider).status().state,"failed")

    def test_junction_in_corpus_and_store_rejected(self):
        if os.name!="nt":
            self.skipTest("Windows junction fixture")
        with tempfile.TemporaryDirectory() as folder:
            link=self.root/"linked"
            result=subprocess.run(["cmd","/c","mklink","/J",str(link),folder],capture_output=True)
            self.assertEqual(result.returncode,0)
            try:
                with self.assertRaises(KnowledgeError):
                    self.service.snapshot()
            finally:
                link.rmdir()
            store=self.root/".orchestrator"
            result=subprocess.run(["cmd","/c","mklink","/J",str(store),folder],capture_output=True)
            self.assertEqual(result.returncode,0)
            try:
                with self.assertRaises(KnowledgeError):
                    self.service.refresh()
            finally:
                store.rmdir()


class KnowledgeTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_bounded_command_success_timeout_and_output(self):
        self.assertEqual(bounded_run([sys.executable,"-c","print('ok')"],self.root),b"ok\r\n" if os.name=="nt" else b"ok\n")
        for code,kwargs,expected in (("import time; time.sleep(5)",{"timeout":0.1},"provider_timeout"),
            ("import sys; sys.stdout.write('x'*100000)",{"byte_limit":100},"provider_output_limit"),
            ("import sys; sys.stderr.write('x'*100000)",{"byte_limit":100},"provider_output_limit"),
            ("raise SystemExit(2)",{},"provider_failure")):
            with self.assertRaises(KnowledgeError) as error:
                bounded_run([sys.executable,"-c",code],self.root,**kwargs)
            self.assertEqual(error.exception.code,expected)

    def test_environment_strips_credentials_and_global_provider_settings(self):
        with patch.dict(os.environ,{"OPENAI_API_KEY":"not-real","GRAPHIFY_FORCE":"1","GRAPHIFY_QUERY_LOG":"outside"}):
            env=provider_environment()
        self.assertNotIn("OPENAI_API_KEY",env)
        self.assertNotIn("GRAPHIFY_FORCE",env)
        self.assertNotIn("GRAPHIFY_QUERY_LOG",env)
        self.assertEqual(env["GRAPHIFY_QUERY_LOG_DISABLE"],"1")

    def test_stdio_malformed_wrong_id_and_no_response(self):
        for code,expected in (("import sys; sys.stdin.readline(); print('bad',flush=True)","provider_contract_violation"),
            ("import sys; sys.stdin.readline(); print('{\"jsonrpc\":\"2.0\",\"id\":true,\"result\":{}}',flush=True)","provider_contract_violation"),
            ("import sys; sys.stdin.readline(); print('{\"jsonrpc\":\"2.0\",\"id\":99,\"result\":{}}',flush=True)","provider_contract_violation"),
            ("import sys,time; sys.stdin.readline(); time.sleep(5)","provider_timeout")):
            client=StdioMCP([sys.executable,"-u","-c",code],self.root,timeout=0.2)
            try:
                with self.assertRaises(KnowledgeError) as error:
                    client.call("initialize",{})
                self.assertEqual(error.exception.code,expected)
            finally:
                client.close()

    def test_provider_version_and_limits(self):
        with self.assertRaises(KnowledgeError):
            GraphifyProvider(Path(sys.executable),query_timeout=True)
        provider=GraphifyProvider(Path(sys.executable))
        with patch("orchestrator.graphify_provider.bounded_run",return_value=b"other"):
            with self.assertRaises(KnowledgeError) as error:
                provider.verify(self.root)
        self.assertEqual(error.exception.code,"provider_version_mismatch")


class ManifestCompatibilityTests(unittest.TestCase):
    def test_documents_require_semantic_manifest_hash_and_graph_evidence(self):
        from orchestrator.knowledge_contracts import SourceFile, SourceSnapshot
        content = b"# Durable architecture\n"
        path = "docs/architecture/knowledge.md"
        snapshot = SourceSnapshot("0" * 64, "0" * 64,
                                  (SourceFile(path, hashlib.sha256(content).hexdigest(), len(content)),), len(content))
        md5 = {path: hashlib.md5(content, usedforsecurity=False).hexdigest()}
        graph = json.dumps({"nodes": [{"id": "doc", "source_file": path}], "edges": []}).encode()
        _, coverage = ProjectKnowledgeService._validate_graph(
            graph, {path: {"ast_hash": "", "semantic_hash": md5[path]}}, snapshot, {path}, md5)
        self.assertEqual(coverage["represented_files"], 1)
        for manifest in ({path: {"ast_hash": md5[path]}}, {path: {"semantic_hash": "wrong"}}):
            with self.assertRaises(KnowledgeError) as error:
                ProjectKnowledgeService._validate_graph(graph, manifest, snapshot, {path}, md5)
            self.assertEqual(error.exception.code, "incomplete_extraction")
        with self.assertRaises(KnowledgeError):
            ProjectKnowledgeService._validate_graph(b'{"nodes":[],"edges":[]}',
                {path: {"semantic_hash": md5[path]}}, snapshot, {path}, md5)

    def test_operational_sources_excluded_without_enabling_documents(self):
        from orchestrator.knowledge_snapshot import allowed_durable_path
        self.assertFalse(allowed_durable_path(Path("docs/plans/draft.md")))
        self.assertFalse(allowed_durable_path(Path("Docs/Reports/intermediate.py")))
        self.assertTrue(allowed_durable_path(Path("docs/architecture/knowledge.md")))
        self.assertNotIn(".md", CorpusPolicy().extensions)
        self.assertEqual(CorpusPolicy().version, "code-corpus/v1")


class RealGraphifyIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("ORCHESTRATOR_GRAPHIFY_PYTHON"),"explicit pinned Graphify interpreter required")
    def test_real_staging_refresh_mcp_unicode_frontend_rename_delete(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"helper.py").write_text("def helper(): return 1\n",encoding="utf-8")
            (root/"модуль.py").write_text("from helper import helper\ndef entry(): return helper()\n",encoding="utf-8")
            (root/"Card.tsx").write_text("export function Card(){return <div/>;}\n",encoding="utf-8")
            (root/"Panel.vue").write_text('<script setup lang="ts">function greet(){return "Hi";}</script><template>{{greet()}}</template>\n',encoding="utf-8")
            (root/"__init__.py").write_text("")
            service=ProjectKnowledgeService(root,GraphifyProvider(Path(os.environ["ORCHESTRATOR_GRAPHIFY_PYTHON"])))
            result=service.refresh()
            self.assertEqual(result.status,"indexed",result.error)
            query=service.query("helper entry")
            self.assertEqual(query.status,"ok",query.error)
            self.assertIn("helper",query.content)
            self.assertTrue(query.citations)
            (root/"модуль.py").rename(root/"renamed.py")
            (root/"Panel.vue").unlink()
            self.assertEqual(service.status().state,"stale")
            before_update = json.loads(service.repository.get("project-knowledge", "graph", service.status().graph["version"], max_bytes=GraphifyProvider.max_graph_bytes).content)
            self.assertEqual(service.refresh_incremental().status,"indexed")
            self.assertEqual(service._load()["mode"], "incremental")
            self.assertEqual(ProjectKnowledgeService(root,service.provider).status().state,"fresh")
            after_update = json.loads(service.repository.get("project-knowledge", "graph", service.status().graph["version"], max_bytes=GraphifyProvider.max_graph_bytes).content)
            before_helper = {node["id"] for node in before_update["nodes"] if node.get("source_file") == "helper.py"}
            after_helper = {node["id"] for node in after_update["nodes"] if node.get("source_file") == "helper.py"}
            self.assertTrue(before_helper)
            self.assertTrue(before_helper.issubset(after_helper))
            q=service.query("entry helper")
            self.assertEqual(q.status,"ok",q.error)
            self.assertNotIn("модуль.py",q.content)
            self.assertNotIn("Panel.vue",q.content)


if __name__=="__main__":
    unittest.main()
