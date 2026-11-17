import json
import uuid

from app.composer.candidates import compose_request
from app.composer.composer import ModelComposer
from app.composer.prompt import SECTION_SYSTEM_PROMPT, section_schema
from app.research.composition import ComposeFocus, StageOption

from ..planner.fakes import FakeModel
from .fixtures import ALUM_CLAIM_ID, QUESTION, pack, quote, replacements, section_reply, sentence

KUT = uuid.UUID("77bf953a-03a3-54c3-a1bb-37ac338266df")
PA = uuid.UUID("9a3c214f-0000-4000-8000-000000000006")
STAGES = [
    StageOption(id=KUT, ordinal=5, name="Kut (iron-black printing)"),
    StageOption(id=PA, ordinal=6, name="Pa"),
]
ALUM = sentence(
    "Alum is the mordant that binds alizarin to cotton.",
    quote(ALUM_CLAIM_ID, "Alum is the mordant that binds alizarin to cotton"),
)


def focused(*stages: StageOption):
    focus = ComposeFocus(discipline="PROCESS", title="How it is made", stages=list(stages))
    return compose_request(pack(), QUESTION, focus=focus)


async def test_a_section_call_names_its_field_and_offers_the_stored_stages_as_data() -> None:
    model = FakeModel([section_reply(ALUM, stages=[KUT])])
    composed = await ModelComposer(model=model).compose(focused(*STAGES))
    (call,) = model.calls
    assert call["system"] == SECTION_SYSTEM_PROMPT
    assert call["schema"] == section_schema([str(KUT), str(PA)])
    assert "Section: How it is made (how the craft is made, stage by stage)" in call["user"]
    assert '<untrusted_source ref="stages" label="process stages stored for the craft">' in call["user"]
    assert f"{KUT}: step 5, Kut (iron-black printing)" in call["user"]
    assert composed.stage_ids == [KUT]
    assert [s.text for s in composed.sections[0].sentences] == [
        "Alum is the mordant that binds alizarin to cotton."
    ]
    assert composed.sections[0].heading == "How it is made"


async def test_a_stage_that_was_not_offered_is_never_chosen() -> None:
    stranger = uuid.UUID("0f0e0d0c-0b0a-4908-8706-050403020100")
    model = FakeModel([section_reply(stages=[stranger, KUT, KUT])])
    composed = await ModelComposer(model=model).compose(focused(*STAGES))
    assert composed.stage_ids == [KUT]
    assert composed.sections == []


async def test_without_offered_stages_the_reply_has_no_stage_field() -> None:
    model = FakeModel([section_reply(ALUM)])
    composed = await ModelComposer(model=model).compose(focused())
    assert "stages" not in model.calls[0]["schema"]["properties"]
    assert composed.stage_ids == []


async def test_a_failing_section_sentence_is_regenerated_once_and_the_chosen_stages_stay() -> None:
    wrong = sentence("Alum is a mordant.", quote("openalex:W404", "a passage that was never read at all"))
    model = FakeModel([section_reply(wrong, stages=[PA]), replacements((0, ALUM))])
    composed = await ModelComposer(model=model).compose(focused(*STAGES))
    assert len(model.calls) == 2
    assert composed.stage_ids == [PA]
    assert [s.text for s in composed.sections[0].sentences] == [
        "Alum is the mordant that binds alizarin to cotton."
    ]


async def test_a_section_keeps_at_most_eight_sentences_and_two_follow_ups() -> None:
    reply = json.loads(section_reply(*[ALUM] * 10, follow_ups=["One?", "Two?", "Three?"]))
    model = FakeModel([json.dumps(reply)])
    composed = await ModelComposer(model=model).compose(focused())
    assert len(composed.sections[0].sentences) == 8
    assert composed.follow_ups == ["One?", "Two?"]
