import uuid

import pytest

from app.research.crafts import CraftResolution
from app.services.craft_index import CraftRecord, build_index
from app.services.craft_matching import SemanticHit, lexical_match, resolution_from, slug_resolution

from .craft_fixtures import BAGRU, BARMER, KUTCH, LUCKNOW, OTHERS, PHULKARI, ZARI, craft_id, sample_index

INDEX = sample_index()


def resolve(text: str, semantic: tuple[SemanticHit, ...] = ()) -> CraftResolution:
    return resolution_from(INDEX, lexical_match(INDEX, text), semantic)


def ranking(resolution: CraftResolution) -> list[tuple[str, float]]:
    return [(c.craft.slug, c.score) for c in resolution.candidates]


def reasons(resolution: CraftResolution, rank: int = 0) -> list[tuple[str, str, float]]:
    return [(r.kind, r.matched, r.score) for r in resolution.candidates[rank].reasons]


def slug_of(identifier: uuid.UUID) -> str:
    return INDEX.refs[identifier].slug


def test_a_full_name_in_a_question_wins_over_the_alias_inside_it() -> None:
    found = resolve("Why is Kutch Ajrakh dyed twice?")
    assert found.status == "RESOLVED"
    assert found.craft is not None and found.craft.slug == "Kutch-Ajrakh"
    assert ranking(found) == [("Kutch-Ajrakh", 1.0)]
    assert reasons(found) == [("EXACT_NAME", "Kutch Ajrakh", 1.0)]
    assert (found.normalised, found.script) == ("why is kutch ajrakh dyed twice", "Latn")


def test_an_alias_two_crafts_share_offers_both() -> None:
    found = resolve("How is Ajrakh washed?")
    assert found.status == "AMBIGUOUS"
    assert found.craft is None
    assert ranking(found) == [("Barmer-Ajrakh-Print", 0.97), ("Kutch-Ajrakh", 0.97)]


def test_a_named_state_settles_a_shared_alias() -> None:
    found = resolve("ajrakh from Rajasthan")
    assert found.status == "RESOLVED"
    assert ranking(found) == [("Barmer-Ajrakh-Print", 0.976), ("Kutch-Ajrakh", 0.776)]
    assert reasons(found) == [("EXACT_ALIAS", "Ajrakh", 0.97), ("PLACE", "Rajasthan", 1.0)]


def test_a_state_no_candidate_is_practised_in_changes_nothing() -> None:
    found = resolve("bagru from gujarat")
    assert found.status == "RESOLVED"
    assert ranking(found) == [("Bagru-Hand-Block-Print", 0.97)]


def test_devanagari_is_matched_through_its_spoken_latin_form() -> None:
    found = resolve("बगरू")
    assert found.status == "RESOLVED"
    assert ranking(found) == [("Bagru-Hand-Block-Print", 0.97)]
    assert reasons(found) == [("EXACT_ALIAS", "Bagru", 0.97)]
    assert (found.normalised, found.script) == ("bagaru", "Deva")


def test_a_merged_craft_name_redirects_to_its_target() -> None:
    found = resolve("Ajrakh Printing of Kutch")
    assert ranking(found) == [("Kutch-Ajrakh", 0.97)]
    assert reasons(found) == [("MERGED_REDIRECT", "Ajrakh Printing of Kutch", 0.97)]
    by_slug = slug_resolution(INDEX, "Ajrakh-Printing-Of-Kutch", "why indigo")
    assert by_slug.status == "RESOLVED"
    assert ranking(by_slug) == [("Kutch-Ajrakh", 1.0)]
    assert reasons(by_slug) == [("MERGED_REDIRECT", "Ajrakh-Printing-Of-Kutch", 1.0)]


def test_legacy_and_catch_all_crafts_match_only_by_slug() -> None:
    assert resolve("namda felt").status == "NONE"
    assert resolve("others").status == "NONE"
    assert slug_resolution(INDEX, "Namda-Felt", "namda").status == "NONE"
    picked = slug_resolution(INDEX, "Others-Textile", "what is this")
    assert picked.craft is not None and picked.craft.slug == slug_of(OTHERS)
    assert reasons(picked) == [("EXACT_SLUG", "Others-Textile", 1.0)]


def test_an_unknown_slug_resolves_to_nothing() -> None:
    found = slug_resolution(INDEX, "kutch-ajrakh", "why indigo")
    assert (found.status, found.candidates) == ("NONE", [])


def test_shared_spellings_rank_below_a_curated_alias() -> None:
    assert ranking(resolve("zardozi")) == [(slug_of(LUCKNOW), 0.97), (slug_of(ZARI), 0.95)]
    assert resolve("zardozi").status == "AMBIGUOUS"
    only = resolve("zardosi")
    assert only.status == "RESOLVED"
    assert ranking(only) == [(slug_of(ZARI), 0.95)]
    assert reasons(only) == [("EXACT_SPELLING", "Zardosi", 0.95)]


def test_a_misspelling_resolves_through_fuzzy_similarity() -> None:
    found = resolve("phulkri")
    assert found.status == "RESOLVED"
    assert found.candidates[0].craft.slug == slug_of(PHULKARI)
    assert found.candidates[0].score == pytest.approx(0.886666, abs=1e-6)
    assert [(kind, matched) for kind, matched, _ in reasons(found)] == [
        ("FUZZY", "Phulkari"),
        ("FAMILY", "phulkari"),
    ]


def test_an_equal_misspelling_of_a_shared_alias_stays_ambiguous() -> None:
    found = resolve("ajrak")
    assert found.status == "AMBIGUOUS"
    assert ranking(found) == [("Barmer-Ajrakh-Print", 0.863636), ("Kutch-Ajrakh", 0.863636)]


def test_semantic_agreement_lifts_a_lexical_candidate() -> None:
    hits = (SemanticHit(KUTCH, 0.9), SemanticHit(BARMER, 0.5), SemanticHit(BAGRU, 0.7))
    found = resolve("ajrak", hits)
    assert found.status == "AMBIGUOUS"
    assert ranking(found) == [
        ("Kutch-Ajrakh", 0.913636),
        ("Barmer-Ajrakh-Print", 0.863636),
        ("Bagru-Hand-Block-Print", 0.56),
    ]
    assert ("SEMANTIC", "Kutch Ajrakh", 0.9) in reasons(found)


def test_semantic_hits_alone_never_resolve() -> None:
    found = resolve("resist dyed cotton with indigo", (SemanticHit(KUTCH, 1.0), SemanticHit(BARMER, 0.75)))
    assert found.status == "AMBIGUOUS"
    assert ranking(found) == [("Kutch-Ajrakh", 0.8), ("Barmer-Ajrakh-Print", 0.6)]


def test_a_family_word_offers_at_most_five_crafts_in_name_order() -> None:
    places = ("Adilabad", "Bastar", "Bengal", "Chhattisgarh", "Jharkhand", "Odisha")
    crafts = [
        CraftRecord(craft_id(f"{p}-Dhokra"), f"{p}-Dhokra", f"{p} Dhokra", "ACTIVE") for p in reversed(places)
    ]
    index = build_index(crafts, [], [])
    found = resolution_from(index, lexical_match(index, "dhokra"))
    assert found.status == "AMBIGUOUS"
    assert ranking(found) == [(f"{p}-Dhokra", 0.7) for p in places[:5]]
    assert all(c.reasons[0].kind == "FAMILY" for c in found.candidates)


def test_a_question_naming_no_craft_resolves_to_nothing() -> None:
    found = resolve("What mordant fixes the colour?")
    assert (found.status, found.craft, found.candidates) == ("NONE", None, [])
