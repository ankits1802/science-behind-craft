from dataclasses import replace

from app.research.expert_panel import EXPERT_PANEL
from app.services.seat_search import seat_query

from ..experts.fixtures import QUESTION, build_ask

ENGLISH = "When did the Khatri printers bring Ajrakh to Kutch?"


def test_a_seat_search_is_filtered_by_the_seats_own_fields() -> None:
    chemist = seat_query(build_ask(("CHEMIST",), discipline="CHEMISTRY"), EXPERT_PANEL["CHEMIST"])
    assert chemist.fields == ("CHEMISTRY", "PROCESS", "MATERIALS", "HEALTH")
    historian = seat_query(build_ask(("HISTORIAN",)), EXPERT_PANEL["HISTORIAN"])
    assert historian.fields == ("HISTORY", "OVERVIEW")


def test_a_seat_searches_the_english_rendering_when_the_answer_has_one() -> None:
    ask = build_ask(("HISTORIAN",))
    rendered = replace(ask, request=ask.request.model_copy(update={"english_question": ENGLISH}))
    assert seat_query(rendered, EXPERT_PANEL["HISTORIAN"]).text.startswith(ENGLISH)
    assert seat_query(ask, EXPERT_PANEL["HISTORIAN"]).text.startswith(QUESTION)
