from app.research.page_counts import BAR_SLUG, Counts, bar_counts, chapter_key, content_counts
from app.services.page_report import bar_content

from .page_report_rules_fixtures import page_document


def counts(pictures: int, figures: int, interactives: int, maps: int) -> Counts:
    return Counts(pictures=pictures, figures=figures, interactives=interactives, maps=maps)


def test_kutch_ajrakh_holds_nine_pictures_seventy_one_figures_fourteen_interactives_and_eight_maps() -> None:
    found = bar_counts(page_document().content, bar_content())
    assert found.bar_slug == BAR_SLUG == "Kutch-Ajrakh"
    assert found.bar == counts(9, 71, 14, 8)


def test_kutch_ajrakh_s_chapters_are_counted_under_the_generated_page_s_names() -> None:
    by_chapter = content_counts(bar_content())
    assert by_chapter["opening"] == counts(1, 1, 1, 0)
    assert by_chapter["chem"] == counts(2, 14, 7, 0)
    assert by_chapter["why"] == counts(2, 14, 0, 7)
    assert by_chapter["whatif"] == counts(0, 6, 4, 0)
    assert by_chapter["media"] == counts(0, 10, 0, 0)
    assert set(by_chapter) == {
        "opening",
        "glance",
        "made",
        "chem",
        "why",
        "history",
        "market",
        "whatif",
        "people",
        "kin",
        "reading",
        "media",
        "sources",
    }


def test_an_authored_chapter_key_is_read_as_the_generated_one() -> None:
    assert [
        chapter_key(key) for key in ("answer", "cloth", "chemistry", "why-kachchh", "what-if", "made")
    ] == [
        "opening",
        "glance",
        "chem",
        "why",
        "whatif",
        "made",
    ]


def test_a_page_is_set_beside_the_bar_chapter_by_chapter_its_own_first() -> None:
    found = bar_counts(page_document().content, bar_content())
    assert found.page == counts(1, 1, 0, 0)
    assert [line.chapter for line in found.chapters][:4] == ["opening", "chem", "glance", "made"]
    chem = next(line for line in found.chapters if line.chapter == "chem")
    assert (chem.page, chem.bar) == (counts(0, 1, 0, 0), counts(2, 14, 7, 0))
    assert "never passes or fails" in found.note
