import zipfile
from io import BytesIO
from typing import Any

from app.research.monograph_document import MonographDocument
from app.research.page_passages import page_passages
from app.research.page_translation_gates import GateInput, refusal, translation_checks
from app.research.page_translation_variant import ServedTranslations, variant_content
from app.research.spec_texts import spec_texts, with_spec_texts
from app.research.translation_passages import passage_leaves, unit_hash
from app.services.page_export_document import page_export
from app.services.page_export_docx import page_docx
from app.services.page_export_model import ExportFigure, PageExport
from app.services.page_translation_serving import variant_body

from .page_fixture import FIXTURE_LABELS, fixture_page

REACTION = FIXTURE_LABELS["reaction_player"]
UNITS_HINDI = {
    "u0103": ["बीदर"],
    "u0204": ["समतल घिसा"],
    "u0306": ["परत"],
    "u0402": ["जस्ता सतह छोड़ता है"],
    "u0507": ["निकाला"],
    "u0606": ["काली मिट्टी का कोर"],
    "u0702": ["अमोनियम क्लोराइड उबलते किले-मिट्टी के ", "घोल में जाता है।"],
    "u0801": ["भौगोलिक संकेत"],
    "u1002": ["बीदर किले की मिट्टी"],
}
LABELS_HINDI = {
    "Zinc dissolves": "जस्ता घुलता है",
    "The phases of the dip": "डुबकी के चरण",
    "Rough core model": "कच्चा कोर मॉडल",
    "Ammonium chloride": "अमोनियम क्लोराइड",
    "The bath": "घोल",
    "Fort earth": "किले की मिट्टी",
}
REACTION_KEYS = [
    f"{REACTION}#steps.0.name",
    f"{REACTION}#steps.0.chemistry.parts.0.label",
    f"{REACTION}#steps.0.chemistry.parts.0.items.0.name",
    f"{REACTION}#steps.0.chemistry.parts.0.items.1.label",
    f"{REACTION}#steps.0.chemistry.parts.0.items.2.name",
    f"{REACTION}#steps.1.name",
    f"{REACTION}#steps.1.chemistry.parts.0.label",
    f"{REACTION}#steps.1.chemistry.parts.0.items.0.name",
    f"{REACTION}#steps.1.chemistry.parts.0.items.1.label",
    f"{REACTION}#steps.1.chemistry.parts.0.items.2.name",
]
MOLECULE_KEYS = [
    "molecules.0.name",
    "molecules.0.dialLabel",
    "molecules.0.atoms",
    "molecules.0.note",
    "key.0.label",
    "key.1.label",
    "key.2.label",
]


def served() -> ServedTranslations:
    units = fixture_page().content.units
    by_hash = {
        unit_hash(units[ref].nodes, units[ref].claim_ids): tuple(texts) for ref, texts in UNITS_HINDI.items()
    }
    labels = {unit_hash([english], []): (hindi,) for english, hindi in LABELS_HINDI.items()}
    return ServedTranslations(by_hash={**by_hash, **labels}, digest="d")


def hindi_page() -> MonographDocument:
    page = fixture_page()
    variant = variant_content(page.content, served(), language="hi", source_version=1, specs=page.specs)
    update: dict[str, Any] = {
        "language": "hi",
        "content": variant.content,
        "specs": dict(variant.specs),
        "translation": variant.translation,
    }
    return page.model_copy(update=update)


def figure(export: PageExport, name: str) -> ExportFigure:
    return next(shown for shown in export.figures() if shown.label == FIXTURE_LABELS[name])


def lines(export: PageExport, name: str) -> list[str]:
    return [line.plain for line in figure(export, name).lines]


def test_a_player_s_labels_are_offered_and_its_formulas_never_are() -> None:
    page = fixture_page()
    keys = [text.key for text in spec_texts(REACTION, "reaction_player", page.specs[REACTION])]
    assert keys == REACTION_KEYS
    molecule = FIXTURE_LABELS["molecule_3d"]
    assert [
        text.key.split("#")[1] for text in spec_texts(molecule, "molecule_3d", page.specs[molecule])
    ] == MOLECULE_KEYS
    assert (
        spec_texts(FIXTURE_LABELS["timeline_map"], "timeline_map", page.specs[FIXTURE_LABELS["timeline_map"]])
        == []
    )


def test_a_native_name_stays_as_its_source_gives_it() -> None:
    stage = FIXTURE_LABELS["stage_player"]
    spec = fixture_page().specs[stage]
    native = {**spec, "stages": [{**spec["stages"][0], "local": True}, *spec["stages"][1:]]}
    keys = {text.key for text in spec_texts(stage, "stage_player", native)}
    assert f"{stage}#stages.0.name" not in keys and f"{stage}#stages.0.english" in keys
    assert f"{stage}#stages.1.name" in keys


def test_the_fixture_page_offers_every_unit_and_every_label_of_its_new_kinds() -> None:
    page = fixture_page()
    offered = page_passages(page.content, page.specs)
    units = [key for key in offered if not key.count("#")]
    labels = [key for key in offered if key.count("#")]
    assert units == list(page.content.units) and len(units) == 116
    assert len(labels) == 43
    assert [key for key in labels if key.startswith(f"{REACTION}#")] == REACTION_KEYS
    assert [key.split("#")[1] for key in labels if key.startswith(FIXTURE_LABELS["dip_player"])] == [
        "stripLabel",
        "dipAgain",
    ]
    stage = [key.split("#")[1] for key in labels if key.startswith(FIXTURE_LABELS["stage_player"])]
    assert stage[0] == "play" and stage[-1] == "afterLabel" and len(stage) == 17
    passage = offered[f"{REACTION}#steps.0.name"]
    assert (passage.chapter, passage.tag, passage.claim_ids) == ("chemistry", "label", [])
    given = GateInput(
        leaves=passage.leaves(),
        current_hash=passage.source_hash,
        given_hash=passage.source_hash,
        texts=["जस्ता घुलता है"],
        language="hi",
    )
    assert refusal(translation_checks(given)) is None


def test_a_translated_unit_of_each_new_kind_is_drawn_and_an_untranslated_one_stays_english() -> None:
    page = hindi_page()
    assert page.translation is not None and (page.translation.translated, page.translation.passages) == (
        15,
        159,
    )
    export = page_export(page, page.specs)
    assert "1. बीदर (this craft's place)" in lines(export, "timeline_map")
    held = next(line for line in figure(export, "timeline_map").lines if line.plain == "2. Hyderabad")
    assert held.lang == "en"
    assert "1. समतल घिसा" in lines(export, "diagram_kit") and "2. In the bath" in lines(export, "diagram_kit")
    assert "1. परत" in lines(export, "swatch_cards")
    reaction = lines(export, "reaction_player")
    assert "1. जस्ता घुलता है (as the page opens)" in reaction and "2. Copper darkens" in reaction
    assert "जस्ता सतह छोड़ता है" in reaction
    assert any(
        line.startswith("2. निकाला: The zinc alloy comes out black") for line in lines(export, "dip_player")
    )
    assert any(line.startswith("डुबकी के चरण (1, 2): ") for line in lines(export, "dip_player"))
    assert "1. कच्चा कोर मॉडल" in lines(export, "stage_player") and "काली मिट्टी का कोर" in lines(
        export, "stage_player"
    )
    assert lines(export, "molecule_3d")[0] == "अमोनियम क्लोराइड · NH₄Cl · PubChem CID 25517"
    assert figure(export, "molecule_3d").title.startswith("अमोनियम क्लोराइड उबलते किले-मिट्टी के घोल में जाता है। [")
    assert "भौगोलिक संकेत" in lines(export, "label_card")
    assert lines(export, "experiment_lab")[1].startswith("1. घोल (drawn in the figure")
    assert "किले की मिट्टी: बीदर किले की मिट्टी" in lines(export, "choice_toggle")


def test_the_served_page_and_its_word_export_draw_the_translated_labels() -> None:
    page = fixture_page()
    body = variant_body(page.model_dump(mode="json", by_alias=True), page.content, served(), "hi")
    assert body is not None and body["language"] == "hi"
    assert body["specs"][REACTION]["steps"][0]["name"] == "जस्ता घुलता है"
    assert body["specs"][REACTION]["steps"][1]["name"] == "Copper darkens"
    data = page_docx(page_export(hindi_page(), hindi_page().specs))
    with zipfile.ZipFile(BytesIO(data)) as package:
        document = package.read("word/document.xml").decode("utf-8")
    assert "जस्ता घुलता है" in document and "बीदर" in document
    assert '<w:lang w:val="en" w:bidi="en"/>' in document


def test_a_label_translation_is_put_back_where_it_was_read() -> None:
    spec = fixture_page().specs[REACTION]
    [first, *_] = spec_texts(REACTION, "reaction_player", spec)
    species = next(text for text in spec_texts(REACTION, "reaction_player", spec) if text.rich)
    shown = with_spec_texts(spec, [(first, ["जस्ता घुलता है"]), (species, ["जस्ता-तांबा मिश्रधातु"])])
    assert shown["steps"][0]["name"] == "जस्ता घुलता है"
    assert shown["steps"][0]["chemistry"]["parts"][0]["items"][0]["name"] == ["जस्ता-तांबा मिश्रधातु"]
    assert spec["steps"][0]["name"] == "Zinc dissolves"
    assert passage_leaves(species.nodes)[0].text == "Zinc-copper alloy"
