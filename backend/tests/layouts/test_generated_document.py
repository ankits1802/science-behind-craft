import re
from pathlib import Path

import pytest

from app.research.component_specs import checked_spec
from app.research.monograph_document import MonographDocument
from app.research.monograph_page import render_nodes
from app.services.monograph_generated_assembly import assembled_document
from app.services.monograph_generated_drawings import Drawings

from .generated_parts import (
    ALUM,
    GI_JOURNAL,
    PLAYER,
    SURVEY,
    TEXT_ALUM,
    TEXT_BAGH,
    VAT_DIP,
    fragment_monograph,
    generated,
    hero_layout,
)

HERO = "bagh-print/pictures/i02"
MASTHEAD = [
    "masthead-kicker",
    "masthead-title",
    "label-place-term",
    "label-place",
    "label-gi-term",
    "label-gi",
]


@pytest.fixture
def document(tmp_path: Path) -> MonographDocument:
    built = assembled_document(generated(hero_layout()), Drawings(root=fragment_monograph(tmp_path)))
    assert built is not None
    return built


def sentence_id(document: MonographDocument, text: str) -> str:
    (found,) = [key for key, unit in document.content.units.items() if text in str(unit.nodes)]
    return found


def test_each_published_sentence_is_one_paragraph_in_its_fields_chapter(document: MonographDocument) -> None:
    alum = sentence_id(document, TEXT_ALUM.removesuffix(" red."))
    bagh = sentence_id(document, TEXT_BAGH.removesuffix(" river."))
    assert re.fullmatch(r"chemistry-[0-9a-f]{10}", alum) and re.fullmatch(r"overview-[0-9a-f]{10}", bagh)
    units = document.content.units
    assert (units[alum].chapter, units[alum].tag, units[alum].field, units[alum].claim_ids) == (
        "chem",
        "p",
        "CHEMISTRY",
        [str(ALUM)],
    )
    assert (units["h-chemistry"].tag, units["h-chemistry"].nodes) == ("h3", ["The chemistry"])
    assert not any("hidden measure" in str(unit.nodes) for unit in units.values())


def plate_units(document: MonographDocument, label: str) -> list[str]:
    figure = document.specs[label]["figure"]
    return [caption["unit"] for caption in figure["captions"]] + [figure["credit"]]


def placed(document: MonographDocument, chapter: str, label: str) -> list[tuple[str, str, str | None]]:
    return [(chapter, label, None), *[(chapter, unit, label) for unit in plate_units(document, label)]]


def test_the_page_reads_hero_masthead_pictures_text_then_components(document: MonographDocument) -> None:
    alum = sentence_id(document, "Alum fixes")
    bagh = sentence_id(document, "Bagh print is")
    assert [(e.chapter, e.ref, e.within) for e in document.content.layout] == [
        *placed(document, "glance", HERO),
        *[("glance", unit, HERO) for unit in MASTHEAD],
        *placed(document, "glance", "bagh-print/pictures/i01"),
        ("glance", "h-overview", None),
        ("glance", bagh, None),
        *placed(document, "chem", "bagh-print/pictures/i04"),
        *placed(document, "chem", "bagh-print/pictures/i03"),
        ("chem", "h-chemistry", None),
        ("chem", alum, None),
        ("chem", VAT_DIP, None),
        ("chem", PLAYER, None),
    ]
    assert [c.label for c in document.content.components] == [
        HERO,
        "bagh-print/pictures/i01",
        "bagh-print/pictures/i04",
        "bagh-print/pictures/i03",
        VAT_DIP,
        PLAYER,
    ]


def test_sources_are_numbered_in_reading_order_and_a_sentence_carries_the_cite_mark(
    document: MonographDocument,
) -> None:
    sources = document.content.sources
    assert [(key, s.number, s.title) for key, s in sources.items()] == [
        ("g1", 1, SURVEY),
        ("g2", 2, "Alum on cotton"),
        ("g3", 3, GI_JOURNAL),
    ]
    alum = sentence_id(document, "Alum fixes")
    assert render_nodes(document.content.units[alum].nodes, sources) == (
        '<span class="s">Alum fixes the madder <span class="nw">red.<button class="kcite" type="button" '
        f'data-c="{alum}" data-g="g2 g1" aria-haspopup="dialog" aria-expanded="false" '
        'aria-label="Sources 1 and 2" aria-description="Bagh survey; Alum on cotton">1,2</button></span></span>'
    )
    assert [(q.source, q.locator, q.quote) for q in document.content.citations[alum]] == [
        ("g2", "p. 1", "quote 1"),
        ("g1", "p. 2", "quote 2"),
    ]
    assert document.content.citation_claims[alum] == [str(ALUM)]


def test_the_masthead_and_label_card_come_from_the_record(document: MonographDocument) -> None:
    units = document.content.units
    assert [(units[key].tag, units[key].nodes) for key in MASTHEAD] == [
        ("p", [{"m": "span", "c": ["Monograph"]}, {"m": "span", "c": ["Textiles · Hand block printing"]}]),
        ("h1", ["Bagh Print"]),
        ("dt", ["Place"]),
        ("dd", ["Madhya Pradesh"]),
        ("dt", ["GI"]),
        ("dd", ["Registered geographical indication"]),
    ]
    assert all(units[key].claim_ids == [] for key in MASTHEAD)


def test_a_picture_is_drawn_from_its_spec_with_the_layouts_crop_and_caption(
    document: MonographDocument,
) -> None:
    units = document.content.units
    for label in (HERO, "bagh-print/pictures/i04"):
        checked_spec("picture_plate", document.specs[label])
    caption, credit = plate_units(document, HERO)
    assert units[caption].nodes == ["Override caption"]
    assert document.specs[HERO]["picture"]["focal"] == {"x": 0.2, "y": 0.2, "width": 0.6, "height": 0.6}
    opener = document.specs["bagh-print/pictures/i04"]
    caption, credit = plate_units(document, "bagh-print/pictures/i04")
    assert units[caption].nodes == ["Picture I04"]
    assert opener["picture"]["focal"] == {"x": 0.0, "y": 0.1, "width": 1.0, "height": 0.8}
    assert "CC BY-SA 4.0" in units[credit].nodes[0] and units[credit].nodes[0].startswith("Photo: ")
    entry = next(c for c in document.content.components if c.label == HERO)
    assert (entry.kind, entry.chapter, entry.field, entry.subjects) == (
        "picture_plate",
        "glance",
        "OVERVIEW",
        ["craft:Bagh-Print"],
    )


def test_a_component_takes_its_spec_or_its_monographs_fragment_and_one_without_either_is_left_out(
    document: MonographDocument,
) -> None:
    assert document.specs[PLAYER] == {"steps": [1, 2]}
    assert document.fragments[VAT_DIP] == (
        '<figure id="fig1"><figcaption><span class="s">Green at <span class="nw">first.<button class="kcite" '
        'type="button" data-c="kutch-ajrakh:chem:q6" data-g="g3" aria-haspopup="dialog" aria-expanded="false" '
        'aria-label="Source 3" aria-description="GI Journal">3</button></span></span></figcaption></figure>'
    )
    quotes = document.content.citations["kutch-ajrakh:chem:q6"]
    assert [(q.source, q.locator, q.quote) for q in quotes] == [("g3", "p. 8", "bright green")]
    assert document.content.citation_claims["kutch-ajrakh:chem:q6"] == ["C086"]
    labels = {c.label for c in document.content.components}
    assert "shared/chemistry/no-drawing" not in labels and "shared/chemistry/proposed-player" not in labels
    vat = next(c for c in document.content.components if c.label == VAT_DIP)
    assert (vat.chapter, vat.anchor, vat.subjects) == ("chem", "#fig1", ["compound:23035"])


def test_the_document_carries_its_subject_version_and_layout(document: MonographDocument) -> None:
    assert (document.subject_kind, document.subject_slug, document.title, document.version) == (
        "craft",
        "Bagh-Print",
        "Bagh Print",
        5,
    )
    assert document.page_url == "https://kalavigyan.example/crafts/Bagh-Print"
    assert document.content.data["page-layout"]["version"] == 2
    assert document.content.data["page-layout"]["entries"][0]["ref"] == HERO


def test_a_fragment_source_already_cited_on_the_page_keeps_its_number(tmp_path: Path) -> None:
    root = fragment_monograph(tmp_path, gi_url="https://example.org/alum")
    built = assembled_document(generated(), Drawings(root=root))
    assert built is not None
    assert list(built.content.sources) == ["g1", "g2"]
    assert 'data-g="g2"' in built.fragments[VAT_DIP]


def test_without_a_layout_the_dossier_placement_and_focal_box_stand(tmp_path: Path) -> None:
    built = assembled_document(generated(), Drawings(root=fragment_monograph(tmp_path)))
    assert built is not None
    caption, _ = plate_units(built, HERO)
    assert built.content.units[caption].nodes == ["Picture I02"]
    assert built.specs[HERO]["picture"]["focal"] == {"x": 0.0, "y": 0.1, "width": 1.0, "height": 0.8}
    assert built.content.data == {}
    assert built.content.layout[0].ref == HERO


def test_a_subject_with_no_visible_sentence_has_no_document(tmp_path: Path) -> None:
    assert assembled_document(generated(visible={}), Drawings(root=tmp_path)) is None
