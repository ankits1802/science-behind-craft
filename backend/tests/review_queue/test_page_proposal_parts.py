import uuid
from typing import Any

from app.research.page_proposal_parts import LAYOUT_TITLE, proposal_parts
from app.research.page_proposals import PageBundle, PartReport

from ..research.page_report_rules_fixtures import FIGURE, SLUG, page_document

FACT_ID, TABLE_ID, LAYOUT_ID, REFUSED_ID = (
    uuid.uuid5(uuid.NAMESPACE_URL, f"page-parts/{name}") for name in "ftlr"
)
HISTORY = "Printers in the town have dyed with alum since the eighteenth century."
SUBJECT = {"kind": "craft", "slug": SLUG}


def fact() -> dict[str, Any]:
    quote = {"text": "printers in the town have dyed with alum since the eighteenth century"}
    source = {"url": "https://example.org/alum-history", "title": "The town's printers", "quotes": [quote]}
    return {"subject": SUBJECT, "field": "HISTORY", "statement": HISTORY, "sources": [source]}


def component(label: str) -> dict[str, Any]:
    proposal = {
        "label": label,
        "title": "Alum on cotton",
        "description": "A table of what alum does on the cotton and how long the town has printed with it.",
        "kind": "fact_table",
        "field": "MATERIALS",
        "craftSlug": SLUG,
        "subjects": [{"kind": "CRAFT", "key": SLUG}],
    }
    return {"proposal": proposal, "cites": {}}


def bundle() -> PageBundle:
    return PageBundle.model_validate(
        {
            "subject": SUBJECT,
            "facts": [fact()],
            "components": [component(FIGURE), component("test-craft/process/vat-steps")],
            "layout": {"baseVersion": 0, "entries": []},
        }
    )


def report(part: str, index: int, ident: uuid.UUID | None, outcome: str = "ACCEPTED") -> PartReport:
    return PartReport.model_validate(
        {
            "part": part,
            "index": index,
            "outcome": outcome,
            "id": None if ident is None else str(ident),
            "message": "Kept.",
        }
    )


def test_each_accepted_part_is_kept_with_the_chapter_it_lands_in_and_the_refused_left_out() -> None:
    reports = [
        report("fact", 0, FACT_ID),
        report("component", 0, TABLE_ID),
        report("component", 1, REFUSED_ID, outcome="REFUSED"),
        report("layout", 0, LAYOUT_ID),
        report("picture", 0, None),
    ]
    parts = proposal_parts(bundle(), reports, page_document())
    assert [(part.part, part.kind, part.id, part.chapter, part.label) for part in parts] == [
        ("fact", "FACTS", FACT_ID, "history", None),
        ("component", "COMPONENTS", TABLE_ID, "chem", FIGURE),
        ("layout", "LAYOUTS", LAYOUT_ID, None, None),
    ]
    assert [part.title for part in parts] == [HISTORY, "Alum on cotton", LAYOUT_TITLE]


def test_without_a_drawing_a_component_lands_in_its_field_s_chapter() -> None:
    parts = proposal_parts(bundle(), [report("component", 0, TABLE_ID)], None)
    assert [(part.chapter, part.label) for part in parts] == [("made", FIGURE)]
