from __future__ import annotations

import uuid
from dataclasses import replace

import pytest

from app.data.craft_master_loader import ID_NAMESPACE, load_master
from app.research.category_page import CategoryPage
from app.services.category_page import category_list, category_page
from app.services.category_preview import category_list_preview, category_page_preview
from app.services.category_register import SubCategoryRecord

from .category_support import LEATHER, LEATHER_DOSSIER, PAPER, leather_plain, leather_records

FOOTWEAR = "Leather-Footwear"
ARTICLES = "Leather-Other-Articles"


def curation_id(key: str) -> uuid.UUID:
    return uuid.uuid5(ID_NAMESPACE, f"curation:{LEATHER}:{key}")


@pytest.fixture(scope="module")
def leather() -> CategoryPage:
    return category_page(leather_records())


def test_the_overview_is_the_dossier_s_cited_lede_facts_and_sections(leather: CategoryPage) -> None:
    plain = leather_plain()
    assert leather.curated and leather.curation is not None
    assert (leather.curation.version, leather.curation.coverage) == (1, "THIN")
    assert [s.text for s in leather.overview.lede] == [s["text"] for s in plain["overview"]["lede"]]
    assert [f.label for f in leather.overview.key_facts] == ["Sub-categories", "Tanning methods"]
    section = leather.overview.sections[0]
    assert (section.discipline, section.title, len(section.sentences)) == ("OVERVIEW", "What it is", 5)
    assert leather.overview.lede[0].claim_ids == [curation_id(key) for key in ("C001", "C003", "C004")]
    marked = [span.term_key for s in leather.overview.sentences() for span in s.terms]
    assert marked == ["tholu-bommalata", "togalu-gombeyata"]


def test_each_sub_category_shows_its_crafts_and_the_first_sentence_that_covers_it(
    leather: CategoryPage,
) -> None:
    master = [craft for craft in load_master() if craft.category_slug == LEATHER]
    subs = {sub.slug: sub for sub in leather.sub_categories}
    assert list(subs) == [FOOTWEAR, ARTICLES]
    for slug, sub in subs.items():
        members = [craft for craft in master if craft.sub_category_slug == slug]
        assert {craft.slug for craft in sub.crafts} == {craft.slug for craft in members}
        assert sub.craft_count == sum(1 for craft in members if not craft.is_catch_all) == 3
        assert sub.sentence == leather.overview.lede[1]
        assert sub.open_question is None
    assert [craft.catch_all for craft in subs[FOOTWEAR].crafts] == [False, False, False, True]
    assert leather.category.craft_count == 6
    assert leather.overview.lede[1].crafts[:2] == ["Kolhapuri-Chappal", "Chamba-Chappal"]


def test_sources_are_numbered_from_one_in_the_order_the_page_first_cites_them(leather: CategoryPage) -> None:
    numbers = {source.id: source.number for source in leather.sources}
    assert numbers[str(curation_id("S10"))] == 1
    assert numbers[str(curation_id("S05"))] == 2
    assert sorted(numbers.values()) == list(range(1, len(leather_plain()["sources"]) + 1))


def test_the_page_lists_only_claims_its_parts_cite_and_the_hero_is_an_open_picture(
    leather: CategoryPage,
) -> None:
    listed = {claim.id for claim in leather.claims}
    assert listed == set(leather.referenced_claim_ids())
    assert listed == {curation_id(claim["id"]) for claim in leather_plain()["claims"]}
    assert leather.hero is not None and leather.hero.media.display == "INLINE"
    assert leather.hero.caption.startswith("A Kolhapuri chappal from Kolhapur")
    assert [p.caption for p in leather.pictures] == [p["caption"] for p in leather_plain()["pictures"]]
    assert [question.key for question in leather.open_questions] == ["O01"]
    assert [row.about for row in leather.sources_differ] == [
        "How many tanneries Kanpur and its Jajmau cluster hold"
    ]
    assert [term.label for term in leather.glossary] == ["tholu bommalata", "togalu gombeyata", "charmakara"]


def test_a_hidden_claim_takes_its_sentences_facts_and_coverage_with_it() -> None:
    records = leather_records()
    hidden = curation_id("C006")
    gone = {hidden, curation_id("C170")}
    page = category_page(replace(records, views=tuple(v for v in records.views if v.id not in gone)))
    assert hidden not in {claim.id for claim in page.claims}
    assert all(hidden not in s.claim_ids for s in page.overview.sentences())
    assert [fact.label for fact in page.overview.key_facts] == ["Tanning methods"]
    subs = {sub.slug: sub for sub in page.sub_categories}
    assert subs[FOOTWEAR].sentence == page.overview.lede[1]
    assert subs[FOOTWEAR].sentence.claim_ids == [curation_id("C014"), curation_id("C206")]
    assert subs[ARTICLES].sentence is not None and ARTICLES in subs[ARTICLES].sentence.sub_categories
    assert page.hero is not None and page.hero.caption.startswith("A Santiniketan leather bag")


def test_a_sub_category_no_source_covers_points_at_its_open_question() -> None:
    plain = leather_plain()
    for sentence in [*plain["overview"]["lede"], *plain["overview"]["sections"][0]["sentences"]]:
        sentence["subCategories"] = [slug for slug in sentence.get("subCategories", []) if slug != ARTICLES]
    plain["openQuestions"].append(
        {
            "id": "O02",
            "question": "No source was found on the other leather articles.",
            "subCategories": [ARTICLES],
        }
    )
    page = category_page(leather_records(plain))
    subs = {sub.slug: sub for sub in page.sub_categories}
    assert (subs[ARTICLES].sentence, subs[ARTICLES].open_question) == (None, "O02")
    gap = next(question for question in page.open_questions if question.key == "O02")
    assert (gap.claim_ids, gap.sub_categories) == ([], [ARTICLES])


def test_a_sentence_names_only_crafts_the_category_lists() -> None:
    records = leather_records()
    articles = records.category.sub_categories[1]
    kept = SubCategoryRecord(
        articles.slug,
        articles.name,
        articles.label,
        tuple(craft for craft in articles.crafts if craft.slug != "Kanpur-Saddlery"),
    )
    category = replace(records.category, sub_categories=(records.category.sub_categories[0], kept))
    page = category_page(replace(records, category=category))
    assert "Kanpur-Saddlery" not in page.overview.lede[1].crafts
    assert "Santiniketan-Leather-Goods" in page.overview.lede[1].crafts


def test_a_category_without_a_dossier_shows_its_sub_categories_and_counts_only() -> None:
    page = category_page_preview(PAPER)
    master = [craft for craft in load_master() if craft.category_slug == PAPER]
    assert (page.curated, page.curation, page.hero) == (False, None, None)
    assert (page.overview.lede, page.overview.sections, page.claims, page.sources) == ([], [], [], [])
    assert page.category.craft_count == sum(1 for craft in master if not craft.is_catch_all)
    assert [sub.slug for sub in page.sub_categories] == ["Paper-Crafts"]
    assert page.sub_categories[0].sentence is None


def test_the_list_counts_every_category_and_quotes_each_curated_lede() -> None:
    listing = category_list_preview([LEATHER_DOSSIER])
    master = load_master()
    assert [c.slug for c in listing.categories] == list(
        dict.fromkeys(craft.category_slug for craft in master)
    )
    for summary in listing.categories:
        members = [craft for craft in master if craft.category_slug == summary.slug]
        portal = summary.craft_count - sum(1 for craft in members if not craft.is_catch_all)
        assert portal >= 0 and summary.curated == (summary.slug == LEATHER)
    leather = next(summary for summary in listing.categories if summary.slug == LEATHER)
    assert leather.lede is not None and leather.lede.text == leather_plain()["overview"]["lede"][0]["text"]
    assert {c.source_id for c in leather.lede.citations} == {source.id for source in listing.sources}
    assert leather.hero is not None and leather.hero.media.display == "INLINE"
    assert category_list([leather_records()]).categories[0] == leather
