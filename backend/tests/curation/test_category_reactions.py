from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.core.errors import InvalidInput
from app.curation.dossier import Dossier
from app.data.craft_master_loader import ID_NAMESPACE
from app.services.category_plan import category_plan
from app.services.category_preview import category_dossier_records
from app.services.curated_index import IndexReaction, IndexSpecies

from .category_support import LEATHER, leather_checked, leather_plain, leather_target, recheck

TEXTILES = "Textiles-Based-Craft-Category"


def textiles_claim(key: str) -> uuid.UUID:
    return uuid.uuid5(ID_NAMESPACE, f"curation:{TEXTILES}:{key}")


def leather_claim(key: str) -> uuid.UUID:
    return uuid.uuid5(ID_NAMESPACE, f"curation:{LEATHER}:{key}")


def test_a_family_dossier_s_reactions_are_indexed_without_a_stage_or_a_reaction_row() -> None:
    plain = leather_plain()
    plain["reactions"] = [
        {
            "id": "R01",
            "kind": "PRECIPITATION",
            "reactants": [{"name": "tannin"}, {"name": "collagen"}],
            "products": [{"name": "tanned leather"}],
            "claimIds": ["C003", "C004"],
        }
    ]
    dossier = Dossier.model_validate(plain)
    plan = category_plan(dossier, recheck(leather_checked()[1], dossier), leather_target())
    assert plan.index.reactions == [
        IndexReaction(
            key="R01",
            reaction_id=None,
            stage_key=None,
            kind="PRECIPITATION",
            reactants=[
                IndexSpecies(name="tannin", formula=None),
                IndexSpecies(name="collagen", formula=None),
            ],
            products=[IndexSpecies(name="tanned leather", formula=None)],
            claim_ids=[leather_claim("C003"), leather_claim("C004")],
        )
    ]
    assert plan.index.materials == []
    assert "reactions" not in plan.rows
    assert "materials" not in plan.rows


def test_a_family_dossier_without_reactions_indexes_none() -> None:
    dossier, check = leather_checked()
    assert category_plan(dossier, check, leather_target()).index.reactions == []


def test_the_textiles_family_preview_holds_its_indigo_chain_and_the_claims_it_cites() -> None:
    records = category_dossier_records(TEXTILES)
    assert records.curated is not None
    assert records.category.slug == TEXTILES
    chain = [
        (item.key, item.kind, [s.name for s in item.reactants], [s.name for s in item.products])
        for item in records.curated.reactions
    ]
    assert chain == [
        ("R01", "OTHER", ["indican"], ["indoxyl"]),
        ("R02", "REDOX", ["indoxyl", "air"], ["indigo"]),
        ("R03", "REDOX", ["indigo"], ["leucoindigo"]),
        ("R04", "REDOX", ["leucoindigo", "air"], ["indigo"]),
    ]
    assert records.curated.reactions[2].claim_ids == [
        textiles_claim("C108"),
        textiles_claim("C110"),
        textiles_claim("C215"),
    ]
    assert all(item.reaction_id is None and item.stage_key is None for item in records.curated.reactions)
    views = {view.id: view for view in records.views}
    cited = [claim_id for item in records.curated.reactions for claim_id in item.claim_ids]
    assert set(cited) <= set(views)
    sources = {citation["sourceId"] for claim_id in cited for citation in views[claim_id].citations}
    assert sources and sources <= set(records.sources)


def test_the_family_preview_refuses_an_unknown_category_or_a_missing_dossier(tmp_path: Path) -> None:
    with pytest.raises(InvalidInput, match="Kutch-Ajrakh is not a category of the master list"):
        category_dossier_records("Kutch-Ajrakh")
    with pytest.raises(InvalidInput, match=f"{LEATHER} has no category dossier in categories/"):
        category_dossier_records(LEATHER, directory=tmp_path)
