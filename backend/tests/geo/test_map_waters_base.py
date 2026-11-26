import pytest

from app.data.water_tiles import held_water_tile, held_waters_index
from app.geo.map_base import SITE_WIDTH, WHOLE_SITE, SiteBox, projected_frame, site_point
from app.geo.map_waters import NO_WATERS, WaterAsk, WaterTile, tiles_in_box, water_shapes, water_tile

SURAN = "Suran"
TAPPAR = "Tappar Reservoir"
TAPPAR_AT = (70.1275, 23.2473)
SURAN_WEST, SURAN_EAST = 70.111, 70.161
DHAMADKA = (70.02, 23.28)


def kutch_box() -> SiteBox:
    return projected_frame(
        [site_point(*DHAMADKA), site_point(*TAPPAR_AT)], min_share=0.035, padding_share=0.25
    )


def tiles_of(box: SiteBox) -> list[WaterTile]:
    return [water_tile(held_water_tile(tile)) for tile in tiles_in_box(held_waters_index()["tiles"], box)]


def test_a_town_s_frame_reads_only_its_own_tiles_and_a_wide_frame_reads_none() -> None:
    box = kutch_box()
    assert box.width <= SITE_WIDTH * 0.35
    assert tiles_in_box(held_waters_index()["tiles"], box) == ["e068n22", "e070n22"]
    assert tiles_in_box(held_waters_index()["tiles"], WHOLE_SITE) == []
    assert water_shapes(tiles_of(box), WHOLE_SITE, WaterAsk(rivers=(SURAN,))) is NO_WATERS


def test_the_named_river_is_drawn_strong_on_its_own_line_and_the_dam_where_its_record_puts_it() -> None:
    box = kutch_box()
    drawn = water_shapes(tiles_of(box), box, WaterAsk(rivers=(SURAN,), dams=(TAPPAR,)))
    assert drawn.lines and drawn.drawn
    (suran,) = drawn.strong
    assert suran.name == SURAN and suran.lines
    west, east = site_point(SURAN_WEST, 23.3)[0] - box.x, site_point(SURAN_EAST, 23.3)[0] - box.x
    assert west - 0.5 <= suran.at[0] <= east + 0.5
    (dam,) = drawn.dams
    x, y = site_point(*TAPPAR_AT)
    assert dam.name == TAPPAR and dam.at == pytest.approx((x - box.x, y - box.y))
    assert all(0 <= px <= box.width and 0 <= py <= box.height for line in drawn.lines for px, py in line)


def test_a_name_the_waters_do_not_hold_draws_nothing_strong_and_marks_no_dam() -> None:
    box = kutch_box()
    drawn = water_shapes(tiles_of(box), box, WaterAsk(rivers=("Saraswati of Sanganer",), dams=("Tapar Dam",)))
    assert drawn.lines and drawn.strong == () and drawn.dams == ()


def test_a_coded_map_without_its_rivers_layer_draws_only_the_waters_it_names() -> None:
    box = kutch_box()
    named = water_shapes(tiles_of(box), box, WaterAsk(rivers=(SURAN,), dams=(TAPPAR,), plain=False))
    assert named.lines == () and len(named.strong) == 1 and len(named.dams) == 1
    assert not water_shapes(tiles_of(box), box, WaterAsk(plain=False)).drawn


def test_the_api_holds_the_tiles_the_web_map_lists_and_refuses_one_it_does_not() -> None:
    index = held_waters_index()
    assert [row["code"] for row in index["datasets"]] == ["OSM_WATERWAYS"]
    assert held_water_tile("e070n22")["tile"] == "e070n22"
    with pytest.raises(ValueError, match="no tile e999n99"):
        held_water_tile("e999n99")
