import hashlib
import math
import re

import pytest

from app.models.crafts import EMBEDDING_DIMENSIONS
from app.retrieval.evaluation import evaluate_golden
from app.retrieval.golden import GOLDEN_QUESTIONS
from app.retrieval.hybrid import StoredKnowledgeSearch
from app.retrieval.indexing import embed_pending
from app.services.claim_seed import load_seed_claims, seed_claims, seed_id
from app.services.claim_seed_passages import store_seed_passages

from .field_voices_rows import rolled_back

pytestmark = pytest.mark.db

RECALL_AT_5_FLOOR = 1.01
MRR_FLOOR = 1.01
WORD = re.compile(r"[a-z0-9]+")
TEMPLATE_MARKS = ("| query: ", "| text: ")
WORD_MIN_CHARS = 3


def content_of(text: str) -> str:
    for mark in TEMPLATE_MARKS:
        if mark in text:
            return text.split(mark, 1)[1]
    return text


def word_vector(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for word in set(WORD.findall(content_of(text).casefold())):
        if len(word) >= WORD_MIN_CHARS:
            vector[int(hashlib.sha256(word.encode()).hexdigest(), 16) % EMBEDDING_DIMENSIONS] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        vector[0] = 1.0
        return vector
    return [value / norm for value in vector]


async def word_embedder(texts: list[str]) -> list[list[float]]:
    return [word_vector(text) for text in texts]


def test_the_word_vectors_score_shared_words() -> None:
    alum = word_vector("task: search result | query: alum mordant")
    same = word_vector("title: none | text: Alum mordant.")
    other = word_vector("title: none | text: indigo vat")
    assert sum(a * b for a, b in zip(alum, same, strict=True)) == pytest.approx(1.0)
    assert sum(a * b for a, b in zip(alum, other, strict=True)) == pytest.approx(0.0)


async def test_the_golden_questions_find_their_seeded_claims_above_the_floors() -> None:
    async with rolled_back() as session:
        data = load_seed_claims()
        assert (await seed_claims(session, data))["unresolvedSlugs"] == []
        await store_seed_passages(session, data)
        await embed_pending(session, word_embedder, batch_size=500)
        retriever = StoredKnowledgeSearch(session, embed=word_embedder)
        report = await evaluate_golden(
            retriever, GOLDEN_QUESTIONS, claim_id=lambda key: seed_id("claim", key)
        )
        summary = report.as_dict()
        assert summary["questions"] == len(GOLDEN_QUESTIONS), summary
        assert report.recall_at_depth is not None and report.recall_at_depth >= RECALL_AT_5_FLOOR, summary
        assert report.mean_reciprocal_rank is not None and report.mean_reciprocal_rank >= MRR_FLOOR, summary
