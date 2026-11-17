from __future__ import annotations

from typing import Any

from google.genai import _transformers, types

from app.providers.gemini_p import GeminiAdapter

EMBEDDING_MODEL = "gemini-embedding-2"
TEXTS = ["Alum fixes alizarin on cotton.", "Iron water darkens the black.", "Kutch water is hard."]


class RecordingModels:
    def __init__(self) -> None:
        self.contents: list[Any] = []

    async def embed_content(self, *, model: str, contents: Any, config: Any) -> Any:
        self.contents.append(contents)
        sent = _transformers.t_contents(contents)
        return types.EmbedContentResponse(
            embeddings=[types.ContentEmbedding(values=[float(n)]) for n in range(len(sent))]
        )


def adapter_with(models: RecordingModels) -> GeminiAdapter:
    adapter = GeminiAdapter(api_key="test-key", base_url=None, preset="gemini", extra={}, learned={})
    adapter.client = type("Client", (), {"aio": type("Aio", (), {"models": models})()})()
    return adapter


async def test_each_text_is_its_own_content_so_gemini_embedding_2_returns_one_vector_per_text() -> None:
    models = RecordingModels()
    vectors = await adapter_with(models).embed(TEXTS, EMBEDDING_MODEL)
    assert vectors == [[0.0], [1.0], [2.0]]
    (contents,) = models.contents
    assert [[part.text for part in content.parts] for content in contents] == [[text] for text in TEXTS]


def test_plain_strings_would_be_merged_into_one_content_by_the_sdk() -> None:
    assert len(_transformers.t_contents(TEXTS)) == 1
    built = [types.Content(parts=[types.Part(text=text)]) for text in TEXTS]
    assert len(_transformers.t_contents(built)) == len(TEXTS)
