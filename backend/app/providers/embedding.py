from __future__ import annotations

from app.research.embedding import TextEmbedder, checked_vectors
from app.services.ai_providers import AiTask

from . import router
from .router import Principal

__all__ = ["router_embedder"]


def router_embedder(principal: Principal | None = None) -> TextEmbedder:
    async def embed(texts: list[str]) -> list[list[float]]:
        result = await router.run(AiTask.EMBED, texts=texts, principal=principal)
        return checked_vectors(result.embeddings, expected=len(texts))

    return embed
