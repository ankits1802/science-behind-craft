import uuid
from typing import Any

from app.research.staged_review_words import PageTouches, decision_words, proposal_review_link
from app.research.staged_reviews import StagedDecision

ITEM = uuid.UUID("6f1c2a4e-8d3b-4c5a-9e7f-0a1b2c3d4e31")
WHY = "Both quotes say this of the vat, word for word."
SITE = "https://kalavigyan.example"
LINK = f"{SITE}/admin/review?proposal={ITEM}"


def decided(**values: Any) -> StagedDecision:
    return StagedDecision.model_validate({"kind": "FACTS", "id": ITEM, "reason": WHY} | values)


def test_the_link_opens_the_proposal_on_the_review_page() -> None:
    assert proposal_review_link(SITE, ITEM) == LINK


def test_a_waiting_fact_s_approval_says_it_is_published_where_it_is_filed_and_why() -> None:
    said = decision_words(decided(action="approve", craft="Kutch-Ajrakh"), "An indigo vat turns blue.")
    assert said == (
        "Approve “An indigo vat turns blue.”: it is published for readers. It is filed under the craft "
        f"Kutch-Ajrakh. The reason given: “{WHY}”"
    )


def test_a_rejection_and_a_raise_each_say_what_they_do() -> None:
    rejected = decision_words(decided(action="reject"), "Lime keeps the vat alkaline.")
    assert rejected.startswith(
        "Reject “Lime keeps the vat alkaline.”: it is not published, and whoever gave it reads the reason."
    )
    raised = decision_words(decided(action="raise"), "Lime keeps the vat alkaline.")
    assert "it is published as reviewed, its evidence level raised." in raised


def test_an_edit_of_published_content_shows_each_field_before_and_after() -> None:
    edit = {"fields": {"text": "Lime keeps the indigo vat alkaline."}, "before": {"text": "Lime keeps it."}}
    said = decision_words(decided(action="edit", edit=edit), "Edit the fact “Lime keeps it.”")
    assert said.startswith(
        "Edit the fact “Lime keeps it.”: readers see it changed (Text “Lime keeps it.” becomes “Lime keeps "
        "the indigo vat alkaline.”), and the record keeps the old version."
    )


def test_a_removal_of_published_content_says_the_record_keeps_it() -> None:
    said = decision_words(
        decided(kind="COMPONENTS", action="remove", craft="Kutch-Ajrakh"), "Remove the table from the page"
    )
    assert said.startswith(
        "Remove the table from the page: readers no longer see it there, and the record keeps it."
    )
    assert "filed under" not in said


def test_a_source_correction_names_each_corrected_field() -> None:
    source = {"title": "Indigo vats and their chemistry", "year": 2007, "authors": ["A. Rao", "B. Shah"]}
    said = decision_words(decided(kind="SOURCES", action="correct", source=source), "Source: Indigo vats")
    assert (
        "the source's record changes: title “Indigo vats and their chemistry”, authors A. Rao and B. Shah, "
        in said
    )
    assert "year 2007." in said


def test_a_page_decision_names_the_chapters_and_components_it_touches_and_its_private_link() -> None:
    page = {"scope": "CHAPTER", "chapter": "chem"}
    touches = PageTouches(("The chemistry",), ("Black and red from one dye bath", "The mordant table"), LINK)
    said = decision_words(
        decided(kind="PAGES", action="approve", page=page),
        "Page proposal for Sanganeri: the chapter chem",
        touches=touches,
    )
    assert said == (
        "Approve “Page proposal for Sanganeri: the chapter chem”: each part of it that still waits is approved "
        "through its own queue's checks. It touches the chapter The chemistry, and the components Black and red "
        "from one dye bath and The mordant table. The page as it stood and as it will be, for reviewers only: "
        f"{LINK} The reason given: “{WHY}”"
    )


def test_a_page_rejection_without_parts_still_gives_its_link() -> None:
    said = decision_words(
        decided(kind="PAGES", action="reject", page={"scope": "PAGE"}),
        "Page proposal for Sanganeri: the whole page",
        touches=PageTouches((), (), LINK),
    )
    assert "is rejected through its own queue's checks." in said and "It touches" not in said and LINK in said
