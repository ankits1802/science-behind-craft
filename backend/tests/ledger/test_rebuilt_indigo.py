from app.services.ledgered_explainer import ledgered_explainer
from app.services.picture_sites import blocked_picture
from app.services.source_merge import source_keys

from .indigo_answer import recorded_indigo
from .indigo_blocks import INDIGO_CID, SHOPS
from .indigo_claims import FRATER_BOOK, GI_COPY, KHAMIR_PART
from .shown import blocks_of, claims_of, repeated_sentences, restated

RECORDED = recorded_indigo()
REBUILT = ledgered_explainer(RECORDED)


def kinds(kind: str) -> list:
    return [block for block in blocks_of(REBUILT) if block.kind == kind]


def test_the_recorded_answer_repeats_itself_as_the_indigo_answer_did() -> None:
    blocks = blocks_of(RECORDED)
    assert repeated_sentences(blocks) == 29
    assert [block.id for block in blocks if getattr(block, "pubchem_cid", None) == INDIGO_CID] == [
        "s1.b3",
        "s1.b4",
        "s1.b6",
        "s3.b3",
        "s3.b4",
        "s3.b11",
    ]


def test_the_rebuilt_answer_shows_each_sentence_once() -> None:
    assert repeated_sentences(blocks_of(REBUILT)) == 0


def test_a_prose_card_or_expert_sentence_always_adds_a_claim_not_yet_shown() -> None:
    assert restated(blocks_of(REBUILT)) == []


def test_one_indigo_card_and_one_indigo_molecule() -> None:
    cards = [card.id for card in kinds("material_card") if card.pubchem_cid == INDIGO_CID]
    molecules = [molecule.id for molecule in kinds("molecule_3d")]
    assert (cards, molecules) == (["s1.b3"], ["s1.b6"])


def test_a_card_leaves_out_what_its_section_s_prose_already_says() -> None:
    (prose, card) = (REBUILT.sections[0].blocks[0], REBUILT.sections[0].blocks[1])
    said = {claim for sentence in prose.cited_sentences() for claim in claims_of(sentence)}
    assert card.kind == "material_card"
    assert all(not claims_of(fact) <= said for fact in card.facts)


def test_each_concept_is_drawn_once() -> None:
    terms = [node.term_key for graph in kinds("concept_graph") for node in graph.nodes]
    assert terms == ["indigo", "alum", "alizarin"]


def test_no_picture_comes_from_a_shop_or_a_social_site() -> None:
    items = [item for block in kinds("images") for item in block.items]
    assert items
    for item in items:
        media = item.media
        assert not blocked_picture(page_url=media.page_url, image_url=media.image_url, title=media.title)
        assert not any(shop.split(".")[0] in media.page_url for shop in SHOPS)


def test_each_section_shows_at_most_one_picture_and_none_twice() -> None:
    shown = [[item.media.id for item in block.items] for block in kinds("images")]
    assert all(len(items) == 1 for items in shown)
    assert len({media for items in shown for media in items}) == len(shown)


def test_an_expert_seat_is_kept_only_for_a_claim_not_yet_shown() -> None:
    assert [view.seat for view in kinds("expert_view")] == ["CHEMIST", "TECHNOLOGIST"]


def test_each_source_is_listed_once() -> None:
    keys = [key for source in REBUILT.sources for key in source_keys(source.model_dump(by_alias=True))]
    assert len(keys) == len(set(keys))
    titles = [source.title for source in REBUILT.sources]
    assert sum("Journal No. 188" in title for title in titles) == 1
    assert sum("Indigo in Kutch" in title for title in titles) == 1
    assert sum("Art of Ajrakh" in title or "art of Ajrakh" in title for title in titles) == 1
    assert sum("Caste Dress to Catwalk" in title for title in titles) == 1
    listed = {source.id for source in REBUILT.sources}
    assert {GI_COPY["id"], KHAMIR_PART["id"]} <= listed


def test_a_merged_source_keeps_the_earliest_edition_year_and_fills_its_gaps() -> None:
    (frater,) = [source for source in REBUILT.sources if "Indigo in Kutch" in source.title]
    assert (frater.year, frater.authors) == (2024, list(FRATER_BOOK["authors"]))


def test_no_claim_the_prose_rested_on_is_lost() -> None:
    def prose_claims(blocks: list) -> set[str]:
        return {
            claim for b in blocks if b.kind == "prose" for s in b.cited_sentences() for claim in claims_of(s)
        }

    kept = {claim for block in blocks_of(REBUILT) for s in block.cited_sentences() for claim in claims_of(s)}
    assert prose_claims(blocks_of(RECORDED)) <= kept


def test_rebuilding_a_rebuilt_answer_changes_nothing() -> None:
    assert ledgered_explainer(REBUILT) == REBUILT
