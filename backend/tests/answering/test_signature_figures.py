from types import SimpleNamespace
from typing import Any

import pytest

from app.core.config import Settings
from app.research.blocks_signature import SIGNATURE_KINDS
from app.research.explainer import BUILT_BLOCK_KINDS, BUILT_FIGURE_KINDS
from app.services import signature_blocks
from app.services.answer_events import CitedClaims
from app.services.answer_lede import LedeTools
from app.services.curation_keys import curated_id
from app.services.knowledge_view import ClaimView
from app.services.signature_blocks import SignatureFigures, ranked_facts, signature_block
from app.services.signature_rules import FigureEvidence

from .signature_evidence import (
    AJRAKH,
    AJRAKH_REF,
    INDIGO_CID,
    INDIGO_CLAIMS,
    MORDANT_CLAIMS,
    ajrakh_compounds,
    enrichment,
    evidence,
    figure_of,
    figured_lede,
    plain_lede,
    seed_view,
)

INDIGO_WHITE_CLAIM = "seed-3965c8f733d2c1a997d5"


def claim(key: str) -> str:
    return str(seed_view(key).id) if key.startswith("seed-") else str(curated_id(AJRAKH, key))


def text_of(key: str) -> str:
    (view,) = evidence(AJRAKH, (key,)).views.values()
    return view.text


def claims_of(sentence: Any) -> set[str]:
    return {citation.claim_id for citation in sentence.citations}


def plain_view(text: str, number: int, *, level: str = "PROVISIONAL") -> ClaimView:
    claim_id = curated_id("Test-Craft", f"C{number:03d}")
    citation = {
        "id": str(curated_id("Test-Craft", "quote", str(number))),
        "claimId": str(claim_id),
        "sourceId": str(curated_id("Test-Craft", "S01")),
        "quote": text,
        "locator": None,
        "context": None,
        "evidence": "QUOTED",
        "level": level,
    }
    return ClaimView(claim_id, text, level, "MECHANISM", None, citations=[citation])


def built(kind: str, *texts: str) -> Any:
    views = {view.id: view for view in (plain_view(text, n) for n, text in enumerate(texts, start=1))}
    cited = CitedClaims(views=views, sources={})
    return signature_block(kind, FigureEvidence(ranked_facts(cited)))


def test_the_figures_are_off_until_the_setting_turns_them_on(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings.model_fields["signature_figures_enabled"].default is False
    assert LedeTools().figures is None
    monkeypatch.setattr(
        signature_blocks, "get_settings", lambda: SimpleNamespace(signature_figures_enabled=False)
    )
    assert signature_blocks.signature_figures(sessions=None) is None
    monkeypatch.setattr(
        signature_blocks, "get_settings", lambda: SimpleNamespace(signature_figures_enabled=True)
    )
    assert isinstance(signature_blocks.signature_figures(sessions=None), SignatureFigures)


def test_the_four_kinds_are_built_as_lede_figures_and_never_as_section_blocks() -> None:
    assert BUILT_FIGURE_KINDS == SIGNATURE_KINDS
    assert not set(BUILT_FIGURE_KINDS) & set(BUILT_BLOCK_KINDS)


def test_the_ajrakh_mordant_bath_shows_alum_red_and_iron_black_from_their_own_claims() -> None:
    bath = figure_of("mordant_bath", AJRAKH, MORDANT_CLAIMS)
    assert (bath.dye, bath.fibre) == ("madder", "cotton")
    assert [(s.mordant, s.colour) for s in bath.swatches] == [("alum", "red"), ("iron", "black")]
    assert [claims_of(s.sentence) for s in bath.swatches] == [{claim("C093")}, {claim("C078")}]
    assert [s.sentence.text for s in bath.swatches] == [text_of("C093"), text_of("C078")]
    assert [s.sentence.id for s in bath.swatches] == ["lede.figure.1", "lede.figure.2"]


def test_without_a_dye_named_by_a_swatch_sentence_no_bath_is_drawn() -> None:
    keys = tuple(key for key in MORDANT_CLAIMS if key != "C093")
    held = signature_block("mordant_bath", FigureEvidence(ranked_facts(evidence(AJRAKH, keys))))
    assert held is None


def test_the_ajrakh_indigo_vat_shows_both_forms_its_lift_dips_and_contents() -> None:
    vat = figure_of("indigo_vat", AJRAKH, INDIGO_CLAIMS, ajrakh_compounds())
    assert vat.vat == "FERMENTED"
    assert claims_of(vat.lift) == {claim("C086")}
    keto, leuco = vat.forms
    assert (keto.form, keto.name, keto.colour, keto.soluble) == ("KETO", "indigo blue", "blue", False)
    assert (leuco.form, leuco.name, leuco.colour, leuco.soluble) == ("LEUCO", "indigo white", "white", True)
    assert claims_of(keto.sentence) == claims_of(leuco.sentence) == {claim(INDIGO_WHITE_CLAIM)}
    assert keto.compound is not None and keto.compound.pubchem_cid == INDIGO_CID
    assert keto.compound.formula == "C16H10N2O2"
    assert leuco.compound is None
    assert [(d.dips, d.stated, d.shade) for d in vat.dips] == [(3, "three or four times", "darkest")]
    assert claims_of(vat.dips[0].sentence) == {claim("C087")}
    assert [c.name for c in vat.contents] == [
        "lime",
        "dates",
        "soda",
        "jaggery",
        "sagikhar",
        "casatoria seeds",
    ]
    assert [claims_of(c.sentence) for c in vat.contents] == [
        {claim("C085")},
        {claim("seed-d9b4aea0626d66ccdb60")},
        {claim("seed-d9b4aea0626d66ccdb60")},
        {claim("C085")},
        {claim("C085")},
        {claim("C083")},
    ]
    assert list(vat.direct_source_ids()) == [keto.compound.source_id]


def test_a_vat_without_the_green_to_blue_lift_is_not_drawn() -> None:
    keys = tuple(key for key in INDIGO_CLAIMS if key not in {"C086", "seed-86fcd25c654d7a0e0079"})
    cited = evidence(AJRAKH, keys)
    assert signature_block("indigo_vat", FigureEvidence(ranked_facts(cited))) is None


def test_the_lost_wax_steps_follow_casting_order_and_name_the_metal() -> None:
    cast = built(
        "lost_wax",
        "Molten brass is poured into the mould.",
        "A wax model is shaped over a clay core.",
        "The clay mould is broken to free the casting.",
        "The model is coated with layers of clay.",
        "Heated, the wax melts out through a channel.",
    )
    assert cast.metal == "brass"
    assert [step.step for step in cast.steps] == ["MODEL", "JACKET", "BURNOUT", "POUR", "BREAK_OUT"]
    assert cast.steps[0].sentence.text == "A wax model is shaped over a clay core."


def test_metal_melting_is_not_the_wax_burning_out() -> None:
    cast = built(
        "lost_wax",
        "These casters melt metal in the lost wax technique.",
        "Molten brass is poured into the mould.",
    )
    assert cast is None


def test_the_firing_shows_each_atmosphere_its_colour_and_a_stated_temperature() -> None:
    fired = built(
        "firing",
        "Fired with plenty of air, the clay turns red.",
        "Starved of air in the kiln, the clay turns black.",
        "The kiln reaches 800 degrees.",
    )
    assert fired.body == "clay"
    assert [(a.atmosphere, a.colour) for a in fired.atmospheres] == [
        ("OXIDISING", "red"),
        ("REDUCING", "black"),
    ]
    assert fired.temperature is not None and fired.temperature.stated == "800 degrees"


@pytest.mark.parametrize(
    ("kind", "texts"),
    [
        ("mordant_bath", ("With alum, madder dyes cotton crimson.", "With iron, madder dyes cotton grey.")),
        ("mordant_bath", ("Lime discharges alum, so no red develops on cotton dyed in madder.",)),
        ("firing", ("The clay is fired in a kiln.",)),
        ("lost_wax", ("A wax model is shaped over a clay core.",)),
    ],
)
def test_values_no_cited_sentence_states_are_never_shown(kind: str, texts: tuple[str, ...]) -> None:
    assert built(kind, *texts) is None


def test_a_hypothesis_is_never_offered_to_a_figure() -> None:
    view = plain_view("With alum, madder dyes cotton red.", 1, level="HYPOTHESIS")
    assert ranked_facts(CitedClaims(views={view.id: view}, sources={})) == ()


async def test_the_lede_takes_the_figure_its_terms_call_for_with_the_figure_sources() -> None:
    lede = plain_lede()
    assert [span.term_key for s in lede.sentences for span in s.terms] == ["alum"]
    figured = await figured_lede(lede)
    figure = figured.lede.figure
    assert figure is not None and figure.kind == "mordant_bath"
    assert figured.lede.sentences == lede.sentences
    assert set(figure.cited_source_ids()) == set(figured.sources)
    assert [span.term_key for span in figure.swatches[1].sentence.terms] == ["kut"]


async def test_the_question_s_terms_come_before_the_lede_s() -> None:
    lede = plain_lede()
    figured = await figured_lede(lede, question="How does indigo turn blue?", keys=INDIGO_CLAIMS)
    assert figured.lede.figure is not None and figured.lede.figure.kind == "indigo_vat"
    assert set(figured.sources) == set(figured.lede.figure.cited_source_ids())


async def test_a_lede_without_a_signature_term_keeps_no_figure() -> None:
    marked = plain_lede()
    lede = marked.model_copy(
        update={"sentences": [s.model_copy(update={"terms": []}) for s in marked.sentences]}
    )
    figured = await figured_lede(lede, question="Who wears Ajrakh?")
    assert figured.lede == lede and figured.sources == {}


async def test_a_failing_compound_read_leaves_the_lede_as_it_was() -> None:
    async def broken(craft: Any) -> Any:
        raise RuntimeError("the database went away")

    lede = plain_lede()
    figures = SignatureFigures(compounds=broken)
    figured = await figures.figured(
        lede,
        question="How does indigo turn blue?",
        craft=None,
        evidence=evidence(AJRAKH, INDIGO_CLAIMS),
        enrichment=enrichment(),
    )
    assert figured.lede == lede
    figured = await figures.figured(
        lede,
        question="How does indigo turn blue?",
        craft=AJRAKH_REF,
        evidence=evidence(AJRAKH, INDIGO_CLAIMS),
        enrichment=enrichment(),
    )
    assert figured.lede == lede and figured.sources == {}


def test_a_swatch_is_preferred_for_what_its_own_claim_says_not_for_a_quote_naming_the_dye() -> None:
    kalamkari = "seed-d40e84ae9b0db76e8d9a"
    bath = figure_of("mordant_bath", AJRAKH, (kalamkari, *MORDANT_CLAIMS))
    assert [claims_of(s.sentence) for s in bath.swatches] == [{claim("C093")}, {claim("C078")}]
