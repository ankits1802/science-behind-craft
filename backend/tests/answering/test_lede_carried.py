import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from app.research.explainer_versions import version_problems
from app.research.structured import StructuredReply
from app.services.answering import AnswerAsk

from ..composer.fixtures import section_reply
from ..planner.fakes import FakeModel
from .fakes import streamed, translation
from .test_answer_flow import events
from .test_follow_up_flow import ALUM, BATH, SECOND_ID, first_version, follow_up_of
from .test_lede_flow import (
    ALUM_RED,
    HARDE,
    MORDANT,
    MORDANT_LEDE,
    lede_pipeline,
    mordant_store,
    sections_model,
    understood_as,
)

LEDE_HI = {
    "lede.1": "फिटकरी वह मॉर्डेंट है जो धावड़ी (झाऊ की गाँठों) के साथ लाल रंग पक्का करती है।",
    "lede.2": "हरड़े, हरड़ का लेप, पहले कपड़े को वह टैनिन देता है जो एक ज़रूरी पूर्व-मॉर्डेंट है।",
}
OTHER_HI = "अनुवाद"


@dataclass
class KeyedTranslator:
    texts: Mapping[str, str]
    keys: list[list[str]] = field(default_factory=list)

    async def __call__(self, *, system: str, user: str, schema: Mapping[str, Any]) -> StructuredReply:
        keys = schema["properties"]["items"]["items"]["properties"]["key"]["enum"]
        self.keys.append(list(keys))
        items = [{"key": key, "text": self.texts.get(key, OTHER_HI)} for key in keys]
        return StructuredReply(text=json.dumps({"items": items}, ensure_ascii=False), degraded=False)


async def test_a_hindi_lede_keeps_its_headline_as_asked_and_its_english_originals() -> None:
    built = lede_pipeline(
        FakeModel([MORDANT_LEDE]),
        store=mordant_store(),
        compose_model=sections_model(),
        understand_model=understood_as("PROCESS", "CHEMISTRY"),
        translated=translation(KeyedTranslator(LEDE_HI)),
    )
    found = events(await streamed(AnswerAsk(question=MORDANT, depth="DETAILED", language="hi"), built))
    (lede,) = [data["block"] for name, data in found if name == "lede"]
    assert lede["headline"] == MORDANT
    assert [(s["text"], s["translated"]) for s in lede["sentences"]] == [
        (LEDE_HI["lede.1"], True),
        (LEDE_HI["lede.2"], True),
    ]
    english = json.loads(MORDANT_LEDE)["sentences"]
    assert [s["original"] for s in lede["sentences"]] == [s["text"] for s in english]
    assert [{c["claimId"] for c in s["citations"]} for s in lede["sentences"]] == [
        {str(ALUM_RED.id)},
        {str(HARDE.id)},
    ]
    (heading,) = [data for name, data in found if name == "section_heading"]
    assert heading == {"sectionId": "s1", "title": OTHER_HI, "original": "Alum binds the red to cotton"}


async def test_a_follow_up_that_opens_with_a_lede_keeps_it_and_its_sources_in_the_merged_version() -> None:
    first = await first_version()
    assert first.lede is None
    store = mordant_store()
    store.answer_id = SECOND_ID
    built = lede_pipeline(FakeModel([MORDANT_LEDE]), store=store, replies=[section_reply(ALUM, BATH)])
    found = events(await streamed(follow_up_of(first, "CHEMISTRY"), built))
    assert "lede" in [name for name, _ in found]
    (finished,) = store.finished
    merged, mark = finished["explainer"], finished["version"]
    assert merged.lede is not None and merged.lede.headline == merged.question
    assert set(merged.lede.cited_source_ids()) <= {source.id for source in merged.sources}
    assert [source.id for source in merged.sources][:1] == merged.lede.cited_source_ids()[:1]
    assert version_problems(first, merged, mark.changes) == []
