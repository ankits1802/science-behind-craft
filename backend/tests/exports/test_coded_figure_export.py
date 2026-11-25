from app.services.drawing_themes import themed_spec
from app.services.page_export_document import page_export
from app.services.page_export_model import ExportFigure
from app.services.page_export_words import PAPER_NOTES

from .page_fixture import fixture_page

LABEL = "bidriware/chemistry/patina-bath-figure"


def _figure(*, served: bool) -> ExportFigure:
    page = fixture_page(("coded_figure",))
    specs = {
        label: themed_spec("coded_figure", spec) if served else spec for label, spec in page.specs.items()
    }
    return next(shown for shown in page_export(page, specs).figures() if shown.label == LABEL)


def test_a_coded_figure_exports_as_its_still_with_its_cited_words_beneath() -> None:
    figure = _figure(served=True)
    assert figure.title.startswith("The black patina forms instantly when the alloy is immersed")
    (still,) = figure.stills
    assert (still.width, still.height) == (320.0, 200.0)
    drawn = [text.text for text in still.texts]
    assert "Bidri alloy" in drawn
    lines = [line.plain for line in figure.lines]
    assert any(line.startswith("20 g of ammonium chloride") for line in lines)
    assert any(line.startswith("The black patina forms instantly on immersion") for line in lines)
    assert figure.note == PAPER_NOTES["coded_figure"]


def test_a_stored_figure_without_its_served_still_is_cut_from_its_code_for_paper() -> None:
    assert len(_figure(served=False).stills) == 1
