import uuid
from types import MappingProxyType

from app.services.drawing_themes import themed_spec
from app.services.export_pictures import Picture
from app.services.page_export_document import page_export
from app.services.page_export_model import ExportFigure
from app.services.page_export_pictures import PagePictures, clip_still_src, wanted_pictures
from app.services.page_export_words import PAPER_NOTES

from .page_fixture import fixture_page

LABEL = "bidriware/chemistry/patina-bath-figure"
CLIP = uuid.UUID("2d4f6a8c-0e1b-4c3d-9e5f-7a9b1c3d5e7f")
CREDIT = "AI video, made with veo-3.1-fast on 2026-11-21"
STILL = Picture(data=b"\xff\xd8\xff\xe0still", width=1280, height=720)


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


def _filmed(pictures: PagePictures) -> tuple[ExportFigure, list[str]]:
    page = fixture_page(("coded_figure",))
    spec = dict(page.specs[LABEL])
    spec["code"] = spec["code"].replace("<ul ", '<video data-film="dip" controls></video><ul ', 1)
    spec["films"] = [{"key": "dip", "clip": str(CLIP), "credit": CREDIT}]
    specs = {**page.specs, LABEL: spec}
    figure = next(
        shown for shown in page_export(page, specs, pictures=pictures).figures() if shown.label == LABEL
    )
    return figure, [picture.image_url for picture in wanted_pictures(page, specs)]


def test_a_clip_s_still_and_credit_are_drawn_on_paper_beside_the_figure_s_own_still() -> None:
    figure, wanted = _filmed(PagePictures(MappingProxyType({f"/api/crafts/media/{CLIP}/still": STILL})))
    assert wanted == [f"https://kalavigyan.example/api/crafts/media/{CLIP}/still"]
    assert clip_still_src(CLIP) == f"/api/crafts/media/{CLIP}/still"
    assert len(figure.stills) == 1
    assert [shown.picture for shown in figure.pictures] == [STILL]
    assert figure.credits == (CREDIT,)


def test_a_clip_whose_still_could_not_be_read_keeps_its_credit_and_no_picture() -> None:
    figure, _ = _filmed(PagePictures())
    assert figure.pictures == () and figure.credits == (CREDIT,)
    assert len(figure.stills) == 1
