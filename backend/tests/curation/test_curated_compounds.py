import uuid
from datetime import UTC, datetime

from app.services.compound_lookup import record_source_id
from app.services.curated_compounds import curated_compound_id, curated_compounds
from app.services.curated_index import IndexMaterial

CURATED_AT = datetime(2026, 11, 17, 18, 17, tzinfo=UTC)
SODA_ASH = 10340
LIME = 6093208
INDIGO = 10215


def material(name: str, cid: int | None, number: int) -> IndexMaterial:
    return IndexMaterial(
        key=f"M{number:02d}",
        material_id=uuid.UUID(int=number),
        concept_id=uuid.UUID(int=100 + number),
        name=name,
        kind="MINERAL",
        role="INPUT",
        local_names=[],
        botanical_name=None,
        pubchem_cid=cid,
        claim_ids=[uuid.UUID(int=200 + number)],
    )


MATERIALS = [
    material("Soda ash", SODA_ASH, 3),
    material("Lime", LIME, 6),
    material("Indigo", INDIGO, 16),
    material("Cotton cloth", None, 1),
    material("Washing soda", SODA_ASH, 7),
]


def test_a_curated_cid_no_compound_holds_becomes_a_compound_named_by_its_first_material() -> None:
    plan = curated_compounds(MATERIALS, stored_cids={INDIGO}, stored_sources={}, retrieved_at=CURATED_AT)
    assert [(row["pubchemCid"], row["name"], row["formula"]) for row in plan.compounds] == [
        (SODA_ASH, "Soda ash", None),
        (LIME, "Lime", None),
    ]
    assert [row["id"] for row in plan.compounds] == [curated_compound_id(SODA_ASH), curated_compound_id(LIME)]
    assert [row["sourceId"] for row in plan.compounds] == [record_source_id(SODA_ASH), record_source_id(LIME)]


def test_each_new_compound_cites_its_pubchem_record_as_a_link_only_source() -> None:
    plan = curated_compounds(MATERIALS, stored_cids={INDIGO}, stored_sources={}, retrieved_at=CURATED_AT)
    source = plan.sources[0]
    assert (source["id"], source["kind"], source["url"], source["storage"], source["retrievedAt"]) == (
        record_source_id(SODA_ASH),
        "COMPOUND_RECORD",
        "https://pubchem.ncbi.nlm.nih.gov/compound/10340",
        "LINK_ONLY",
        CURATED_AT,
    )
    assert source["title"] == "Soda ash (PubChem CID 10340)"


def test_a_record_source_already_stored_for_the_cid_is_reused_not_written_again() -> None:
    held = uuid.UUID(int=999)
    plan = curated_compounds(
        MATERIALS, stored_cids={INDIGO}, stored_sources={SODA_ASH: held}, retrieved_at=CURATED_AT
    )
    assert [row["sourceId"] for row in plan.compounds] == [held, record_source_id(LIME)]
    assert [row["id"] for row in plan.sources] == [record_source_id(LIME)]


def test_nothing_is_planned_when_every_cid_has_its_compound() -> None:
    plan = curated_compounds(
        MATERIALS, stored_cids={SODA_ASH, LIME, INDIGO}, stored_sources={}, retrieved_at=CURATED_AT
    )
    assert (plan.compounds, plan.sources) == ((), ())


def test_a_compound_already_stored_under_the_material_s_name_without_a_cid_is_left_to_the_lookup() -> None:
    plan = curated_compounds(
        MATERIALS,
        stored_cids=set(),
        stored_sources={},
        retrieved_at=CURATED_AT,
        unlinked_names={"indigo", "lime"},
    )
    assert [row["pubchemCid"] for row in plan.compounds] == [SODA_ASH]
