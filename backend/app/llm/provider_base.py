"""LLM provider abstraction — the contract every backend implements.

Local-first: Ollama is primary; OpenAI-compatible local servers (LM Studio,
llama.cpp, vLLM) are interchangeable; an external cloud provider is allowed ONLY
when ``settings.allow_external_llm`` is true (default false).

Hard rules enforced by callers (see docs/05_local_llm_strategy.md):
  * the LLM never computes a financial number;
  * outputs are strict JSON, schema-validated, retried, repaired;
  * every numeric token is audited against the evidence pack / structured data.

This module defines interfaces and dataclasses only — concrete providers and the
router/audit live in sibling modules and are implemented in milestone M4.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(slots=True)
class ChatRequest:
    messages: list[Message]
    model: str
    temperature: float = 0.2
    json_mode: bool = True           # request strict JSON output
    json_schema: dict[str, Any] | None = None
    max_tokens: int | None = None
    timeout_s: int = 120
    task: str = "generic"            # routing + logging key
    prompt_version: str = "v0"       # logged to model_calls


@dataclass(slots=True)
class ChatResponse:
    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class ChatProvider(Protocol):
    """Every LLM backend implements this. Implementations must:

    - honor ``json_mode`` (native JSON formatting where supported);
    - never raise on model content — only on transport/timeout;
    - return token + latency telemetry for ``model_calls`` logging.
    """

    name: str

    def chat(self, request: ChatRequest) -> ChatResponse: ...

    def embed(self, texts: list[str], model: str) -> list[list[float]]: ...

    def is_available(self) -> bool: ...
