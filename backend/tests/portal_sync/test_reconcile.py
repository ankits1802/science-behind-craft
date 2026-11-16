import hashlib
import uuid
from dataclasses import replace

import pytest

from app.core.errors import InvalidInput
from app.services.portal_craft_feed import parse_feed
from app.services.portal_craft_plan import KnownCraft
from app.services.portal_craft_reconcile import plan_sync
from tests.portal_sync.fixtures import (
    BLOCK_PRINTING,
    SYNCED_AT,
    craft,
    designer_payload,
    edited,
    field_payload,
    known_state,
)

CRAFT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "craft-master.kalavigyan")


def designer(payload=None):
    return parse_feed(payload or designer_payload(), portal="DESIGNER")


def field(payload=None):
    return parse_feed(payload or field_payload(), portal="FIELD_REPOSITORY")


def by_slug(plan):
    return {write.slug: write for write in plan.crafts}


def stable_craft_id(slug: str) -> str:
    master_id = "cmc" + hashlib.md5(f"c:{slug}".encode()).hexdigest()[:22]
    return str(uuid.uuid5(CRAFT_NAMESPACE, master_id))


def test_both_portals_plan_new_crafts_with_stable_ids_and_sources() -> None:
    plan = plan_sync([field(), designer()], known_state(), synced_at=SYNCED_AT)
    writes = by_slug(plan)
    assert plan.portals == ("DESIGNER", "FIELD_REPOSITORY")
    assert set(writes) == {
        "Dabu-Print",
        "Dabu-Printing",
        "Kutch-Ajrakh",
        "Sanjhi",
        "Bagru-Print",
        "Pattachitra-Odisha",
    }
    assert sorted(slug for slug, write in writes.items() if write.insert) == [
        "Dabu-Print",
        "Dabu-Printing",
        "Pattachitra-Odisha",
        "Sanjhi",
    ]
    dabu = writes["Dabu-Print"]
    assert dabu.id == stable_craft_id("Dabu-Print")
    assert (dabu.status, dabu.merged_into_slug) == ("ACTIVE", None)
    assert dabu.columns.name == "Dabu Print"
    assert dabu.columns.local_name == "दाबू"
    assert dabu.columns.sub_category_slug == BLOCK_PRINTING
    assert dabu.columns.category == "Textiles based Craft Category"
    assert dabu.columns.craft_code == "dabu"
    assert dabu.meta["portalOrigin"] == "DESIGNER"
    assert list(dabu.meta["portalSources"]) == ["DESIGNER", "FIELD_REPOSITORY"]
    assert dabu.meta["portalSources"]["FIELD_REPOSITORY"]["slug"] == "dabu-print"
    assert dabu.meta["portalSources"]["DESIGNER"]["syncedAt"] == SYNCED_AT


def test_master_crafts_keep_name_status_and_metadata() -> None:
    writes = by_slug(plan_sync([designer(), field()], known_state(), synced_at=SYNCED_AT))
    ajrakh = writes["Kutch-Ajrakh"]
    assert (ajrakh.insert, ajrakh.columns, ajrakh.status) == (False, None, None)
    assert ajrakh.meta["masterId"] == "cmc1"
    assert ajrakh.meta["portalSources"]["DESIGNER"]["name"] == "Ajrakh"
    assert "portalOrigin" not in ajrakh.meta
    bagru = writes["Bagru-Print"]
    assert bagru.status is None
    assert bagru.meta["portalSources"]["FIELD_REPOSITORY"]["status"] == "MERGED"
    assert bagru.meta["portalSources"]["FIELD_REPOSITORY"]["mergedIntoSlug"] == "Dabu-Print"


def test_merge_redirects_and_status_across_portals() -> None:
    writes = by_slug(plan_sync([designer(), field()], known_state(), synced_at=SYNCED_AT))
    printing = writes["Dabu-Printing"]
    assert (printing.status, printing.merged_into_slug) == ("MERGED", "Dabu-Print")
    assert writes["Sanjhi"].status == "ACTIVE"
    assert writes["Pattachitra-Odisha"].columns.sub_category_slug is None
    assert writes["Pattachitra-Odisha"].meta["portalOrigin"] == "FIELD_REPOSITORY"


def test_taxonomy_codes_and_spellings_only_add_what_is_missing() -> None:
    plan = plan_sync([designer(), field()], known_state(), synced_at=SYNCED_AT)
    assert [(c.slug, c.name, c.sort_order) for c in plan.categories] == [("Paper-Crafts", "Paper Crafts", 9)]
    assert [(s.slug, s.category_slug) for s in plan.sub_categories] == [("Paper-Cutting", "Paper-Crafts")]
    assert [c.code for c in plan.codes] == ["dabu", "patta"]
    assert [s.spelling for s in plan.spellings] == ["daboo"]
    assert by_slug(plan)["Sanjhi"].columns.category == "Paper Crafts"


def test_aliases_carry_the_portal_and_skip_the_stored_name() -> None:
    plan = plan_sync([designer(), field()], known_state(), synced_at=SYNCED_AT)
    rows = [(a.craft_slug, a.alias, a.alias_norm, a.script, a.lang, a.source) for a in plan.aliases]
    assert rows == [
        ("Dabu-Print", "दाबू", "दाबू", "Deva", "hi", "DR_SYNC"),
        ("Kutch-Ajrakh", "Ajrakh", "ajrakh", "Latn", "en", "DR_SYNC"),
        ("Kutch-Ajrakh", "Ajrak", "ajrak", "Latn", "en", "DR_SYNC"),
        ("Kutch-Ajrakh", "अजरख", "अजरख", "Deva", "hi", "DR_SYNC"),
    ]


def test_field_repository_aliases_are_fr_sync() -> None:
    payload = edited(field_payload(), lambda p: p["crafts"][0].update(aliases=["Daboo work"]))
    plan = plan_sync([field(payload)], known_state(), synced_at=SYNCED_AT)
    assert ("dabu-print", "Daboo work", "daboo work", "FR_SYNC") in [
        (a.craft_slug, a.alias, a.alias_norm, a.source) for a in plan.aliases
    ]


def test_a_craft_no_portal_lists_any_more_becomes_legacy() -> None:
    gone = KnownCraft(
        "Old-Craft",
        "Old Craft",
        BLOCK_PRINTING,
        "ACTIVE",
        None,
        {
            "portalOrigin": "DESIGNER",
            "portalSources": {"DESIGNER": {"status": "ACTIVE", "mergedIntoSlug": None}},
        },
    )
    writes = by_slug(plan_sync([designer()], known_state(gone), synced_at=SYNCED_AT))
    assert (writes["Old-Craft"].status, writes["Old-Craft"].columns) == ("LEGACY", None)
    assert writes["Old-Craft"].meta["portalSources"] == {}


def test_a_portal_missing_from_this_run_keeps_its_recorded_source() -> None:
    kept = KnownCraft(
        "Kept-Craft",
        "Kept Craft",
        BLOCK_PRINTING,
        "ACTIVE",
        None,
        {"portalOrigin": "FIELD_REPOSITORY", "portalSources": {"FIELD_REPOSITORY": {"status": "ACTIVE"}}},
    )
    writes = by_slug(plan_sync([designer()], known_state(kept), synced_at=SYNCED_AT))
    assert "Kept-Craft" not in writes


def test_a_rename_onto_another_crafts_name_keeps_the_stored_name() -> None:
    alpha = KnownCraft("Alpha", "Alpha", BLOCK_PRINTING, "ACTIVE", None, {"portalOrigin": "DESIGNER"})
    beta = KnownCraft("Beta", "Beta", BLOCK_PRINTING, "ACTIVE", None, {"portalOrigin": "DESIGNER"})
    payload = edited(designer_payload(), lambda p: p["crafts"].append(craft("d9", "Alpha", "Beta")))
    plan = plan_sync([designer(payload)], known_state(alpha, beta), synced_at=SYNCED_AT)
    assert by_slug(plan)["Alpha"].columns is None
    assert plan.name_conflicts == ("Alpha: 'Beta' is already the name of Beta",)
    assert ("Alpha", "Beta") in [(a.craft_slug, a.alias) for a in plan.aliases]


def test_a_rename_to_a_free_name_updates_the_craft() -> None:
    alpha = KnownCraft("Alpha", "Alpha", BLOCK_PRINTING, "ACTIVE", None, {"portalOrigin": "DESIGNER"})
    payload = edited(designer_payload(), lambda p: p["crafts"].append(craft("d9", "Alpha", "Alpha Print")))
    plan = plan_sync([designer(payload)], known_state(alpha), synced_at=SYNCED_AT)
    assert by_slug(plan)["Alpha"].columns.name == "Alpha Print"
    assert plan.name_conflicts == ()


def test_a_redirect_into_a_merged_craft_follows_to_the_end() -> None:
    payload = edited(
        designer_payload(),
        lambda p: p["crafts"].extend(
            [
                craft("d8", "Old", "Old", status="MERGED", merged_into="d1"),
                craft("d9", "Older", "Older", status="MERGED", merged_into="d8"),
            ]
        ),
    )
    writes = by_slug(plan_sync([designer(payload)], known_state(), synced_at=SYNCED_AT))
    assert writes["Old"].merged_into_slug == "Kutch-Ajrakh"
    assert writes["Older"].merged_into_slug == "Kutch-Ajrakh"


def test_a_merge_loop_is_refused() -> None:
    known = known_state()
    looped_master = KnownCraft("Kutch-Ajrakh", "Ajrakh Print of Kutch", BLOCK_PRINTING, "MERGED", "Y", {})
    y = KnownCraft("Y", "Y", BLOCK_PRINTING, "MERGED", "Kutch-Ajrakh", {})
    rigged = replace(known, crafts=(looped_master, known.crafts[1], y))
    payload = edited(
        designer_payload(),
        lambda p: p["crafts"].append(craft("d9", "Z", "Z", status="MERGED", merged_into="d1")),
    )
    with pytest.raises(InvalidInput, match="loop"):
        plan_sync([designer(payload)], rigged, synced_at=SYNCED_AT)


def test_a_missing_master_craft_stops_the_sync() -> None:
    known = known_state()
    rigged = replace(known, master_slugs=frozenset({"Kutch-Ajrakh", "Never-Seeded"}))
    with pytest.raises(InvalidInput, match="run seed_crafts before the portal sync"):
        plan_sync([designer()], rigged, synced_at=SYNCED_AT)


def test_two_feeds_from_one_portal_are_refused() -> None:
    with pytest.raises(InvalidInput, match="DESIGNER more than once"):
        plan_sync([designer(), designer()], known_state(), synced_at=SYNCED_AT)


def test_the_order_feeds_arrive_in_does_not_change_the_plan() -> None:
    first = plan_sync([designer(), field()], known_state(), synced_at=SYNCED_AT)
    second = plan_sync([field(), designer()], known_state(), synced_at=SYNCED_AT)
    assert first == second
