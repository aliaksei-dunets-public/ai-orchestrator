"""Bounded subprocess и минимальный read-only stdio MCP client."""
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time

from .knowledge_contracts import KnowledgeError


def provider_environment():
    names = ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
             "APPDATA", "LOCALAPPDATA")
    env = {name: os.environ[name] for name in names if name in os.environ}
    env.update(PYTHONUTF8="1", GRAPHIFY_QUERY_LOG_DISABLE="1", GRAPHIFY_MAX_WORKERS="1")
    return env


class _BoundedProcess:
    def __init__(self, args, cwd, byte_limit, *, lines=False):
        try:
            self.process = subprocess.Popen(args, cwd=cwd, env=provider_environment(), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        except OSError as exc:
            raise KnowledgeError("provider_unavailable", "Не удалось запустить provider process") from exc
        self.limit = byte_limit
        self.size = 0
        self.error = None
        self.stdout = bytearray()
        self.messages = queue.Queue(maxsize=32)
        self.lock = threading.Lock()
        self.threads = []
        for stream, is_stdout in ((self.process.stdout, True), (self.process.stderr, False)):
            thread = threading.Thread(target=self._read, args=(stream, is_stdout, lines), daemon=True)
            thread.start()
            self.threads.append(thread)

    def _read(self, stream, is_stdout, lines):
        try:
            while True:
                chunk = stream.readline(self.limit + 1) if lines and is_stdout else stream.read1(4096)
                if not chunk:
                    if lines and is_stdout:
                        self.messages.put_nowait(None)
                    break
                with self.lock:
                    self.size += len(chunk)
                    if self.size > self.limit:
                        raise KnowledgeError("provider_output_limit", "Превышен process output byte budget")
                    if is_stdout and not lines:
                        self.stdout.extend(chunk)
                if lines and is_stdout:
                    self.messages.put_nowait(chunk)
        except queue.Full:
            self._fail(KnowledgeError("provider_output_limit", "Превышен MCP message queue budget"))
        except (OSError, ValueError, KnowledgeError) as exc:
            self._fail(exc if isinstance(exc, KnowledgeError) else KnowledgeError("provider_failure", "Ошибка pipe reader"))

    def _fail(self, error):
        with self.lock:
            self.error = self.error or error
        try:
            self.process.kill()
        except OSError:
            pass

    def close(self):
        if self.process.poll() is None:
            self._fail(KnowledgeError("provider_closed", "Provider process закрыт"))
        try:
            self.process.stdin.close()
        except OSError:
            pass
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
        for thread in self.threads:
            thread.join(timeout=1)
        self.process.stdout.close()
        self.process.stderr.close()


def bounded_run(args, cwd, *, timeout=90, byte_limit=1024 * 1024):
    proc = _BoundedProcess(args, cwd, byte_limit)
    try:
        proc.process.stdin.close()
        try:
            result = proc.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise KnowledgeError("provider_timeout", "Истёк timeout provider command") from exc
        for thread in proc.threads:
            thread.join(timeout=1)
        if proc.error:
            raise proc.error
        if result:
            raise KnowledgeError("provider_failure", "Provider command завершилась ошибкой", exit_code=result)
        return bytes(proc.stdout)
    finally:
        proc.close()


class StdioMCP:
    def __init__(self, args, cwd, *, timeout=25, byte_limit=1024 * 1024):
        self.proc = _BoundedProcess(args, cwd, byte_limit, lines=True)
        self.timeout = timeout
        self.deadline = time.monotonic() + timeout
        self.seq = 0

    def notify(self, method):
        self._send({"jsonrpc":"2.0", "method":method})

    def _send(self, message):
        if self.proc.error:
            raise self.proc.error
        data = json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"
        if len(data) > 8192:
            raise KnowledgeError("validation_failed", "MCP request превышает 8192 bytes")
        errors = []
        def write():
            try:
                self.proc.process.stdin.write(data)
                self.proc.process.stdin.flush()
            except (OSError, ValueError) as exc:
                errors.append(exc)
        thread = threading.Thread(target=write,daemon=True)
        thread.start()
        thread.join(timeout=max(0,self.deadline-time.monotonic()))
        if thread.is_alive():
            error = KnowledgeError("provider_timeout", "Истёк MCP session timeout при записи")
            self.proc._fail(error)
            thread.join(timeout=1)
            raise error
        if errors:
            raise KnowledgeError("provider_failure", "MCP stdin недоступен") from errors[0]

    def call(self, method, params):
        self.seq += 1
        self._send({"jsonrpc":"2.0", "id":self.seq, "method":method, "params":params})
        return self._wait_response(self.deadline)

    def _wait_response(self, deadline):
        messages = 0
        while time.monotonic() < deadline:
            if self.proc.error:
                raise self.proc.error
            try:
                raw = self.proc.messages.get(timeout=min(0.1, max(0.001, deadline - time.monotonic())))
            except queue.Empty:
                continue
            answer = self._decode(raw)
            if answer is not None:
                return answer
            messages += 1
            if messages > 100:
                raise KnowledgeError("provider_output_limit", "Превышен MCP notification budget")
        raise KnowledgeError("provider_timeout", "Истёк MCP response timeout")

    def _decode(self, raw):
        if raw is None:
            raise self.proc.error or KnowledgeError("provider_failure", "MCP stdout закрыт")
        try:
            message = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise KnowledgeError("provider_contract_violation", "MCP response не JSON") from exc
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            raise KnowledgeError("provider_contract_violation", "Неверный MCP envelope")
        if "method" in message:
            if "id" in message:
                raise KnowledgeError("provider_contract_violation", "Server requests не поддержаны")
            return None
        if type(message.get("id")) is not int or message["id"] != self.seq or "error" in message or "result" not in message:
            raise KnowledgeError("provider_contract_violation", "Неверный MCP response identity/result")
        if not isinstance(message["result"], dict):
            raise KnowledgeError("provider_contract_violation", "MCP result должен быть объектом")
        return message["result"]

    def close(self):
        self.proc.close()
