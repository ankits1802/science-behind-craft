import uuid
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.crafts import EMBEDDING_DIMENSIONS
from app.research.planning import MODE_POLICIES
from app.research.retrieval import (
    HIDDEN_CLAIM_STATUSES,
    MODE_CLAIM_LEVELS,
    MODE_CLAIM_STATUSES,
    KnowledgeQuery,
    KnowledgeRetriever,
)
from app.retrieval.hybrid import CORPUS_TIER, StoredKnowledgeSearch
from app.retrieval.statements import (
    RANKING_DEPTH,
    CraftScope,
    chunk_conditions,
    chunk_lexical_ranking,
    chunk_vector_ranking,
    claim_conditions,
    claim_lexical_ranking,
    claim_vector_ranking,
)

from ..craft_fixtures import FixedEmbedder

CRAFT = uuid.uuid5(uuid.NAMESPACE_URL, "test-craft/Qorvane-Ikat")
FAMILY = uuid.uuid5(uuid.NAMESPACE_URL, "test-sub/qorvane")
SCOPE = CraftScope(craft_id=CRAFT, sub_category_id=FAMILY)
VECTOR = [0.0] * EMBEDDING_DIMENSIONS


def compiled(statement: Select[Any]) -> tuple[str, dict[str, Any]]:
    result = statement.compile(dialect=postgresql.dialect())
    return " ".join(result.string.split()), dict(result.params)


def params_with(params: dict[str, Any], prefix: str) -> list[Any]:
    return [value for name, value in sorted(params.items()) if name.startswith(prefix)]


def test_verified_mode_reads_approved_reviewed_and_verified_claims_only() -> None:
    sql, params = compiled(claim_lexical_ranking(claim_conditions(SCOPE, mode="VERIFIED"), "alum"))
    assert params_with(params, "status_") == [["APPROVED"]]
    assert params_with(params, "evidenceLevel_") == [["VERIFIED", "REVIEWED"]]
    assert '"Claim".status IN' in sql and '"Claim"."evidenceLevel" IN' in sql


def test_hybrid_mode_reads_every_level_and_every_status_but_the_hidden_ones() -> None:
    _, params = compiled(claim_lexical_ranking(claim_conditions(SCOPE, mode="HYBRID"), "alum"))
    assert params_with(params, "status_") == [["PROPOSED", "IN_REVIEW", "APPROVED"]]
    assert params_with(params, "evidenceLevel_") == [["VERIFIED", "REVIEWED", "PROVISIONAL", "HYPOTHESIS"]]
    assert HIDDEN_CLAIM_STATUSES == ("DRAFT", "REJECTED", "RETRACTED")


def test_every_mode_has_claim_filters_and_only_the_corpus_modes_read_chunks() -> None:
    assert set(MODE_CLAIM_LEVELS) == set(MODE_CLAIM_STATUSES) == set(MODE_POLICIES)
    assert [mode for mode, policy in MODE_POLICIES.items() if CORPUS_TIER in policy.tiers] == [
        "HYBRID",
        "DEEP",
    ]


def test_claims_are_scoped_to_the_craft_and_its_family_and_need_a_visible_source() -> None:
    sql, params = compiled(claim_lexical_ranking(claim_conditions(SCOPE, mode="HYBRID"), "alum"))
    assert '"Concept"."craftId" = %(craftId_1)s::UUID OR "Concept"."craftId" IS NULL' in sql
    assert '"Concept"."subCategoryId" = %(subCategoryId_1)s::UUID' in sql
    assert params["craftId_1"] == CRAFT and params["subCategoryId_1"] == FAMILY
    assert '"Claim"."subjectType" = %(subjectType_1)s::VARCHAR' in sql
    assert params["subjectType_1"] == "CONCEPT" and params["subjectType_2"] == "EDGE"
    assert '"ConceptEdge"."srcId" IN' in sql and '"ConceptEdge"."dstId" IN' in sql
    assert '"ClaimSource"."claimId" = "Claim".id' in sql
    assert '"Source".sensitivity != %(sensitivity_3)s' in sql
    assert params_with(params, "sensitivity_") == ["OPEN", "OPEN", "RESTRICTED"]


def test_a_craft_without_a_family_reads_only_its_own_concepts() -> None:
    sql, _ = compiled(claim_lexical_ranking(claim_conditions(CraftScope(CRAFT, None), mode="HYBRID"), "alum"))
    assert "subCategoryId" not in sql


def test_facets_filter_the_concept_types() -> None:
    conditions = claim_conditions(SCOPE, mode="HYBRID", facets=("MATERIAL", "MECHANISM"))
    sql, params = compiled(claim_lexical_ranking(conditions, "alum"))
    assert '"Concept".type IN' in sql
    assert params_with(params, "type_") == [["MATERIAL", "MECHANISM"]]


def test_the_lexical_ranking_matches_the_or_query_and_orders_by_cover_density() -> None:
    sql, params = compiled(claim_lexical_ranking(claim_conditions(SCOPE, mode="HYBRID"), "alum | madder"))
    assert sql.startswith('SELECT "Claim".id FROM "Claim" WHERE')
    assert '"Claim".tsv @@ to_tsquery(%(to_tsquery_1)s::REGCONFIG, %(to_tsquery_2)s::VARCHAR)' in sql
    assert sql.endswith(
        'ORDER BY ts_rank_cd("Claim".tsv, to_tsquery(%(to_tsquery_1)s::REGCONFIG, %(to_tsquery_2)s::VARCHAR))'
        ' DESC, "Claim".id LIMIT %(param_1)s::INTEGER'
    )
    assert params["to_tsquery_1"] == "english" and params["to_tsquery_2"] == "alum | madder"
    assert params["param_1"] == RANKING_DEPTH == 30


def test_the_vector_ranking_is_an_exact_cosine_scan_of_the_scoped_rows() -> None:
    sql, params = compiled(claim_vector_ranking(claim_conditions(SCOPE, mode="HYBRID"), VECTOR, depth=7))
    assert sql.startswith('WITH scoped AS MATERIALIZED (SELECT "Claim".id AS id, "Claim".embedding <=> ')
    assert '"Claim".embedding IS NOT NULL' in sql
    assert sql.endswith(
        "SELECT scoped.id FROM scoped ORDER BY scoped.distance, scoped.id LIMIT %(param_1)s::INTEGER"
    )
    assert params["param_1"] == 7


def test_chunks_come_from_sources_cited_by_scoped_claims_within_the_reader_acl() -> None:
    conditions = chunk_conditions(SCOPE, mode="HYBRID", acls=("PUBLIC",))
    sql, params = compiled(chunk_lexical_ranking(conditions, "alum"))
    assert sql.startswith('SELECT "Chunk".id FROM "Chunk" WHERE "Chunk"."sourceId" IN (SELECT "Source".id')
    assert '"ClaimSource"."claimId" IN (SELECT "Claim".id FROM "Claim"' in sql
    assert '"Chunk".acl IN' in sql and params_with(params, "acl_") == [["PUBLIC"]]
    assert '"Chunk".sensitivity != ' in sql
    assert params_with(params, "sensitivity_").count("RESTRICTED") == 3
    vector_sql, _ = compiled(chunk_vector_ranking(conditions, VECTOR))
    assert vector_sql.startswith(
        'WITH scoped AS MATERIALIZED (SELECT "Chunk".id AS id, "Chunk".embedding <=> '
    )


def test_the_query_contract_refuses_repeats_and_out_of_range_limits() -> None:
    with pytest.raises(ValueError):
        KnowledgeQuery(craft_slug="Kutch-Ajrakh", text="alum", mode="HYBRID", facets=("MATERIAL", "MATERIAL"))
    with pytest.raises(ValueError):
        KnowledgeQuery(craft_slug="Kutch-Ajrakh", text="alum", mode="HYBRID", limit=51)
    with pytest.raises(ValueError):
        KnowledgeQuery(craft_slug="Kutch-Ajrakh", text="alum", mode="HYBRID", chunk_acls=("EVERYONE",))
    query = KnowledgeQuery.model_validate({"craftSlug": "Kutch-Ajrakh", "text": " alum ", "mode": "VERIFIED"})
    assert query.text == "alum" and query.chunk_acls == ("PUBLIC",) and query.limit == 12


def test_the_stored_search_implements_the_retriever_contract() -> None:
    search = StoredKnowledgeSearch(cast(AsyncSession, object()), embed=FixedEmbedder())
    assert isinstance(search, KnowledgeRetriever)
