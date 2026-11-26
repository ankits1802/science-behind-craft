import base64
import re

import pytest

from app.models.page_previews import PREVIEW_DRAWINGS
from app.research.component_specs_plates_parts import PICTURE_PATTERN
from app.research.monograph_page import LayoutEntry
from app.research.page_render import (
    DESKTOP_WIDTH,
    DRAWING_STATES,
    IMAGE_BYTES_MAX,
    PHONE_WIDTH,
    PICTURE_HOSTS,
    VIEW_HEIGHTS,
    RenderedImage,
    component_role,
    image_bytes,
    kept_images,
    render_plan,
)

from .page_report_rules_fixtures import FIGURE, PICTURE, page_document


def image(name: str, size: int) -> RenderedImage:
    data = base64.b64encode(b"x" * size).decode("ascii")
    return RenderedImage(name=name, caption=name, width=10, height=10, data=data)


def test_the_page_is_drawn_at_a_phone_s_width_and_a_desktop_s() -> None:
    assert (PHONE_WIDTH, DESKTOP_WIDTH) == (390, 1440)
    assert (VIEW_HEIGHTS[PHONE_WIDTH], VIEW_HEIGHTS[DESKTOP_WIDTH]) == (844, 900)


@pytest.mark.parametrize(
    ("kind", "role"),
    [
        ("picture_plate", "picture"),
        ("map_layer", "map"),
        ("timeline_map", "map"),
        ("why_here", "map"),
        ("chart", "chart"),
        ("reaction_player", "interactive"),
        ("dip_player", "interactive"),
        ("molecule_3d", "interactive"),
        ("fact_table", "figure"),
        ("citation_tool", "figure"),
    ],
)
def test_each_component_is_checked_by_its_role(kind: str, role: str) -> None:
    assert component_role(kind) == role


def test_the_plan_names_each_component_its_masthead_and_the_chapters_after_the_opening() -> None:
    plan = render_plan(page_document())
    assert [(c.label, c.role, c.placed) for c in plan.components] == [
        (PICTURE, "picture", True),
        (FIGURE, "figure", True),
    ]
    assert plan.masthead == PICTURE
    assert plan.chapters == ["chem"]


def test_a_toggle_its_lab_draws_is_checked_inside_the_lab_and_a_toggle_with_no_lab_is_placed_alone() -> None:
    base = page_document()
    lab, toggle, alone = (
        "test-craft/chemistry/lab",
        "test-craft/chemistry/inside",
        "test-craft/chemistry/alone",
    )
    template = next(component for component in base.content.components if component.label == FIGURE)
    added = [
        template.model_copy(update={"label": label, "kind": kind})
        for label, kind in ((lab, "experiment_lab"), (toggle, "choice_toggle"), (alone, "choice_toggle"))
    ]
    layout = [
        *base.content.layout,
        *(LayoutEntry(chapter="chem", kind="component", ref=entry.label, within=None) for entry in added),
    ]
    content = base.content.model_copy(
        update={"components": [*base.content.components, *added], "layout": layout}
    )
    specs = {**base.specs, lab: {"experiments": [{"key": "inside", "toggle": {"component": toggle}}]}}
    plan = render_plan(base.model_copy(update={"content": content, "specs": specs}))
    placed = {component.label: (component.role, component.placed) for component in plan.components}
    assert placed[lab] == ("interactive", True)
    assert placed[toggle] == ("interactive", False)
    assert placed[alone] == ("interactive", True)


def test_a_picture_s_size_is_its_decoded_bytes() -> None:
    assert image_bytes(RenderedImage(name="a", caption="a", width=1, height=1, data="AAAA")) == 3


def test_the_pictures_kept_stay_within_the_total_in_their_order() -> None:
    images = [image("a", 400_000), image("b", 400_000), image("c", 300_000), image("d", 100_000)]
    kept = kept_images(images, most=1_000_000)
    assert [found.name for found in kept] == ["a", "b", "d"]
    assert sum(map(image_bytes, kept)) == 900_000
    assert IMAGE_BYTES_MAX == 1_000_000


def test_the_renderer_reaches_only_the_picture_host_the_spec_allows_beside_the_site() -> None:
    hosts = {
        host.replace("\\.", ".")
        for host in re.findall(r"https://((?:[a-z0-9-]+\\\.)+[a-z]+)", PICTURE_PATTERN)
    }
    assert hosts == set(PICTURE_HOSTS) == {"upload.wikimedia.org"}


def test_the_drawing_states_are_the_preview_row_s() -> None:
    assert DRAWING_STATES == PREVIEW_DRAWINGS == ("CHECKED", "FAILED", "UNMADE")
