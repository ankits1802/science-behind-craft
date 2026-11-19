from __future__ import annotations

from typing import Any

import pytest

from app.research.retrieval import KnowledgeQuery
from app.retrieval.hybrid import StoredKnowledgeSearch, search_words

HINDI_QUESTION = "अजरख में फिटकरी क्यों डाली जाती है?"
MIXED_QUESTION = "अजरख में alum क्यों?"
ENGLISH_RENDERING = "Why is alum added in Ajrakh?"


class Rendering:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.asked: list[str] = []

    async def __call__(self, text: str) -> str:
        self.calls.append("render")
        self.asked.append(text)
        return ENGLISH_RENDERING


class Stopped(Exception):
    pass


class RecordingSession:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def execute(self, statement: Any) -> Any:
        self.calls.append("execute")
        raise Stopped


async def test_a_question_without_latin_words_is_searched_in_its_english_rendering() -> None:
    rendering = Rendering([])
    assert await search_words(HINDI_QUESTION, rendering) == ENGLISH_RENDERING
    assert rendering.asked == [HINDI_QUESTION]


async def test_a_question_with_latin_words_makes_no_model_call() -> None:
    rendering = Rendering([])
    assert await search_words(MIXED_QUESTION, rendering) == MIXED_QUESTION
    assert await search_words("Why is alum used?", rendering) == "Why is alum used?"
    assert rendering.asked == []


async def test_without_a_rendering_the_question_is_searched_as_asked() -> None:
    assert await search_words(HINDI_QUESTION, None) == HINDI_QUESTION


async def test_the_rendering_and_the_vector_come_before_the_search_takes_a_connection() -> None:
    session = RecordingSession()
    rendering = Rendering(session.calls)

    async def embed(texts: list[str]) -> list[list[float]]:
        session.calls.append("embed")
        assert texts == [f"task: search result | query: {HINDI_QUESTION}"]
        return [[1.0] + [0.0] * 1535]

    search = StoredKnowledgeSearch(session, embed=embed, english=rendering)
    with pytest.raises(Stopped):
        await search.search(KnowledgeQuery(craft_slug="Kutch-Ajrakh", text=HINDI_QUESTION, mode="HYBRID"))
    assert session.calls == ["render", "embed", "execute"]
