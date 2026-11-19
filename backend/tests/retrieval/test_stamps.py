import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models import Chunk, Claim, KnowledgePiece
from app.models.crafts import EMBEDDING_DIMENSIONS
from app.retrieval.indexing import _vector_values
from app.retrieval.stamps import made_by_current_model, needs_vector
from app.retrieval.statements import (
    CraftScope,
    chunk_conditions,
    chunk_vector_ranking,
    claim_conditions,
    claim_vector_ranking,
)

SCOPE = CraftScope(craft_id=uuid.uuid5(uuid.NAMESPACE_URL, "test-craft/Qorvane-Ikat"), sub_category_id=None)
VECTOR = [0.0] * EMBEDDING_DIMENSIONS
CURRENT = "(SELECT kv_embedding_model() AS kv_embedding_model_1)"


def sql_of(statement: Any) -> str:
    return " ".join(str(statement.compile(dialect=postgresql.dialect())).split())


def test_the_claim_vector_ranking_reads_only_vectors_of_the_routes_current_model() -> None:
    sql = sql_of(claim_vector_ranking(claim_conditions(SCOPE, mode="HYBRID"), VECTOR))
    assert f'"Claim"."embeddingModel" = {CURRENT}' in sql
    assert '"Claim".embedding IS NOT NULL' in sql


def test_the_chunk_vector_ranking_reads_only_vectors_of_the_routes_current_model() -> None:
    sql = sql_of(chunk_vector_ranking(chunk_conditions(SCOPE, mode="HYBRID", acls=("PUBLIC",)), VECTOR))
    assert f'"Chunk"."embeddingModel" = {CURRENT}' in sql


def test_a_row_needs_a_vector_when_it_has_none_or_another_models() -> None:
    sql = sql_of(select(Claim.id).where(needs_vector(Claim.embedding, Claim.embeddingModel)))
    assert '"Claim".embedding IS NULL OR' in sql
    assert f'"Claim"."embeddingModel" IS DISTINCT FROM {CURRENT}' in sql


def test_a_current_vector_is_one_stamped_with_the_routes_model() -> None:
    sql = sql_of(select(Chunk.id).where(made_by_current_model(Chunk.embeddingModel)))
    assert sql.endswith(f'WHERE "Chunk"."embeddingModel" = {CURRENT}')


def test_claims_and_chunks_are_stamped_as_they_are_written_and_pieces_are_not() -> None:
    vector = [1.0] * 3
    claim = _vector_values(Claim, vector)
    assert set(claim) == {"embedding", "embeddingModel"} and claim["embedding"] == vector
    assert "SELECT kv_embedding_model()" in sql_of(claim["embeddingModel"])
    assert set(_vector_values(Chunk, vector)) == {"embedding", "embeddingModel"}
    assert _vector_values(KnowledgePiece, vector) == {"embedding": vector}
