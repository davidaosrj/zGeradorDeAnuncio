"""Cliente mínimo e sem dependências para a API HTTP do Ollama."""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://192.168.1.231:11434"


class OllamaError(RuntimeError):
    """Erro de conexão ou de contrato com o Ollama."""


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str = DEFAULT_BASE_URL
    model: str | None = None
    timeout_seconds: float = 120.0

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        raw_timeout = os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")
        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise OllamaError("OLLAMA_TIMEOUT_SECONDS deve ser um número positivo") from exc
        if timeout <= 0:
            raise OllamaError("OLLAMA_TIMEOUT_SECONDS deve ser um número positivo")
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL),
            model=os.getenv("OLLAMA_MODEL") or None,
            timeout_seconds=timeout,
        )


class OllamaClient:
    def __init__(
        self,
        config: OllamaConfig | None = None,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.config = config or OllamaConfig.from_env()
        self._opener = opener

    def list_models(self) -> list[str]:
        payload = self._request("GET", "/api/tags")
        models = payload.get("models")
        if not isinstance(models, list):
            raise OllamaError("Resposta de /api/tags não contém uma lista 'models'")
        return [item["name"] for item in models if isinstance(item, dict) and isinstance(item.get("name"), str)]

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        format: str | dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        selected_model = model or self.config.model
        if not selected_model:
            raise OllamaError("Informe o modelo com --model ou OLLAMA_MODEL")
        body: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "stream": False,
        }
        if format is not None:
            body["format"] = format
        if options is not None:
            body["options"] = options
        payload = self._request("POST", "/api/chat", body)
        message = payload.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise OllamaError("Resposta de /api/chat não contém 'message.content'")
        return message["content"]

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with self._opener(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama respondeu HTTP {exc.code}: {detail}") from exc
        except (URLError, socket.timeout, TimeoutError, OSError) as exc:
            raise OllamaError(f"Não foi possível acessar {url}: {exc}") from exc
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise OllamaError(f"Ollama retornou JSON inválido em {path}") from exc
        if not isinstance(payload, dict):
            raise OllamaError(f"Ollama retornou um objeto inválido em {path}")
        return payload
