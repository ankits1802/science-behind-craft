import pytest
from pydantic import ValidationError

from app.research.blocks import ProseBlock
from app.research.blocks_matter import ReactionPlayerBlock, StepColour
from app.research.citations import Citation
from app.research.knowledge_pieces import piece_content_hash
from app.science.reaction_colours import step_colours
from app.science.reaction_player import reaction_player, reaction_player_problems
from app.services.claim_ledger import ClaimLedger

from ..contracts.golden import golden_json
from .golden_process import GOLDEN, golden_records

INDIGO_LIFT = (
    "At first bright green, the cloth rapidly becomes blue as oxygen meets the dye particles on the fibres."
)
KUT_BLACK = (
    "When printed onto the harde treated cloth kut develops a deep fast chocolate-black colour as the iron "
    "particles in the kut paste oxidise with the tannic acid."
)
VAT_NAMES = (
    "On oxidisation, indigo white is converted into granules of indigo blue which has then to be reduced "
    "through fermentation into soluble indigo white, before dyeing can begin."
)
MADDER_RED = (
    "This dye extracted from these long thin roots links to the alum mordant on the cotton fibres and develops "
    "red area of a design, where Pa, Gach pastes have been printed."
)


def cited(quote: str, number: int = 1) -> Citation:
    return Citation(
        id=f"c{number}",
        claim_id=f"claim-{number}",
        source_id="s1",
        quote=quote,
        locator=None,
        context=None,
        evidence="QUOTED",
        level="PROVISIONAL",
    )


def sides(quote: str) -> list[tuple[str, str, str]]:
    return [(c.side, c.colour, c.stated) for c in step_colours([cited(quote)])]


def golden_steps() -> list[dict]:
    stages = [stage for process in golden_json(GOLDEN)["processes"] for stage in process["stages"]]
    return [(stage, reaction) for stage in stages for reaction in stage["reactions"]]


def player() -> ReactionPlayerBlock:
    block = reaction_player(golden_records(), block_id="s4.b2")
    assert block is not None
    return block


def test_a_colour_change_the_source_states_gives_the_step_its_two_sides() -> None:
    assert sides(INDIGO_LIFT) == [
        ("BEFORE", "GREEN", "At first bright green, the cloth rapidly becomes blue"),
        ("AFTER", "BLUE", "At first bright green, the cloth rapidly becomes blue"),
    ]


def test_a_colour_a_step_develops_is_its_after_side_named_by_the_last_part_of_a_compound_word() -> None:
    assert sides(KUT_BLACK) == [("AFTER", "BLACK", "develops a deep fast chocolate-black")]
    assert sides(MADDER_RED) == [("AFTER", "RED", "develops red")]


def test_colour_words_used_as_names_or_denied_give_no_colour() -> None:
    assert sides(VAT_NAMES) == []
    assert sides("The cloth does not develop red without alum.") == []
    assert sides("Indigo is blue.") == []


def test_a_step_colour_must_be_named_by_words_a_cited_quote_says() -> None:
    with pytest.raises(ValidationError):
        StepColour(side="AFTER", colour="RED", stated="becomes blue", citations=[cited(INDIGO_LIFT)])
    with pytest.raises(ValidationError):
        StepColour(side="AFTER", colour="BLUE", stated="turns blue at once", citations=[cited(INDIGO_LIFT)])


def test_each_step_names_its_stage_and_the_conditions_its_stage_states() -> None:
    steps = player().steps
    assert [step.stage for step in steps] == [
        "Kut (iron-black printing)",
        "Red dyeing (rang) with madder or alizarin",
    ]
    assert [[(c.label, c.stated) for c in step.conditions] for step in steps] == [
        [("Fermenting the iron paste", "ten to fifteen days")],
        [("Red dye bath", "up to four hours")],
    ]


def test_the_alizarin_lake_turns_red_as_its_madder_quote_says_and_iron_acetate_states_no_colour() -> None:
    iron, lake = player().steps
    assert iron.colours == []
    assert [(c.side, c.colour, c.stated) for c in lake.colours] == [("AFTER", "RED", "develops red")]


def test_the_notes_are_each_reaction_s_stored_claims_once_each_in_reading_order() -> None:
    block = player()
    expected = [
        (str(reaction["id"]), claim["text"]) for _, reaction in golden_steps() for claim in reaction["claims"]
    ]
    assert [(str(note.reaction_id), note.sentence.text) for note in block.notes] == expected
    assert [note.sentence.id for note in block.notes] == ["s4.b2.1", "s4.b2.2", "s4.b2.3", "s4.b2.4"]
    assert [s.id for s in block.cited_sentences()] == [note.sentence.id for note in block.notes]


def test_a_player_built_from_the_rows_matches_them_and_an_edited_note_does_not() -> None:
    block = player()
    assert reaction_player_problems(block, golden_records()) == []
    note = block.notes[0]
    edited = note.model_copy(update={"sentence": note.sentence.model_copy(update={"text": "Iron is red."})})
    problems = reaction_player_problems(block.model_copy(update={"notes": [edited]}), golden_records())
    assert problems == [f"note s4.b2.1 is not a stored claim of reaction {note.reaction_id}"]


def test_a_player_stored_before_steps_had_details_still_reads_hashes_alike_and_holds() -> None:
    payload = player().model_dump(mode="json", by_alias=True)
    old = {**payload, "notes": [], "steps": [_plain_step(step) for step in payload["steps"]]}
    plain = {key: value for key, value in old.items() if key != "notes"}
    stored = ReactionPlayerBlock.model_validate(plain)
    assert stored.model_dump(mode="json", by_alias=True) == plain
    assert piece_content_hash(stored) == piece_content_hash(ReactionPlayerBlock.model_validate(old))
    assert reaction_player_problems(stored, golden_records()) == []


def test_a_note_the_page_already_shows_goes_and_the_steps_stay() -> None:
    block = player()
    shown = block.notes[0].sentence.model_dump(mode="json", by_alias=True)
    prose = ProseBlock(
        id="s1.b1", kind="prose", version=1, reuse=None, sentences=[{**shown, "id": "s1.b1.1"}]
    )
    sources = {
        sid: ref.model_dump(mode="json", by_alias=True) for sid, ref in golden_records().sources.items()
    }
    ledger = ClaimLedger()
    ledger.admit("s1", [prose], sources)
    (kept,) = ledger.admit("s2", [block], sources)
    assert [step.reaction_id for step in kept.steps] == [step.reaction_id for step in block.steps]
    assert [note.sentence.text for note in kept.notes] == [note.sentence.text for note in block.notes[1:]]


def _plain_step(step: dict) -> dict:
    return {key: value for key, value in step.items() if key not in {"stage", "conditions", "colours"}}
