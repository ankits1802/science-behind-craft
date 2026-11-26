import math

import pytest

from app.geo.map_base import (
    SITE_HEIGHT,
    SITE_WIDTH,
    WHOLE_SITE,
    BaseAsk,
    SiteBox,
    base_shapes,
    draws_district_lines,
    projected_frame,
    site_degrees,
    site_point,
)
from app.services.export_map_base import base_sources
from app.services.place_ground import stored_layers

WEST, SOUTH, EAST, NORTH = 68.206, 6.756, 97.394, 37.082
JAIPUR = 102
ROUNDING = 0.05


def _box(west: float, south: float, east: float, north: float) -> SiteBox:
    corner, far = site_point(west, north), site_point(east, south)
    return SiteBox(corner[0], corner[1], far[0] - corner[0], far[1] - corner[1])


def test_the_paper_map_takes_the_web_map_s_projection() -> None:
    across = math.cos(math.radians(21.919))
    units = (1000 - 48) / ((EAST - WEST) * across)
    assert site_point(WEST, NORTH) == pytest.approx((24.0, 24.0))
    assert site_point(EAST, SOUTH) == pytest.approx((976.0, 24 + (NORTH - SOUTH) * units), rel=1e-4)
    assert pytest.approx((NORTH - SOUTH) * units + 48, rel=1e-4) == SITE_HEIGHT
    assert site_degrees(*site_point(75.79, 26.82)) == pytest.approx((75.79, 26.82))


def test_a_frame_holds_its_places_padded_and_shaped_as_the_web_frames_them() -> None:
    points = [(100.0, 200.0), (140.0, 230.0)]
    frame = projected_frame(points, min_share=0.035, padding_share=0.25)
    assert frame.width == pytest.approx(60.0)
    assert frame.height == pytest.approx(48.0)
    assert (frame.x, frame.y) == pytest.approx((90.0, 191.0))
    assert projected_frame([], min_share=0.035, padding_share=0.25) == WHOLE_SITE
    tiny = projected_frame([(500.0, 500.0)], min_share=0.035, padding_share=0.25)
    assert tiny.width == pytest.approx(SITE_WIDTH * 0.035)


def test_district_lines_show_in_a_zoomed_frame_or_when_asked() -> None:
    assert draws_district_lines(SiteBox(0, 0, SITE_WIDTH * 0.35, 100), asked=False)
    assert not draws_district_lines(WHOLE_SITE, asked=False)
    assert draws_district_lines(WHOLE_SITE, asked=True)


def test_the_base_of_a_zoomed_frame_holds_states_districts_and_coast_cut_to_the_frame() -> None:
    delhi = _box(76.8, 28.35, 77.6, 28.95)
    ask = BaseAsk(relief=True, rivers=True, districts=False, homes=(JAIPUR,))
    shapes = base_shapes(stored_layers(), base_sources(), delhi, ask)
    assert shapes.land and shapes.states and shapes.districts
    assert shapes.coast == () and shapes.homes == ()
    for line in (*shapes.states, *shapes.districts):
        for x, y in line:
            assert -ROUNDING <= x <= delhi.width + ROUNDING and -ROUNDING <= y <= delhi.height + ROUNDING
    jaipur = _box(75.0, 26.2, 76.6, 27.6)
    framed = base_shapes(stored_layers(), base_sources(), jaipur, ask)
    assert framed.homes and framed.relief
    kutch = _box(68.0, 22.6, 71.0, 24.6)
    coast = base_shapes(
        stored_layers(), base_sources(), kutch, BaseAsk(relief=False, rivers=False, districts=False)
    )
    assert coast.coast and coast.relief == () and coast.rivers == ()
