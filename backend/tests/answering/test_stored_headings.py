import dataclasses

from app.research.sections import is_facet_label
from app.services.answer_events import cited_claims
from app.services.answering import AnswerAsk
from app.services.knowledge_view import SECTION_HEADINGS
from app.services.stored_explainer import stored_heading

from ..composer.fixtures import QUESTION
from .fakes import SOURCES, VIEWS, FakeStore, pipeline, streamed
from .test_answer_flow import events


def test_no_stored_answer_heading_is_a_field_label() -> None:
    for group in set(SECTION_HEADINGS.values()):
        assert not is_facet_label(stored_heading(group, "Kutch Ajrakh"))
    assert stored_heading("History", "Kutch Ajrakh") == "Where Kutch Ajrakh comes from"
    assert stored_heading("Process", "Kutch Ajrakh") == "How Kutch Ajrakh is made"
    assert stored_heading("Design", "Kutch Ajrakh") == "The patterns of Kutch Ajrakh"
    assert stored_heading("Materials and tools", "Kutch Ajrakh") == "Materials and tools"


async def test_a_spent_budget_answer_heads_its_sections_without_field_labels() -> None:
    views = [
        dataclasses.replace(VIEWS[0], concept_type="HISTORICAL_CONTEXT"),
        dataclasses.replace(VIEWS[1], concept_type="PROCESS_STAGE"),
        dataclasses.replace(VIEWS[2], concept_type="DESIGN_PRINCIPLE"),
    ]
    store = FakeStore(stored=cited_claims(views, SOURCES))
    ask = AnswerAsk(question=QUESTION, depth="BASIC")
    found = events(await streamed(ask, pipeline(store=store, spent=True)))
    started = [(data["discipline"], data["title"]) for name, data in found if name == "section_started"]
    assert started == [
        ("HISTORY", "Where Kutch Ajrakh comes from"),
        ("DESIGN", "The patterns of Kutch Ajrakh"),
        ("PROCESS", "How Kutch Ajrakh is made"),
    ]
