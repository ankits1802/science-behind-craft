import pytest

from app.core.errors import InvalidInput
from app.retrieval.fusion import RRF_K, VOTING_DEPTH, reciprocal_rank_fusion
from app.retrieval.text import TSQUERY_MAX_TERMS, document_text, or_tsquery, query_text


def test_the_fusion_constant_is_the_published_sixty() -> None:
    assert RRF_K == 60


def test_fused_scores_add_one_over_k_plus_rank_from_each_ranking() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["c", "a"]])
    assert [item.key for item in fused] == ["a", "c", "b"]
    scores = {item.key: item.score for item in fused}
    assert scores["a"] == pytest.approx(0.032522475, abs=1e-9)
    assert scores["c"] == pytest.approx(0.032266459, abs=1e-9)
    assert scores["b"] == pytest.approx(0.016129032, abs=1e-9)
    assert {item.key: item.ranks for item in fused} == {"a": (1, 2), "b": (2, None), "c": (3, 1)}


def test_a_small_constant_weights_the_top_ranks_harder() -> None:
    fused = reciprocal_rank_fusion([["a", "b"]], k=1)
    assert [(item.key, item.score) for item in fused] == [("a", 0.5), ("b", pytest.approx(1 / 3))]


def test_equal_scores_fall_back_to_the_best_rank_then_the_key() -> None:
    assert [item.key for item in reciprocal_rank_fusion([["y"], ["x"]])] == ["x", "y"]
    fused = reciprocal_rank_fusion([["p", "q", "r"], ["r", "s"]], k=1)
    assert [item.key for item in fused] == ["r", "p", "q", "s"]


def test_no_rankings_fuse_to_nothing() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


def test_a_ranking_that_repeats_an_item_is_refused() -> None:
    with pytest.raises(InvalidInput, match="lists 'a' twice"):
        reciprocal_rank_fusion([["a", "b", "a"]])


def test_a_fusion_constant_below_one_is_refused() -> None:
    with pytest.raises(InvalidInput):
        reciprocal_rank_fusion([["a"]], k=0)


def ranking(prefix: str, length: int, placed: dict[int, str]) -> list[str]:
    return [placed.get(rank, f"{prefix}{rank}") for rank in range(1, length + 1)]


def test_each_ranking_votes_with_its_first_thirty_as_before_the_pool_widened() -> None:
    assert VOTING_DEPTH == 30
    words = ranking("w", 60, {1: "gold", 37: "near"})
    vectors = ranking("v", 60, {1: "gold", 10: "near"})
    entities = ranking("e", 60, {6: "near"})
    fused = {item.key: item for item in reciprocal_rank_fusion([words, vectors, entities])}
    assert fused["gold"].voted == pytest.approx(2 / 61, abs=1e-12)
    assert fused["near"].voted == pytest.approx(1 / 70 + 1 / 66, abs=1e-12)
    assert fused["near"].score == pytest.approx(1 / 97 + 1 / 70 + 1 / 66, abs=1e-12)
    assert fused["near"].score > fused["gold"].score
    order = [item.key for item in reciprocal_rank_fusion([words, vectors, entities])]
    assert order.index("gold") < order.index("near")


def test_an_item_found_only_below_the_voting_depth_follows_every_voted_item() -> None:
    first = ranking("a", 35, {30: "shallow", 31: "deep"})
    second = ranking("b", 35, {31: "deep"})
    fused = reciprocal_rank_fusion([first, second])
    keys = [item.key for item in fused]
    deep = next(item for item in fused if item.key == "deep")
    assert (deep.voted, deep.score) == (0.0, pytest.approx(2 / 91, abs=1e-12))
    assert keys.index("shallow") < keys.index("deep")
    assert all(item.voted > 0 for item in fused[: keys.index("deep")])


def test_a_voting_depth_below_one_is_refused() -> None:
    with pytest.raises(InvalidInput, match="at least its first item"):
        reciprocal_rank_fusion([["a"]], voting_depth=0)


def test_the_text_query_ors_distinct_words_of_three_or_more_characters_then_the_short_ones() -> None:
    query = or_tsquery("What mordant is used in Ajrakh? Ajrakh uses alum; pH 4")
    assert query == "what | mordant | used | ajrakh | uses | alum | is | in | ph"


def test_the_text_query_folds_width_and_case_and_drops_operators() -> None:
    assert or_tsquery("ＡＬＵＭ & (madder) | !iron:*") == "alum | madder | iron"


def test_a_question_without_latin_words_has_no_text_query() -> None:
    assert or_tsquery("अजरख में फिटकरी") is None
    assert or_tsquery("is it ok?") is None


def test_the_text_query_keeps_at_most_forty_terms() -> None:
    words = [f"word{n:02d}" for n in range(45)]
    terms = or_tsquery(" ".join(words))
    assert terms is not None
    assert terms.split(" | ") == words[:TSQUERY_MAX_TERMS]
    assert TSQUERY_MAX_TERMS == 40


def test_queries_and_documents_carry_the_retrieval_task_prefixes() -> None:
    assert query_text("  dye\n fast ") == "task: search result | query: dye fast"
    assert document_text("Alum  fixes\nmadder.") == "title: none | text: Alum fixes madder."
    assert document_text("x", title=" Wood  Handbook ") == "title: Wood Handbook | text: x"
