import uuid

from app.research.craft_page import CraftPage, craft_page_text
from app.services.curation_keys import curated_id
from app.services.curation_preview import dossier_preview

from ..curation.import_support import AJRAKH, AJRAKH_GOLDEN, raw
from .golden import golden_json, golden_text, reproduces


def test_the_craft_page_golden_parses_and_matches_the_response_models() -> None:
    assert reproduces(CraftPage, AJRAKH_GOLDEN)


def test_the_craft_page_golden_is_the_kutch_ajrakh_dossier_as_served() -> None:
    assert craft_page_text(dossier_preview(AJRAKH)) == golden_text(AJRAKH_GOLDEN)


def test_the_golden_claims_are_the_dossier_claims() -> None:
    page = golden_json(AJRAKH_GOLDEN)
    expected = {str(curated_id(AJRAKH, claim["id"])) for claim in raw(AJRAKH)["claims"]}
    assert {claim["id"] for claim in page["claims"]} == expected
    assert uuid.UUID(page["craft"]["id"])
    assert page["curated"] is True
