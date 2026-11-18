from __future__ import annotations

from dataclasses import replace

import pytest

from app.research.craft_page import CraftPage
from app.services.craft_page import craft_page
from app.services.craft_page_records import ClaimFacts

from .test_craft_page import HISTORY_CONCEPT, stored_view, uncurated_records


@pytest.mark.parametrize(
    ("text", "span"),
    [
        (
            "In 1930 hundreds of Indian cotton fragments of the 11th to 14th century were found at "
            "Al Fustat in Old Cairo, the earliest known printed cloth.",
            (1001, 1400),
        ),
        (
            "The applicant states that hand block printing was Bagru's main source of revenue during "
            "the 18th and 19th centuries.",
            (1701, 1900),
        ),
        (
            "TERI places the foundations of the Firozabad bangle industry in the Mughal period, the 16th "
            "to 18th century, when the Indian glass industry received royal patronage.",
            (1501, 1800),
        ),
        (
            "Mamallapuram, on the Coromandel coast, was a major port city of the Pallava dynasty from the "
            "sixth to ninth century CE.",
            (501, 900),
        ),
        ("A Hoysala inscription in Mysuru dates back to the 11th and 12th century.", (1001, 1200)),
        (
            "According to the GI application, pata paintings flourished in Orissa in the early 15th and "
            "16th centuries.",
            (1401, 1600),
        ),
        (
            "Soviet scholars dated the introduction of rotary querns to Central Asia, including India, to "
            "the 3rd and 4th centuries CE.",
            (201, 400),
        ),
    ],
)
def test_a_stated_century_range_is_one_event_from_its_first_century_to_its_last(
    text: str, span: tuple[int, int]
) -> None:
    page = _with_stored_claim(text)
    assert [(event.kind, event.start, event.end) for event in page.events] == [("STATED", *span)]


@pytest.mark.parametrize(
    "text",
    [
        "No record of a Sanganer printing unit is traced before the early 18th century, and 16th and "
        "17th century East India Company records give no such account.",
        "Sahapedia notes that no examples of bidri dating to the 15th or 16th centuries have been found "
        "in paintings or literature.",
        "About 1450 million years ago the Delhi Orogeny metamorphosed the original limestones of Makrana "
        "into marble.",
        "Blowing through the pipe raises the fire to about 1000-1200 degrees Celsius.",
        "Ceramics Monthly reports that one Jaipur workshop fires its kiln for 8 hours to 1000°C.",
    ],
)
def test_an_absence_a_measure_or_a_sum_is_never_a_dated_event(text: str) -> None:
    assert _with_stored_claim(text).events == []


def _with_stored_claim(text: str) -> CraftPage:
    base = uncurated_records()
    view = stored_view(7, text, HISTORY_CONCEPT)
    facts = {**base.facts, view.id: ClaimFacts("LIVE_RESEARCH", False, None, "History", "HISTORICAL_CONTEXT")}
    return craft_page(replace(base, views=(*base.views, view), facts=facts))
