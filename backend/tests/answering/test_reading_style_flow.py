from app.composer.prompt import SECTION_SYSTEM_PROMPT
from app.research.reading_style import style_paragraph

from ..planner.fakes import FakeModel
from .fakes import pipeline, streamed
from .test_answer_flow import REPLY, detailed


async def test_a_young_readers_sections_are_composed_in_their_style_and_nothing_else_changes() -> None:
    plain_model, young_model = FakeModel([REPLY]), FakeModel([REPLY])
    plain = await streamed(detailed(), pipeline(compose_model=plain_model))
    young = await streamed(detailed(reading_style="CHILD"), pipeline(compose_model=young_model))
    assert [call["system"] for call in plain_model.calls] == [SECTION_SYSTEM_PROMPT]
    assert [call["system"] for call in young_model.calls] == [
        f"{SECTION_SYSTEM_PROMPT}\n\n{style_paragraph('CHILD')}"
    ]
    assert [call["user"] for call in young_model.calls] == [call["user"] for call in plain_model.calls]
    assert young == plain
