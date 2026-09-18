"""Version-pinned CLI indexer и query_graph-only MCP adapter."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .knowledge_contracts import KnowledgeError, ProviderCapabilities, ProviderIdentity
from .knowledge_process import StdioMCP, bounded_run


class GraphifyProvider:
    identity = ProviderIdentity()
    capabilities = ProviderCapabilities()
    max_graph_bytes = 32 * 1024 * 1024

    def __init__(self, python: Path, *, index_timeout: int = 90, query_timeout: int = 25,
                 process_byte_limit: int = 1024 * 1024):
        for value in (index_timeout, query_timeout, process_byte_limit):
            if type(value) is not int or value < 1:
                raise KnowledgeError("validation_failed", "Provider limits должны быть положительными целыми")
        self.python = Path(python).resolve()
        self.index_timeout, self.query_timeout, self.process_byte_limit = index_timeout, query_timeout, process_byte_limit
        self._verified = False

    def verify(self, cwd: Path):
        if not self._verified:
            value = bounded_run([str(self.python), "-X", "utf8", "-c",
                "from importlib.metadata import version; print(version('graphifyy'))"], cwd,
                timeout=self.query_timeout, byte_limit=self.process_byte_limit).decode("utf-8").strip()
            if value != self.identity.version:
                raise KnowledgeError("provider_version_mismatch", "Требуется закреплённая Graphify version", expected=self.identity.version)
            self._verified = True

    def index(self, corpus_root: Path, output_root: Path):
        self.verify(corpus_root)
        bounded_run([str(self.python), "-X", "utf8", "-m", "graphify", "extract", str(corpus_root),
            "--code-only", "--no-cluster", "--no-gitignore", "--force", "--max-workers", "1", "--out", str(output_root)],
            corpus_root, timeout=self.index_timeout, byte_limit=self.process_byte_limit)
        folder = output_root / "graphify-out"
        try:
            with (folder / "graph.json").open("rb") as stream:
                content = stream.read(self.max_graph_bytes + 1)
            with (folder / "manifest.json").open("rb") as stream:
                manifest_content = stream.read(self.max_graph_bytes + 1)
            if max(len(content),len(manifest_content)) > self.max_graph_bytes:
                raise KnowledgeError("provider_output_limit", "Graph/manifest превышает byte budget")
            manifest = json.loads(manifest_content)
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            raise KnowledgeError("provider_contract_violation", "Не получены валидные graph/manifest") from exc
        return content, manifest

    def incremental_update(self, corpus_root: Path, *, base_graph: bytes, base_manifest: dict):
        """Run Graphify's native AST-only incremental update on a staged corpus.

        The caller supplies the last validated graph and manifest. Graphify owns
        changed-file extraction, dependency refresh and pruning of deleted files;
        this adapter only prepares the provider workspace and reads its output.
        """
        self.verify(corpus_root)
        if not isinstance(base_graph, bytes) or len(base_graph) > self.max_graph_bytes:
            raise KnowledgeError("provider_output_limit", "Base graph превышает byte budget")
        if not isinstance(base_manifest, dict):
            raise KnowledgeError("incremental_baseline_missing", "Нет валидного Graphify manifest baseline")
        provider_out = corpus_root / "graphify-out"
        provider_out.mkdir(parents=True, exist_ok=True)
        (provider_out / "graph.json").write_bytes(base_graph)
        (provider_out / "manifest.json").write_text(
            json.dumps(base_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        bounded_run([str(self.python), "-X", "utf8", "-m", "graphify", "update", str(corpus_root), "--no-cluster"],
                    corpus_root, timeout=self.index_timeout, byte_limit=self.process_byte_limit)
        try:
            content = (provider_out / "graph.json").read_bytes()
            manifest = json.loads((provider_out / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            raise KnowledgeError("provider_contract_violation", "Incremental Graphify output недоступен") from exc
        if len(content) > self.max_graph_bytes or not isinstance(manifest, dict):
            raise KnowledgeError("provider_output_limit", "Incremental graph/manifest превышает byte budget")
        # Graphify's native update path emits the classic node-link spelling
        # ``links`` while full extract emits ``edges``.  Normalize the contract
        # for ProjectKnowledgeService while preserving the upstream field for
        # MCP/query compatibility and auditability.
        try:
            graph = json.loads(content)
            if isinstance(graph, dict) and "edges" not in graph and isinstance(graph.get("links"), list):
                graph["edges"] = graph["links"]
                content = json.dumps(graph, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            raise KnowledgeError("provider_contract_violation", "Incremental graph JSON недействителен") from exc
        if len(content) > self.max_graph_bytes:
            raise KnowledgeError("provider_output_limit", "Нормализованный incremental graph превышает byte budget")
        return content, manifest

    def query(self, graph_path: Path, cwd: Path, *, question: str, mode: str, depth: int, token_budget: int):
        # Upstream отвергает payload.bin: ему требуется .json. Изолированная
        # копия также не позволяет подмешать work-memory sidecars repository.
        with graph_path.open("rb") as stream:
            graph = stream.read(self.max_graph_bytes + 1)
        if len(graph) > self.max_graph_bytes:
            raise KnowledgeError("provider_output_limit", "Query graph превышает byte budget")
        with tempfile.TemporaryDirectory(prefix="orchestrator-graph-query-") as name:
            isolated = Path(name) / "graph.json"
            isolated.write_bytes(graph)
            return self._query_json(isolated,cwd,question=question,mode=mode,depth=depth,token_budget=token_budget)

    def _query_json(self, graph_path: Path, cwd: Path, *, question: str, mode: str, depth: int, token_budget: int):
        self.verify(cwd)
        client = StdioMCP([str(self.python), "-X", "utf8", "-m", "graphify.serve", str(graph_path)], cwd,
                          timeout=self.query_timeout, byte_limit=self.process_byte_limit)
        try:
            handshake = client.call("initialize", {"protocolVersion":"2025-03-26", "capabilities":{},
                "clientInfo":{"name":"orchestrator-knowledge","version":"1"}})
            if handshake.get("protocolVersion") != "2025-03-26":
                raise KnowledgeError("provider_contract_violation", "Неожиданная MCP protocol version")
            client.notify("notifications/initialized")
            catalog = client.call("tools/list", {})
            tools = catalog.get("tools")
            if not isinstance(tools, list) or not any(isinstance(tool, dict) and tool.get("name") == "query_graph" for tool in tools):
                raise KnowledgeError("provider_contract_violation", "query_graph отсутствует в MCP catalog")
            result = client.call("tools/call", {"name":"query_graph", "arguments":{
                "question":question, "mode":mode, "depth":depth, "token_budget":token_budget}})
            content = result.get("content")
            if result.get("isError") or not isinstance(content, list) or not content:
                raise KnowledgeError("provider_failure", "MCP query отказала")
            if any(not isinstance(part, dict) or part.get("type") != "text" or not isinstance(part.get("text"), str) for part in content):
                raise KnowledgeError("provider_contract_violation", "Поддержан только текстовый query result")
            text = "\n".join(part["text"] for part in content)
            if text.lower().startswith(("error:", "error executing ", "unknown tool:")):
                raise KnowledgeError("provider_failure", "Upstream вернул текстовую ошибку")
            return text
        finally:
            client.close()
