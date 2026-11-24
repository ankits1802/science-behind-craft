from app.research.datasets import BOUNDARY_CAPTION
from app.services.page_export_document import export_specs, page_export
from app.services.page_export_figures import PAPER_NOTES
from app.services.page_export_kit import KIT_MOTION_NOTE
from app.services.page_export_model import ExportFigure
from app.services.page_export_units import PageTexts

from .page_fixture import FIXTURE_LABELS, NEW_KINDS, fixture_export, fixture_page, kutch_document

KUTCH = "Kutch-Ajrakh"
LAID_OUT = (
    "timeline_map",
    "diagram_kit",
    "stage_player",
    "swatch_cards",
    "reaction_player",
    "dip_player",
    "molecule_3d",
    "experiment_lab",
    "choice_toggle",
    "choice_toggle_copper",
    "label_card",
)
REPLACED = ("u0301", "u0411", "u0501", "u0601", "u0605", "u0608", "u0611", "u0614", "u0617", "u0701", "u0901")
STILLS = {
    "timeline_map": 1,
    "diagram_kit": 1,
    "swatch_cards": 2,
    "reaction_player": 1,
    "dip_player": 2,
    "stage_player": 2,
    "molecule_3d": 1,
    "label_card": 1,
    "experiment_lab": 0,
    "choice_toggle": 0,
    "choice_toggle_copper": 0,
}


def figure(name: str) -> ExportFigure:
    return next(shown for shown in fixture_export().figures() if shown.label == FIXTURE_LABELS[name])


def lines(name: str) -> list[str]:
    return [line.plain for line in figure(name).lines]


def test_every_new_kind_is_one_figure_in_the_order_the_page_lays_it_out_with_its_stills() -> None:
    assert sorted(LAID_OUT) == sorted(NEW_KINDS)
    assert [shown.label for shown in fixture_export().figures()] == [
        FIXTURE_LABELS[name] for name in LAID_OUT
    ]
    assert {name: len(figure(name).stills) for name in NEW_KINDS} == STILLS
    assert [chapter.title for chapter in fixture_export().chapters] == [
        "Every new kind",
        "History",
        "How it is made",
        "The chemistry",
        "Market and GI",
    ]


def test_the_timeline_map_rests_on_its_last_year_with_every_place_numbered_cited_and_credited() -> None:
    shown = figure("timeline_map")
    assert shown.title == "Where bidri was made, from Bidar to Lucknow"
    found = lines("timeline_map")
    assert "1. Bidar (this craft's place)" in found and "2. Hyderabad" in found and "5. Lucknow" in found
    assert (
        "1422–1436: The start of bidri at Bidar is attributed to the reign of Ahmed Shah Bahamani, "
        "who ruled from 1422 to 1436. [2, 3]"
    ) in found
    assert (
        "Bidar to Hyderabad, 1956: Many artisans from Bidar migrated to Hyderabad, and after the 1956 "
        "reorganisation of states many came to Hyderabad City in 1956 and 1957. [3, 4]"
    ) in found
    assert BOUNDARY_CAPTION in found
    assert shown.credits[0] == (
        "Indian district boundaries, matched to LGD codes · 2026 · 2026 · "
        "simplified to 0.01 degree, 0.001 degree coordinate grid · For reference only"
    )
    assert shown.note == PAPER_NOTES["timeline_map"]


def test_a_composed_diagram_names_each_panel_its_change_and_the_parts_it_draws() -> None:
    assert figure("diagram_kit").title == "From zinc-white to black"
    found = lines("diagram_kit")
    assert found[1] == "1. Sanded level"
    assert "2. In the bath" in found and "→ dipped" in found and "3. Lifted out" in found
    assert any(line.startswith("Drawn: Zinc-white alloy, inlaid with silver [") for line in found)
    assert figure("diagram_kit").note == KIT_MOTION_NOTE


def test_the_colour_key_names_each_colour_what_gives_it_and_its_swatches() -> None:
    found = lines("swatch_cards")
    assert "1. Patina" in found and "2. Inlay" in found
    assert "Given by: Fort earth and ammonium chloride [2, 4]" in found
    assert "Swatches: Sanded alloy, zinc-white [2, 4] becomes After the bath, black [2, 4]" in found
    assert "Swatches: Silver inlay becomes Silver after the bath [2, 4]" in found
    assert figure("swatch_cards").note is None


def test_a_reaction_player_lists_every_step_and_rests_on_the_one_the_page_opens_on() -> None:
    found = lines("reaction_player")
    assert "1. Zinc dissolves (as the page opens)" in found and "2. Copper darkens" in found
    assert "Zinc leaves the surface" in found
    assert any(
        line.startswith("Species: Zinc-copper alloy") and "Copper-rich surface" in line for line in found
    )
    assert any(line.endswith("Copper oxides (CuO, Cu₂O)") for line in found)
    assert any(
        line.startswith("Solution: Ammonium chloride and potassium nitrate in water [") for line in found
    )
    assert figure("reaction_player").note == PAPER_NOTES["reaction_player"]


def test_a_dip_and_a_stage_player_list_their_phases_and_stages_in_order() -> None:
    dip = lines("dip_player")
    assert any(line.startswith("1. In the bath: The finished article is dipped") for line in dip)
    assert any(line.startswith("3. Oiled: The blackened piece is polished") for line in dip)
    assert "The phases of the dip (1, 2): The surface before and after" in dip
    stage = lines("stage_player")
    assert (
        "1. Rough core model" in stage
        and "Model after: Black core" in stage
        and "5. Firing, dewaxing and casting" in stage
    )
    assert figure("stage_player").note == PAPER_NOTES["stage_player"]


def test_a_molecule_gives_its_name_formula_record_and_key() -> None:
    found = lines("molecule_3d")
    assert found[:3] == [
        "Ammonium chloride · NH₄Cl · PubChem CID 25517",
        "Nitrogen, hydrogen and chlorine",
        "Its record is PubChem's",
    ]
    assert "Key: Nitrogen; Hydrogen; Chlorine" in found
    assert figure("molecule_3d").title.startswith(
        "Ammonium chloride goes into the boiling fort-earth bath. ["
    )


def test_a_label_card_lab_and_toggles_give_their_facts_choices_and_results() -> None:
    assert figure("label_card").title == "Bidriware's GI registration"
    assert any(
        line.startswith("Certificate: Number 21, issued on 30 January 2006 [") for line in lines("label_card")
    )
    assert lines("experiment_lab") == [
        "Choose an experiment",
        "1. The bath (drawn in the figure Which bath blackens the alloy?)",
        "2. The copper (drawn in the figure What does the copper do?)",
    ]
    toggle = lines("choice_toggle")
    assert "Fort earth: Bidar fort earth" in toggle and "Two salts: A laboratory solution" in toggle
    assert figure("choice_toggle").title == "Which bath blackens the alloy?"


def test_every_unit_placed_in_a_component_is_drawn_in_its_figure() -> None:
    page = fixture_page()
    texts = PageTexts(page.content)
    held = [entry for entry in page.content.layout if entry.kind == "unit" and entry.within]
    for entry in held:
        if entry.ref in REPLACED:
            continue
        shown = next(found for found in fixture_export().figures() if found.label == entry.within)
        words = texts.plain(entry.ref)
        assert any(words in line.plain for line in shown.lines) or words in shown.title, (entry.ref, words)


def test_a_unit_no_builder_names_is_still_given_in_its_figure() -> None:
    page = fixture_page()
    label = FIXTURE_LABELS["molecule_3d"]
    extra = page.content.units["u0101"].model_copy(update={"chapter": "chemistry"})
    layout = [*page.content.layout]
    layout.insert(
        layout.index(next(e for e in layout if e.ref == "u0702")) + 1,
        layout[2].model_copy(update={"ref": "u9999", "within": label, "chapter": "chemistry"}),
    )
    content = page.content.model_copy(
        update={"units": {**page.content.units, "u9999": extra}, "layout": layout}
    )
    shown = page_export(page.model_copy(update={"content": content}), page.specs)
    molecule = next(found for found in shown.figures() if found.label == label)
    assert molecule.lines[-1].plain == "Where bidri was made, from Bidar to Lucknow"


def test_kutch_ajrakh_exports_every_component_chapter_and_source_once() -> None:
    document = kutch_document()
    content = document.content
    export = page_export(document, export_specs(document))
    labels = [shown.label for shown in export.figures()]
    assert sorted(labels) == sorted(component.label for component in content.components) and len(labels) == 80
    assert all(shown.title for shown in export.figures())
    assert len(export.references) == len(content.sources) == 69
    titles = [chapter.title for chapter in export.chapters]
    assert titles == [chapter.title for chapter in content.chapters if chapter.title in titles]
    assert "The chemistry" in titles and "Sources" in titles
    assert sum(len(shown.stills) for shown in export.figures()) >= 10
