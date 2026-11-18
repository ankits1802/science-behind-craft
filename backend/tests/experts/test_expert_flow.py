import dataclasses
import uuid
from collections.abc import Iterable

from app.services.answer_events import CitedClaims, cited_claims
from app.services.block_builders import BLOCK_BUILDERS, BlockBuilders
from app.services.expert_views import ExpertPanelBuilder

from ..answering.fakes import (
    BOOK,
    LAKE,
    SOURCES,
    VIEWS,
    FakeStore,
    enriched,
    pipeline,
    stored_view,
    streamed,
    understanding_model,
)
from ..answering.piece_fakes import MemoryPieces
from ..answering.test_answer_flow import REPLY, detailed, events
from .fixtures import differ, panel_model, said, take, tools

MORDANT = uuid.UUID("5a000000-0000-4000-8000-0000000000aa")
ALUM, LAKE_VIEW, WASH, GUESS = (dataclasses.replace(view, concept_id=MORDANT) for view in VIEWS)
SOAKED = stored_view(
    uuid.UUID("5a000000-0000-4000-8000-0000000000b1"),
    "Cloth is soaked in the alum bath overnight before printing.",
    "PROVISIONAL",
    (31, BOOK, "Cloth is soaked in the alum bath overnight before printing", "p. 44"),
    concept_id=MORDANT,
)
RINSED = stored_view(
    uuid.UUID("5a000000-0000-4000-8000-0000000000b2"),
    "Unfixed alum is rinsed out in running water after the dye bath.",
    "PROVISIONAL",
    (32, LAKE, "Unfixed alum is rinsed out in running water after the dye bath", None),
    concept_id=MORDANT,
)
HEATED = stored_view(
    uuid.UUID("5a000000-0000-4000-8000-0000000000b3"),
    "A hot alum bath fixes the red faster than a cold one.",
    "PROVISIONAL",
    (33, LAKE, "A hot alum bath fixes the red faster than a cold one", None),
    concept_id=MORDANT,
)
UNDERSTOOD = {
    "craft": "",
    "craftNames": [],
    "disciplines": ["CHEMISTRY"],
    "seats": ["CHEMIST", "MATERIALS_SCIENTIST"],
}


@dataclasses.dataclass
class SubjectStore(FakeStore):
    async def cited(self, claim_ids: Iterable[uuid.UUID]) -> CitedClaims:
        wanted = list(claim_ids)
        self.asked_for.append(wanted)
        known = [view for view in (ALUM, LAKE_VIEW, WASH, GUESS) if view.id in wanted]
        return cited_claims([*known, SOAKED, RINSED, HEATED], SOURCES)


async def test_expert_views_stream_after_the_prose_and_join_the_explainer_and_its_pieces() -> None:
    store, pieces = SubjectStore(), MemoryPieces()
    panel = panel_model(
        [take("CHEMIST", said(SOAKED)), take("MATERIALS_SCIENTIST", said(RINSED))],
        [differ("CHEMIST", ALUM, "MATERIALS_SCIENTIST", HEATED)],
    )
    (entry,) = [entry for entry in BLOCK_BUILDERS if entry.kind == "expert_view"]
    answer = dataclasses.replace(
        pipeline(
            replies=[REPLY],
            store=store,
            pieces=pieces,
            enrichment=enriched(),
            understand_model=understanding_model(UNDERSTOOD),
        ),
        builders=BlockBuilders([(entry, ExpertPanelBuilder(tools(panel)))]),
    )
    found = events(await streamed(detailed(), answer))
    shown = [(payload["block"]["id"], payload["block"]["kind"]) for name, payload in found if name == "block"]
    assert shown == [
        ("s1.b1", "prose"),
        ("s1.b2", "expert_view"),
        ("s1.b3", "expert_view"),
        ("s1.b4", "images"),
    ]
    (call,) = panel.calls
    assert call["schema"]["properties"]["views"]["items"]["properties"]["seat"]["enum"] == [
        "CHEMIST",
        "MATERIALS_SCIENTIST",
    ]
    (finished,) = store.finished
    chemist, scientist = finished["explainer"].sections[0].blocks[1:3]
    assert (chemist.seat, scientist.seat) == ("CHEMIST", "MATERIALS_SCIENTIST")
    assert [c.claim_id for c in chemist.differs[0].this_view.citations] == [str(ALUM.id)]
    assert [c.claim_id for c in scientist.differs[0].this_view.citations] == [str(HEATED.id)]
    assert [sentence.text for sentence in (*chemist.take, *scientist.take)] == [SOAKED.text, RINSED.text]
    ((_, _, sections),) = pieces.kept
    assert [block.kind for block in sections[0].blocks] == ["prose", "expert_view", "expert_view"]
