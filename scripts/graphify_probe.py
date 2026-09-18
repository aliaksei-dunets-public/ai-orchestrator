"""Безопасный локальный probe upstream Graphify, не knowledge adapter.

Запуск: основная .venv python scripts/graphify_probe.py --python <Graphify Python>.
Только синтетические fixtures в .tmp; никаких install/hooks/global команд.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import tempfile
import threading
from pathlib import Path


VERSION = "0.9.63"


def clean_env():
    env = {name: os.environ[name] for name in (
        "SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
        "APPDATA", "LOCALAPPDATA",
    ) if name in os.environ}
    env.update(PYTHONUTF8="1", GRAPHIFY_QUERY_LOG_DISABLE="1", GRAPHIFY_MAX_WORKERS="1")
    return env


def command(python, args, cwd):
    result = subprocess.run([str(python), *args], cwd=cwd, env=clean_env(), capture_output=True,
                            encoding="utf-8", errors="replace", timeout=90)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {result.stderr[-4000:]} {result.stdout[-2000:]}")
    return result.stdout


class ProbeMCP:
    def __init__(self, python, graph, cwd):
        self.process = subprocess.Popen([str(python), "-X", "utf8", "-m", "graphify.serve", str(graph)],
            cwd=cwd, env=clean_env(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding="utf-8", errors="replace", bufsize=1)
        self.messages = queue.Queue(maxsize=100)
        self.stderr = ""
        self.seq = 0
        def reader():
            for line in self.process.stdout:
                self.messages.put(line)
            self.messages.put(None)
        def errors():
            for line in self.process.stderr:
                self.stderr = (self.stderr + line)[-4000:]
        threading.Thread(target=reader, daemon=True).start()
        threading.Thread(target=errors, daemon=True).start()

    def call(self, method, params):
        self.seq += 1
        self.send({"jsonrpc":"2.0", "id":self.seq, "method":method, "params":params})
        for _ in range(100):
            raw = self.messages.get(timeout=25)
            if raw is None:
                raise RuntimeError("MCP exited: " + self.stderr)
            message = json.loads(raw)
            if message.get("id") != self.seq:
                continue
            if "error" in message:
                raise RuntimeError(str(message["error"]))
            return message["result"]
        raise RuntimeError("MCP notification limit")

    def send(self, message):
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()


def probe(python, workspace):
    temp_base = (workspace / ".tmp").resolve()
    temp_base.mkdir(exist_ok=True)
    assert temp_base.is_relative_to(workspace.resolve())
    with tempfile.TemporaryDirectory(prefix="graphify-probe-", dir=temp_base) as folder:
        root = Path(folder).resolve()
        assert root.is_relative_to(temp_base)
        (root / "helper.py").write_text("class Base:\n    pass\n\ndef helper():\n    return 1\n", encoding="utf-8")
        (root / "модуль.py").write_text("from helper import Base, helper\nclass Child(Base):\n    def call(self):\n        return helper()\n", encoding="utf-8")
        (root / "Card.tsx").write_text("export function Card() { return <div>Hello</div>; }\n", encoding="utf-8")
        (root / "Panel.vue").write_text('<script setup lang="ts">\nfunction greet() { return "Hi"; }\n</script>\n<template><div>{{ greet() }}</div></template>\n', encoding="utf-8")
        (root / "notes.md").write_text("Synthetic doc; must not need semantic backend.\n", encoding="utf-8")
        actual = command(python, ["-c", "from importlib.metadata import version; print(version('graphifyy'))"], root).strip()
        assert actual == VERSION, actual
        out = root / "indexed"
        extract = ["-X", "utf8", "-m", "graphify", "extract", str(root), "--code-only", "--no-cluster", "--out", str(out), "--force", "--exclude", "indexed/**"]
        initial_output = command(python, extract, root)
        graph = out / "graphify-out" / "graph.json"
        data = json.loads(graph.read_text(encoding="utf-8"))
        initial_sources = sorted({node.get("source_file", "") for node in data["nodes"]})
        labels = {node.get("label", "") for node in data["nodes"]}
        assert any("helper" in label for label in labels), labels
        assert any("Card" in label for label in labels), labels
        mcp = ProbeMCP(python, graph, root)
        try:
            handshake = mcp.call("initialize", {"protocolVersion":"2025-03-26", "capabilities":{}, "clientInfo":{"name":"orchestrator-probe","version":"1"}})
            mcp.send({"jsonrpc":"2.0","method":"notifications/initialized"})
            catalog = mcp.call("tools/list", {})["tools"]
            names = {tool["name"] for tool in catalog}
            assert {"query_graph","get_node","graph_stats"}.issubset(names), names
            query = mcp.call("tools/call", {"name":"query_graph", "arguments":{"question":"helper Child Base", "mode":"bfs", "depth":2, "token_budget":500}})
            assert not query.get("isError"), query
            query_text = "\n".join(part.get("text", "") for part in query.get("content", []) if part["type"] == "text")
            assert "helper" in query_text.lower(), query_text
            stats = mcp.call("tools/call", {"name":"graph_stats","arguments":{}})
            assert not stats.get("isError"), stats
        finally:
            mcp.close()
        (root / "модуль.py").rename(root / "renamed.py")
        (root / "Panel.vue").unlink()
        command(python, extract, root)
        changed = json.loads(graph.read_text(encoding="utf-8"))
        changed_sources = sorted({node.get("source_file", "") for node in changed["nodes"]})
        assert not any("модуль.py" in source or "Panel.vue" in source for source in changed_sources), changed_sources
        assert any("renamed.py" in source for source in changed_sources), changed_sources
        return {"provider":"Graphify-Labs/graphify", "version":actual,
                "fixture_nodes":len(data["nodes"]), "fixture_edges":len(data["edges"]),
                "initial_sources":initial_sources, "after_rename_delete_sources":changed_sources,
                "mcp_protocol":handshake["protocolVersion"], "mcp_tools":sorted(names),
                "project_switch_supported_upstream":any("project_path" in tool.get("inputSchema",{}).get("properties",{}) for tool in catalog),
                "query_chars":len(query_text), "query_excerpt":query_text[:1800],
                "code_only_without_credentials":True,
                "extract_excerpt":initial_output[-1200:], "scope":"upstream fixture probe; not production adapter"}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--python",type=Path,required=True)
    args=parser.parse_args()
    workspace=Path(__file__).resolve().parent.parent
    print(json.dumps(probe(args.python.resolve(),workspace),ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
