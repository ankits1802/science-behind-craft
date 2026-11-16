import pytest

from app.core import errors
from app.providers import router
from app.providers.base import ProviderError
from app.research.fetcher import FetchRefused
from app.research.quotes import (
    figures_in,
    normalise_quote_text,
    quote_occurs,
    quote_overlap,
    trivial_quote,
    unsupported_figures,
)
from app.research.vocabulary import LEVEL_ORDER, weakest_level


def test_quote_text_is_folded_for_comparison_only() -> None:
    raw = "Mor-\n  dant  “fixing”­ of the ﬁbre in H₂O"
    assert normalise_quote_text(raw) == 'Mordant "fixing" of the fibre in H2O'


def test_a_quote_must_occur_verbatim_after_normalisation() -> None:
    page = "The dye-\nstuff was “fixed” with alum at about 60 °C."
    assert quote_occurs('dye-stuff was "fixed"', page)
    assert quote_occurs("fixed” with alum at about 60 °C", page)
    assert not quote_occurs("Dyestuff was", page)
    assert not quote_occurs("fixed with iron", page)
    assert not quote_occurs("   ", page)


def test_a_quote_starts_and_ends_on_whole_words_and_whole_numbers() -> None:
    hot = "The kiln is heated to 1500 °C over 1.5 hours with 11 workers."
    assert not quote_occurs("50", hot)
    assert not quote_occurs("500 °C", hot)
    assert not quote_occurs("1 workers", hot)
    assert not quote_occurs("5 hours", hot)
    assert not quote_occurs("1", hot)
    assert not quote_occurs("eated to 1500", hot)
    assert quote_occurs("heated to 1500 °C", hot)
    assert quote_occurs("over 1.5 hours", hot)
    assert quote_occurs("1500 °C over", hot)
    assert quote_occurs("with 11 workers.", hot)


def test_a_quote_shorter_than_twenty_characters_after_folding_is_trivial() -> None:
    assert trivial_quote("a")
    assert trivial_quote("the")
    assert trivial_quote("alum   is   a   mordant")
    assert trivial_quote("x" * 19)
    assert not trivial_quote("x" * 20)
    assert not trivial_quote("alum is the mordant used")


def test_overlap_is_the_share_of_a_sentences_content_words_its_quotes_carry() -> None:
    assert quote_overlap("Arsenic is the mordant.", ["Alum is applied to the cloth before dyeing"]) == 0.0
    assert quote_overlap("Alum fixes dye on cotton.", ["alum fixes the dye", "on the cotton cloth"]) == 1.0
    assert quote_overlap("Mordants bind alizarin dyes.", ["a mordant binds"]) == 0.5
    assert quote_overlap("It is so.", ["anything at all here"]) == 0.0


def test_figures_are_formulas_and_numbers_outside_them() -> None:
    sentence = "Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2 at 62–64 °C over 1,200 m in Ajrakh, pH 7.5."
    assert figures_in(sentence) == ["CH3COOH", "Fe(CH3COO)2", "H2", "2", "62", "64", "1200", "7.5"]


def test_every_figure_must_appear_in_a_cited_text() -> None:
    assert unsupported_figures("Water boils at 100 °C.", ["water boils at 100 degrees"]) == []
    assert unsupported_figures("Heat it to 120 °C.", ["Heat it to 100 °C."]) == ["120"]
    assert unsupported_figures("It takes 2 hours.", ["H2O is used"]) == ["2"]
    assert unsupported_figures("About 1,200 artisans.", ["about 1200 artisans"]) == []
    assert unsupported_figures("Water is H2O.", ["CO2 and H2O"]) == []
    assert unsupported_figures("No figures here.", []) == []


def test_levels_combine_to_the_weakest() -> None:
    assert list(LEVEL_ORDER) == ["VERIFIED", "REVIEWED", "PROVISIONAL", "HYPOTHESIS"]
    assert weakest_level(["VERIFIED", "PROVISIONAL", "REVIEWED"]) == "PROVISIONAL"
    assert weakest_level(["HYPOTHESIS", "VERIFIED"]) == "HYPOTHESIS"
    with pytest.raises(errors.InvalidInput):
        weakest_level([])
    with pytest.raises(errors.InvalidInput):
        weakest_level(["UNAVAILABLE"])


def test_failure_kinds_either_move_on_or_stop() -> None:
    assert errors.NEXT_ROUTE_KINDS | errors.STOP_KINDS == errors.FAILURE_KINDS
    assert not errors.NEXT_ROUTE_KINDS & errors.STOP_KINDS
    assert router.STOP_KINDS is errors.STOP_KINDS


def test_provider_and_router_errors_join_the_shared_hierarchy() -> None:
    busy = ProviderError("busy", retryable=True, status=429, kind="rate_limit", retry_after=3)
    assert isinstance(busy, errors.ExternalFailure)
    assert isinstance(busy, errors.AppError)
    assert (busy.kind, busy.retryable, busy.status, busy.retry_after) == ("rate_limit", True, 429, 3)
    assert busy.tries_next
    assert not ProviderError("no", kind="refusal").tries_next
    assert ProviderError("plain").kind == "error"
    assert isinstance(router.RouterError("ceiling", "Budget reached"), errors.AppError)


def test_unknown_failure_kinds_and_reasons_are_refused() -> None:
    with pytest.raises(ValueError):
        errors.ExternalFailure("x", kind="timeout")
    with pytest.raises(ValueError):
        errors.Refused("", "no reason")
    with pytest.raises(ValueError):
        FetchRefused("https://example.org", "BLOCKED")


def test_a_fetch_refusal_is_a_refusal_with_its_reason() -> None:
    refusal = FetchRefused("https://169.254.169.254.nip.io/", "PRIVATE_ADDRESS", "metadata address")
    assert isinstance(refusal, errors.Refused)
    assert refusal.reason == "PRIVATE_ADDRESS"
    assert refusal.url == "https://169.254.169.254.nip.io/"
    assert str(refusal) == "Fetch refused (PRIVATE_ADDRESS): metadata address"
