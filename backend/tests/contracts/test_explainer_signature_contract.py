import pytest
from pydantic import ValidationError

from app.research.blocks_lede import LedeBlock
from app.research.blocks_signature import SIGNATURE_KINDS, SignatureBlock
from app.research.explainer import BlockEvent, LedeEvent
from app.services.curation_keys import curated_id

from ..answering.signature_evidence import (
    AJRAKH,
    DHOKRA,
    NIZAMABAD,
    built_figures,
    dossier_claims,
    figured_lede,
    plain_lede,
)
from .explainer_golden import citations_in, seed_citations
from .golden import dumped, golden_json, golden_text, reproduces

FIGURES = "explainer.signature.golden.json"
LEDE = "explainer.signature-lede.golden.json"
FIGURE_LIST = list[SignatureBlock]


def test_the_signature_goldens_are_reproduced_byte_for_byte() -> None:
    assert reproduces(FIGURE_LIST, FIGURES)
    assert reproduces(LedeBlock, LEDE)


def test_the_goldens_are_what_the_builders_make_from_the_stored_claims() -> None:
    assert dumped(FIGURE_LIST, built_figures()) == golden_text(FIGURES)


async def test_the_lede_golden_is_the_figured_lede_of_the_ajrakh_question() -> None:
    figured = await figured_lede(plain_lede())
    assert dumped(LedeBlock, figured.lede) == golden_text(LEDE)


def test_one_figure_of_each_kind_in_order() -> None:
    assert [figure["kind"] for figure in golden_json(FIGURES)] == list(SIGNATURE_KINDS)


def test_every_figure_quote_is_a_stored_quote_of_its_claim() -> None:
    stored = _stored_quotes()
    seeded = seed_citations()
    for cite in citations_in([golden_json(FIGURES), golden_json(LEDE)]):
        if cite["id"] in seeded:
            assert seeded[cite["id"]]["quote"] == cite["quote"]
        else:
            assert cite["quote"] in stored[cite["claimId"]]


def test_the_lede_event_carries_each_figure_and_a_section_never_does() -> None:
    lede = golden_json(LEDE)
    for figure in golden_json(FIGURES):
        event = LedeEvent.model_validate({"block": lede | {"figure": figure}})
        assert event.block.figure is not None and event.block.figure.kind == figure["kind"]
        with pytest.raises(ValidationError, match="not built yet"):
            BlockEvent.model_validate({"sectionId": "s1", "block": figure | {"id": "s1.b9"}})


def _stored_quotes() -> dict[str, list[str]]:
    quotes: dict[str, list[str]] = {}
    for slug in (AJRAKH, DHOKRA, NIZAMABAD):
        for key, claim in dossier_claims(slug).items():
            quotes[str(curated_id(slug, key))] = [quote["quote"] for quote in claim["quotes"]]
    return quotes
