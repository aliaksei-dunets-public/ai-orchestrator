"""Платформенный JSON subprocess transport для зарегистрированного model host."""
from __future__ import annotations

import json
import subprocess
import tempfile

from .workflow_builder import canonical
from .workflow_execution import ModelAdapter, reject


def process_model_adapter(*, executor_ref: str, provider: str, argv: list[str], timeout: float = 120,
                          max_bytes: int = 2 * 1024 * 1024) -> ModelAdapter:
    """Host задаёт argv напрямую; TOML не управляет командами/shell.

    Одна команда получает один JSON в stdin, возвращает один JSON в stdout.
    operation=probe: {profile}; ответ {available, provider, model}.
    operation=invoke: {request}; ответ {result, provider, model}.
    Provider wrapper самостоятельно подключает CLI/SDK и обязан сообщить
    модель, которой действительно выполнен запрос. Внутри shell не используется.
    """
    if (not isinstance(argv, list) or not argv or any(not isinstance(p, str) or not p for p in argv)
            or type(timeout) not in {int, float} or timeout <= 0
            or type(max_bytes) is not int or max_bytes < 1):
        reject("invalid_adapter", "Некорректные argv/timeout/max_bytes")
    command = tuple(argv)

    def exchange(value):
        encoded = canonical(value)
        if len(encoded) > max_bytes:
            reject("transport_failure", "Request превышает предел transport")
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            try:
                process = subprocess.run(command, input=encoded, stdout=output, stderr=errors,
                    timeout=timeout, check=False, shell=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValueError("Model transport недоступен или превысил timeout") from exc
            if process.returncode != 0 or output.tell() > max_bytes:
                reject("transport_failure", "Model transport завершился ошибкой или превысил предел ответа")
            output.seek(0)
            try:
                return json.loads(output.read(max_bytes + 1))
            except (ValueError, UnicodeError) as exc:
                raise ValueError("Model transport вернул неверный JSON") from exc

    def available(profile):
        value = exchange({"operation": "probe", "profile": profile})
        if (not isinstance(value, dict) or set(value) != {"available", "provider", "model"}
                or type(value["available"]) is not bool or value["provider"] != profile["provider"]
                or value["model"] != profile["model"]):
            reject("executor_mismatch", "Probe не подтверждает точный model profile")
        return value["available"]

    def invoke(request):
        return exchange({"operation": "invoke", "request": request})

    return ModelAdapter(executor_ref, provider, available, invoke)


__all__ = ["process_model_adapter"]
