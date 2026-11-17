from __future__ import annotations

from collections import Counter

from app.models import enums as e
from app.services.curation_keys import DISCIPLINE_CONCEPT_TYPES, curated_id
from app.services.curation_rows import claim_source_id
from app.services.term_glossary import term_id

from .import_support import AJRAKH, expected_id, plan_of, raw

KACHCHH = 449
BARMER = 90
GUJARAT = 24
RAJASTHAN = 8


def test_claims_and_sources_take_the_plan_ids() -> None:
    plan = plan_of(AJRAKH)
    claims = {row["id"]: row for row in plan.part("claims")}
    assert expected_id("curation:Kutch-Ajrakh:C001") in claims
    assert len(claims) == len(raw(AJRAKH)["claims"]) == 132
    sources = {row["id"] for row in plan.part("sources")}
    assert expected_id("curation:Kutch-Ajrakh:S01") in sources
    assert len(sources) == 20


def test_sources_are_excerpts_imported_by_curation_with_their_reliability() -> None:
    plan = plan_of(AJRAKH)
    given = {source["id"]: source["reliability"] for source in raw(AJRAKH)["sources"]}
    for row in plan.part("sources"):
        assert row["origin"] == "IMPORT"
        assert row["storage"] == "EXCERPT"
        assert row["externalIds"]["systemActor"] == "curation"
        key = row["externalIds"]["curation"].split(":")[1]
        assert row["reliability"] == given[key]


def test_levels_follow_the_hypothesis_flag_and_sources_differ_follows_conflicts() -> None:
    plan = plan_of(AJRAKH)
    plain = raw(AJRAKH)
    conflicted = {claim_id for conflict in plain["conflicts"] for claim_id in conflict["claimIds"]}
    guessed = {claim["id"] for claim in plain["claims"] if claim.get("hypothesis")}
    rows = {row["id"]: row for row in plan.part("claims")}
    for claim in plain["claims"]:
        row = rows[curated_id(AJRAKH, claim["id"])]
        assert row["evidenceLevel"] == ("HYPOTHESIS" if claim["id"] in guessed else "PROVISIONAL")
        assert row["sourcesDiffer"] == (claim["id"] in conflicted)
        assert (row["origin"], row["status"], row["subjectType"]) == ("IMPORT", "APPROVED", "CONCEPT")
    assert len(guessed) == 5


def test_every_quote_becomes_one_passing_citation() -> None:
    plan = plan_of(AJRAKH)
    quotes = {
        (claim["id"], quote["sourceId"], quote["quote"])
        for claim in raw(AJRAKH)["claims"]
        for quote in claim["quotes"]
    }
    citations = plan.part("claimSources")
    assert len(citations) == len(quotes) == 269
    assert {row["quoteCheck"] for row in citations} == {"PASS"}
    claim, source, quote = sorted(quotes)[0]
    assert claim_source_id(AJRAKH, claim, source, quote) in {row["id"] for row in citations}


def test_craft_claims_sit_on_one_concept_per_discipline() -> None:
    plan = plan_of(AJRAKH)
    concepts = {row["id"]: row for row in plan.part("concepts")}
    crafted = [
        row
        for row in plan.part("claims")
        if concepts[row["subjectId"]]["originRef"].endswith(":craft:HISTORY")
    ]
    assert crafted and {concepts[row["subjectId"]]["type"] for row in crafted} == {"HISTORICAL_CONTEXT"}
    assert set(DISCIPLINE_CONCEPT_TYPES) == set(e.DISCIPLINES)
    assert set(DISCIPLINE_CONCEPT_TYPES.values()) <= set(e.CONCEPT_TYPES)


def test_one_place_with_several_roles_is_one_concept() -> None:
    plan = plan_of(AJRAKH)
    dhamadka = [place for place in plan.index.places if place.name == "Dhamadka"]
    assert [place.role for place in dhamadka] == ["PRACTISED", "HISTORIC_CENTRE", "MIGRATED_FROM"]
    assert len({place.concept_id for place in dhamadka}) == 1


def test_villages_land_in_their_district_and_only_where_the_craft_is_made() -> None:
    plan = plan_of(AJRAKH)
    found = {(row["placeLabel"], row["role"]): row for row in plan.part("locations")}
    for village in ("Ajrakhpur", "Dhamadka", "Khavda"):
        row = found[(village, "PRACTISED")]
        assert (row["precision"], row["districtLgd"], row["stateLgd"]) == ("DISTRICT", KACHCHH, GUJARAT)
    assert (found[("Barmer", "PRACTISED")]["districtLgd"], found[("Barmer", "PRACTISED")]["stateLgd"]) == (
        BARMER,
        RAJASTHAN,
    )
    assert {label for label, _role in found}.isdisjoint({"Sindh", "Pethapur", "Dhamadka River (Suran)"})
    assert all(row["sourceId"] in {s["id"] for s in plan.part("sources")} for row in found.values())
    pethapur = next(place for place in plan.index.places if place.name == "Pethapur")
    assert (pethapur.role, pethapur.location_id, pethapur.district_lgd) == ("MATERIAL_SOURCE", None, 446)


def test_stages_are_ordered_only_where_the_dossier_orders_them() -> None:
    plan = plan_of(AJRAKH)
    stages = {row["name"]: row for row in plan.part("stages")}
    assert len(stages) == 14
    assert (stages["Scouring"]["ordinal"], stages["Scouring"]["ordered"]) == (1, True)
    unordered = sorted((row["ordinal"], row["name"]) for row in stages.values() if not row["ordered"])
    assert unordered == [(12, "Sun bleaching on the river bank"), (13, "Final wash"), (14, "Block carving")]
    assert len({row["ordinal"] for row in stages.values()}) == 14


def test_reactions_without_formulas_are_kept_as_text() -> None:
    plan = plan_of(AJRAKH)
    reactions = plan.part("reactions")
    assert len(reactions) == 2
    assert all(not row["balanced"] and row["equationBalanced"] is None for row in reactions)
    assert "indigo dye on the fibres from the vat + oxygen → blue indigo" in {
        row["label"] for row in reactions
    }
    cited = {row["id"] for row in plan.part("claimSources")}
    assert {row["claimSourceId"] for row in plan.part("reactionCitations")} <= cited


def test_tools_are_stage_materials_with_the_tool_role() -> None:
    plan = plan_of(AJRAKH)
    roles = Counter(row["role"] for row in plan.part("stageMaterials"))
    tool_uses = sum(len(stage.get("tools", [])) for stage in raw(AJRAKH)["stages"])
    assert roles["TOOL"] == tool_uses == 3


def test_pictures_are_inline_under_their_open_licence() -> None:
    plan = plan_of(AJRAKH)
    media = plan.part("media")
    assert len(media) == 4
    assert {row["display"] for row in media} == {"INLINE"}
    assert {row["provider"] for row in media} == {"curation"}
    assert len(plan.part("mediaClaims")) == 4


def test_glossary_spellings_become_label_and_aliases() -> None:
    plan = plan_of(AJRAKH)
    terms = {row["key"]: row for row in plan.part("terms")}
    assert terms["saaj"]["aliases"] == ["saaji", "neerani"]
    assert terms["kut"]["aliases"] == ["kat"]
    assert terms["saaj"]["id"] == term_id("saaj")
    assert len(plan.part("termCrafts")) == len(terms) == 17


def test_gi_and_market_records_keep_what_the_dossier_states() -> None:
    plan = plan_of(AJRAKH)
    (gi,) = plan.part("giRecords")
    assert (gi["applicationNumber"], gi["registeredOn"], gi["journalIssue"]) == ("1050", "2024-04-22", "188")
    assert gi["proprietors"] == ["Ajarakhpur Hastkala Vikas Sangathan"]
    (price,) = plan.part("prices")
    assert (price["pricedOn"], price["placeName"], price["districtLgd"]) == ("1975", "Barmer", BARMER)
    assert sorted(row["year"] for row in plan.part("workforce")) == [1970, 1990, 2001, 2011, 2023]


def test_a_shared_doi_points_every_reference_at_the_kept_source() -> None:
    plan = plan_of(AJRAKH)
    first, second = plan.part("sources")[:2]
    moved = plan.with_sources({first["id"]: second["id"]})
    assert first["id"] not in {row["id"] for row in moved.part("sources")}
    assert first["id"] not in {row["sourceId"] for row in moved.part("claimSources")}
    assert first["id"] not in {row["sourceId"] for row in moved.part("locations")}
