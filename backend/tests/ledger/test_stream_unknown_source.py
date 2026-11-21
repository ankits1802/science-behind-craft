from typing import Any

from app.research.explainer import ExplainerSection
from app.services.claim_ledger import admission_batches
from app.services.explainer_events import ExplainerStream

from .indigo_answer import recorded_sections
from .indigo_claims import SOURCES

ORDER = ("s1", "s2", "s3", "s4", "s5")


class Recorded:
    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    async def __call__(self, name: str, data: Any) -> None:
        self.events.append((name, data))

    def blocks(self) -> list[Any]:
        return [data["block"] for name, data in self.events if name == "block"]

    def source_ids(self) -> set[str]:
        return {data["id"] for name, data in self.events if name == "source"}


def _sections() -> dict[str, ExplainerSection]:
    return {payload["id"]: ExplainerSection.model_validate(payload) for payload in recorded_sections()}


def _first_cited_source(sections: dict[str, ExplainerSection]) -> str:
    for section_id in ORDER:
        for block in sections[section_id].blocks:
            if block.cited_source_ids():
                return block.cited_source_ids()[0]
    raise AssertionError("the recorded answer cites no source")


async def test_a_block_citing_a_source_not_sent_with_it_is_left_out_and_the_answer_goes_on() -> None:
    sections = _sections()
    withheld = _first_cited_source(sections)
    citing = {
        block.id
        for section in sections.values()
        for block in section.blocks
        if withheld in block.cited_source_ids()
    }
    refs = {ref["id"]: ref for ref in SOURCES if ref["id"] != withheld}
    recorded = Recorded()
    stream = ExplainerStream(recorded, language="en")
    returned = []
    for section_id in ORDER:
        for batch in admission_batches(sections[section_id].blocks):
            returned += await stream.blocks(section_id, batch, refs)
    shown = recorded.blocks()
    assert citing
    assert shown
    assert not {block.id for block in shown} & citing
    assert [block.id for block in returned] == [block.id for block in shown]
    assert {source for block in shown for source in block.cited_source_ids()} <= recorded.source_ids()
    assert withheld not in recorded.source_ids()
