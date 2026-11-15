from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ChatRequest:
    model: str
    system: str
    user: str
    max_tokens: int = 2048
    temperature: float | None = None
    reasoning: bool = False
    reasoning_effort: str | None = None
    reasoning_budget: int | None = None
    json_schema: dict | None = None


@dataclass
class ChatResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int = 0
    meta: dict = field(default_factory=dict)
    cached_input_tokens: int | None = None
    cache_write_tokens: int | None = None


class ProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        status: int | None = None,
        kind: str = "error",
        retry_after: float | None = None,
    ):
        super().__init__(message)
        self.retryable = retryable
        self.status = status
        self.kind = kind
        self.retry_after = retry_after


class Adapter(ABC):
    learned: dict[str, list[str]]

    def __init__(self, *, api_key: str | None, base_url: str | None, preset: str, extra: dict, learned: dict):
        self.api_key = api_key
        self.base_url = base_url
        self.preset = preset
        self.extra = extra or {}
        self.learned = {k: list(v) for k, v in (learned or {}).items()}
        self.learned_changed = False

    def rejects(self, model: str, param: str) -> bool:
        return param in self.learned.get(model, [])

    def learn(self, model: str, param: str) -> None:
        lst = self.learned.setdefault(model, [])
        if param not in lst:
            lst.append(param)
            self.learned_changed = True

    @abstractmethod
    async def chat(self, req: ChatRequest) -> ChatResult: ...

    @abstractmethod
    async def list_models(self) -> list[dict]: ...

    async def embed(self, texts: list[str], model: str, dimensions: int | None = None) -> list[list[float]]:
        raise ProviderError(
            f"{self.preset} does not provide embeddings through this adapter", kind="unavailable"
        )

    async def aclose(self) -> None:
        return None
