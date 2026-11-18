import uuid
from pathlib import Path

from app.research.craft_page import CraftPage, craft_page_text
from app.scripts.import_curation import main
from app.services.craft_page_preview import register_page
from app.services.curation_keys import curated_id
from app.services.curation_preview import dossier_preview

from ..curation.import_support import AJRAKH, AJRAKH_GOLDEN, raw
from .golden import golden_json, golden_text, reproduces

REGISTER_GOLDEN = "craft.page.register.golden.json"
REGISTER_CRAFT = "Farrukhabad-Prints"


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


def test_the_register_page_golden_parses_and_matches_the_response_models() -> None:
    assert reproduces(CraftPage, REGISTER_GOLDEN)


def test_the_register_page_golden_is_a_craft_without_a_dossier_beside_kutch_ajrakh() -> None:
    page = register_page(REGISTER_CRAFT, dossiers=[AJRAKH])
    assert craft_page_text(page) == golden_text(REGISTER_GOLDEN)
    assert (page.curated, page.claims, page.depth.basis) == (False, [], "REGISTER")


def test_the_documented_commands_write_both_goldens(tmp_path: Path) -> None:
    curated, register = tmp_path / AJRAKH_GOLDEN, tmp_path / REGISTER_GOLDEN
    assert main(["--preview", AJRAKH, "--out", str(curated)]) == 0
    assert main(["--register-preview", REGISTER_CRAFT, "--with-dossier", AJRAKH, "--out", str(register)]) == 0
    assert curated.read_bytes() == golden_text(AJRAKH_GOLDEN).encode("utf-8")
    assert register.read_bytes() == golden_text(REGISTER_GOLDEN).encode("utf-8")
