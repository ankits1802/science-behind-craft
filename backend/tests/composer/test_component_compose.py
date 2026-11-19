import json
import logging
import uuid

import pytest
from pydantic import ValidationError

from app.composer.candidates import compose_request
from app.composer.composer import ModelComposer
from app.composer.prompt import SECTION_SYSTEM_PROMPT, section_schema
from app.research.composition import ComponentOption, ComposedAnswer, ComposeFocus, StageOption

from ..planner.fakes import FakeModel
from .fixtures import ALUM_CLAIM_ID, QUESTION, pack, quote, section_reply, sentence

PLAYER = ComponentOption(
    label="kutch-ajrakh/chemistry/red-alum-madder-player",
    kind="reaction_player",
    description="Red develops only where alum was printed.\nPlace it where a page explains the red.",
)
MOLECULES = ComponentOption(
    label="shared/chemistry/alizarin-purpurin-3d",
    kind="molecule_3d",
    description="Alizarin and purpurin in three dimensions.",
)
INVENTED = "kutch-ajrakh/chemistry/made-up-player"
ALUM = sentence(
    "Alum is the mordant that binds alizarin to cotton.",
    quote(ALUM_CLAIM_ID, "Alum is the mordant that binds alizarin to cotton"),
)


def offering(*components: ComponentOption, stages: list[StageOption] | None = None):
    focus = ComposeFocus(
        discipline="CHEMISTRY", title="The chemistry", stages=stages or [], components=list(components)
    )
    return compose_request(pack(), QUESTION, focus=focus)


def chose(*labels: str, items: tuple = (ALUM,)) -> str:
    reply = json.loads(section_reply(*items))
    reply["components"] = list(labels)
    return json.dumps(reply)


async def test_a_section_call_offers_its_catalogue_one_line_each_as_data() -> None:
    model = FakeModel([chose(PLAYER.label)])
    await ModelComposer(model=model).compose(offering(PLAYER, MOLECULES))
    (call,) = model.calls
    assert call["system"] == SECTION_SYSTEM_PROMPT
    assert "- components: present only when components are offered" in call["system"]
    offered = call["schema"]["properties"]["components"]
    assert offered == {"type": "array", "items": {"type": "string", "enum": [PLAYER.label, MOLECULES.label]}}
    assert call["schema"]["required"] == ["sentences", "components", "heading", "followUps"]
    assert '<untrusted_source ref="components" label="components already built for the craft' in call["user"]
    assert (
        "kutch-ajrakh/chemistry/red-alum-madder-player: reaction_player, Red develops only where alum was "
        "printed. Place it where a page explains the red."
    ) in call["user"]
    assert (
        "shared/chemistry/alizarin-purpurin-3d: molecule_3d, Alizarin and purpurin in three dimensions."
        in (call["user"])
    )


async def test_the_answer_keeps_offered_labels_once_each_in_the_order_chosen() -> None:
    model = FakeModel([chose(MOLECULES.label, PLAYER.label, MOLECULES.label)])
    composed = await ModelComposer(model=model).compose(offering(PLAYER, MOLECULES))
    assert composed.component_labels == [MOLECULES.label, PLAYER.label]


async def test_a_label_the_model_invents_is_dropped_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    model = FakeModel([chose(INVENTED, PLAYER.label, "shared/chemistry/indigo-vat-dip")])
    with caplog.at_level(logging.WARNING, logger="app.composer.composer"):
        composed = await ModelComposer(model=model).compose(offering(PLAYER, MOLECULES))
    assert composed.component_labels == [PLAYER.label]
    assert "compose dropped 2 component label(s) that were not offered" in caplog.text


async def test_without_an_offered_catalogue_the_reply_has_no_component_field() -> None:
    model = FakeModel([chose(PLAYER.label)])
    composed = await ModelComposer(model=model).compose(offering())
    assert "components" not in model.calls[0]["schema"]["properties"]
    assert 'ref="components"' not in model.calls[0]["user"]
    assert composed.component_labels == []


async def test_stages_and_components_are_offered_side_by_side() -> None:
    stage = StageOption(id=uuid.UUID("77bf953a-03a3-54c3-a1bb-37ac338266df"), ordinal=5, name="Kut")
    reply = {**json.loads(chose(PLAYER.label)), "stages": [str(stage.id)]}
    model = FakeModel([json.dumps(reply)])
    composed = await ModelComposer(model=model).compose(offering(PLAYER, stages=[stage]))
    schema = model.calls[0]["schema"]
    assert schema == section_schema([str(stage.id)], labels=[PLAYER.label])
    assert list(schema["properties"]) == ["sentences", "stages", "components", "heading", "followUps"]
    assert (composed.stage_ids, composed.component_labels) == ([stage.id], [PLAYER.label])


async def test_components_alone_never_make_an_answer() -> None:
    wrong = sentence("Alum is a mordant.", quote("openalex:W404", "a passage that was never read at all"))
    model = FakeModel([chose(PLAYER.label, items=(wrong,)), json.dumps({"sentences": []})])
    composed = await ModelComposer(model=model).compose(offering(PLAYER))
    assert composed.not_enough_evidence is not None
    assert composed.component_labels == []


def test_a_focus_offers_each_component_once_and_at_most_six() -> None:
    with pytest.raises(ValidationError):
        ComposeFocus(discipline="CHEMISTRY", title="The chemistry", components=[PLAYER, PLAYER])
    many = [PLAYER.model_copy(update={"label": f"shared/chemistry/player-{n}"}) for n in range(7)]
    with pytest.raises(ValidationError):
        ComposeFocus(discipline="CHEMISTRY", title="The chemistry", components=many)
    assert len(ComposeFocus(discipline="CHEMISTRY", title="x", components=many[:6]).components) == 6


def test_a_composed_answer_places_each_component_once_beside_what_it_shows() -> None:
    summary = offering().searched
    with pytest.raises(ValidationError):
        ComposedAnswer(not_enough_evidence=summary, component_labels=[PLAYER.label])
    with pytest.raises(ValidationError):
        ComposedAnswer(stage_ids=[uuid.uuid4()], component_labels=[PLAYER.label, PLAYER.label])
    shown = ComposedAnswer(stage_ids=[uuid.uuid4()], component_labels=[PLAYER.label])
    assert shown.component_labels == [PLAYER.label]
