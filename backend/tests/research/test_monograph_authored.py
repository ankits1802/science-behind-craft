import json
from pathlib import Path
from typing import Any

import pytest

from app.core.errors import InvalidInput
from app.research.monograph_document import MonographDocument, fragment_file_name, spec_file_name
from app.research.monograph_page import (
    COMPONENT_SLOT,
    SLOT_PATTERN,
    MonographContent,
    render_nodes,
    slot_keys,
)
from app.scripts.build_monograph import document_text
from app.services import monograph_document as authored
from app.services.chapter_preview import PREVIEW_SITE

SLUG = "Authored-Test"
PLATE = "authored-test/design/plate"
PLAYER = "authored-test/chemistry/player"
GOLDEN = Path(__file__).resolve().parents[3] / "shared" / "monograph.document.golden.json"
PAGE_URL = "https://kalavigyan.example/crafts/Authored-Test"


def _content() -> MonographContent:
    component = {
        "chapter": "c",
        "title": "T",
        "description": "D.",
        "field": "CHEMISTRY",
        "fields": [],
        "subjects": [],
    }
    unit = {"chapter": "c", "tag": "p", "field": "CHEMISTRY", "claimIds": []}
    return MonographContent.model_validate(
        {
            "craftSlug": SLUG,
            "sources": {},
            "citations": {},
            "citationClaims": {},
            "data": {},
            "units": {"u1": unit | {"nodes": ["Alum & madder"]}, "u2": unit | {"nodes": ["Red"]}},
            "components": [
                component | {"label": PLATE, "anchor": "#plate", "kind": "picture_plate"},
                component | {"label": PLAYER, "anchor": "#red", "kind": "reaction_player"},
            ],
            "layout": [
                {"chapter": "c", "kind": "component", "ref": PLATE, "within": None},
                {"chapter": "c", "kind": "unit", "ref": "u1", "within": PLATE},
                {"chapter": "c", "kind": "component", "ref": PLAYER, "within": PLATE},
                {"chapter": "c", "kind": "unit", "ref": "u2", "within": PLAYER},
            ],
        }
    )


@pytest.fixture
def folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(authored, "MONOGRAPHS_DIR", tmp_path)
    root = tmp_path / SLUG
    (root / "fragments").mkdir(parents=True)
    (root / "specs").mkdir()
    (root / "content.json").write_bytes(_content().model_dump_json(by_alias=True).encode("utf-8"))
    fragments = {
        PLATE: '<figure id="plate"><kv-slot unit="u1"></kv-slot><kv-slot component="authored-test/chemistry/player"></kv-slot></figure>',
        PLAYER: '<div id="red"><kv-slot unit="u2"></kv-slot></div>',
    }
    for label, text in fragments.items():
        (root / "fragments" / fragment_file_name(label)).write_bytes(text.encode("utf-8"))
    return root


def _spec(folder: Path, label: str, value: Any) -> None:
    (folder / "specs" / spec_file_name(label)).write_bytes(json.dumps(value).encode("utf-8"))


def test_a_component_with_a_spec_file_is_drawn_from_it_and_every_other_from_its_filled_fragment(
    folder: Path,
) -> None:
    _spec(folder, PLAYER, {"steps": [{"label": "Alum"}]})
    document = authored.authored_document(
        authored.monograph_content(SLUG), title="Authored Test", page_url=PAGE_URL
    )
    assert (document.subject_kind, document.subject_slug, document.version) == ("craft", SLUG, 1)
    assert document.specs == {PLAYER: {"steps": [{"label": "Alum"}]}}
    assert document.fragments == {
        PLATE: '<figure id="plate">Alum &amp; madder<kv-slot component="authored-test/chemistry/player"></kv-slot></figure>'
    }


def test_a_spec_that_is_not_an_object_or_a_missing_fragment_is_refused(folder: Path) -> None:
    _spec(folder, PLAYER, ["steps"])
    with pytest.raises(InvalidInput, match="not a JSON object"):
        authored.authored_document(authored.monograph_content(SLUG), title="T", page_url=PAGE_URL)
    (folder / "specs" / spec_file_name(PLAYER)).unlink()
    (folder / "fragments" / fragment_file_name(PLATE)).unlink()
    with pytest.raises(InvalidInput, match="missing"):
        authored.authored_document(authored.monograph_content(SLUG), title="T", page_url=PAGE_URL)


def test_only_a_folder_with_content_is_authored(folder: Path) -> None:
    assert authored.has_authored_content(SLUG)
    assert not authored.has_authored_content("Not-Authored")


def test_a_documents_hash_ignores_its_stored_version_but_not_its_text(folder: Path) -> None:
    document = authored.authored_document(authored.monograph_content(SLUG), title="T", page_url=PAGE_URL)
    digest = authored.document_hash(document)
    assert authored.document_hash(document.model_copy(update={"version": 7})) == digest
    assert authored.document_hash(document.model_copy(update={"title": "U"})) != digest
    assert len(digest) == 64


@pytest.fixture(scope="module")
def ajrakh() -> MonographDocument:
    content = authored.monograph_content("Kutch-Ajrakh")
    return authored.authored_document(content, title="Kutch Ajrakh", page_url=PAGE_URL)


def test_the_ajrakh_document_draws_every_component_once_and_validates_from_its_json(
    ajrakh: MonographDocument,
) -> None:
    labels = {c.label for c in ajrakh.content.components}
    assert len(labels) == 79
    assert set(ajrakh.specs) | set(ajrakh.fragments) == labels
    assert not set(ajrakh.specs) & set(ajrakh.fragments)
    assert MonographDocument.model_validate(json.loads(authored.document_json(ajrakh))) == ajrakh


def test_each_ajrakh_fragment_holds_its_units_text_and_only_the_slots_of_components_within_it(
    ajrakh: MonographDocument,
) -> None:
    content = ajrakh.content
    for label, fragment in ajrakh.fragments.items():
        within = [entry for entry in content.layout if entry.within == label]
        nested = sorted(entry.ref for entry in within if entry.kind == "component")
        assert sorted(slot_keys(fragment, COMPONENT_SLOT)) == nested, label
        assert len(SLOT_PATTERN.findall(fragment)) == len(nested), label
        for entry in within:
            if entry.kind == "unit":
                assert render_nodes(content.units[entry.ref].nodes, content.sources) in fragment, entry.ref


def test_the_shared_golden_document_is_what_the_documented_command_writes() -> None:
    assert GOLDEN.read_bytes().decode("utf-8") == document_text("Kutch-Ajrakh", site=PREVIEW_SITE)
