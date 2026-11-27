from app.services.monograph_generated_parts import StoredSection
from app.services.page_preview_additions import NO_ADDITIONS, PageAdditions

PUBLISHED = {"text": "Madder gives a red colour on cotton.", "claimIds": ["c1"]}
WRITTEN = (
    {"text": "Alum is printed before the madder bath.", "claimIds": ["c2"]},
    {"text": "Madder gives the cotton its red.", "claimIds": ["c1"]},
)
DRAFTED = {"text": "The printed cloth is washed in the river.", "claimIds": ["c3"]}
STORED = [
    StoredSection("CHEMISTRY", 4, (PUBLISHED,)),
    StoredSection("HISTORY", 2, ({"text": "h", "claimIds": ["c4"]},)),
]


def test_a_written_section_takes_the_published_one_s_place_with_the_draft_s_facts_after_it() -> None:
    drawn = PageAdditions(written={"CHEMISTRY": WRITTEN}, sentences={"CHEMISTRY": (DRAFTED,)}).sections(
        STORED
    )
    assert [(section.field, section.version) for section in drawn] == [("CHEMISTRY", 4), ("HISTORY", 2)]
    assert drawn[0].sentences == (*WRITTEN, DRAFTED)
    assert drawn[1] == STORED[1]


def test_a_written_section_of_a_field_with_none_published_is_drawn_new_in_its_field_s_place() -> None:
    drawn = PageAdditions(written={"PROCESS": WRITTEN}).sections(STORED)
    assert [(section.field, section.version) for section in drawn] == [
        ("PROCESS", 0),
        ("CHEMISTRY", 4),
        ("HISTORY", 2),
    ]
    assert drawn[0].sentences == WRITTEN


def test_without_a_written_section_the_draft_s_facts_join_the_published_section_as_before() -> None:
    drawn = PageAdditions(sentences={"CHEMISTRY": (DRAFTED,)}).sections(STORED)
    assert drawn[0].sentences == (PUBLISHED, DRAFTED)
    assert NO_ADDITIONS.sections(STORED) == STORED
