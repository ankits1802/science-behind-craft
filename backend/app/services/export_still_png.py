from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from types import MappingProxyType
from typing import TYPE_CHECKING

from app.data.export_assets import font_files

from .export_stills import WHITE, Still, StillText

if TYPE_CHECKING:
    from PIL.ImageDraw import ImageDraw

__all__ = ["STILL_PIXELS", "StillPicture", "still_png"]

STILL_PIXELS = 1000
SUPERSAMPLE = 2
LATIN = "Latn"
TEXT_MIN_PIXELS = 12
ANCHORS: Mapping[str, str] = MappingProxyType({"start": "ls", "middle": "ms", "end": "rs"})


@dataclass(frozen=True)
class StillPicture:
    data: bytes
    width: int
    height: int


def still_png(still: Still, *, pixels: int = STILL_PIXELS) -> StillPicture | None:
    from PIL import Image, ImageDraw

    if not still.drawn or still.width <= 0 or still.height <= 0:
        return None
    scale = pixels / max(still.width, still.height)
    width, height = max(1, round(still.width * scale)), max(1, round(still.height * scale))
    drawn = Image.new("RGB", (width * SUPERSAMPLE, height * SUPERSAMPLE), WHITE)
    draw = ImageDraw.Draw(drawn)
    ratio = scale * SUPERSAMPLE
    for path in still.paths:
        points = [(x * ratio, y * ratio) for x, y in path.points]
        if path.fill is not None and len(points) > 2:
            draw.polygon(points, fill=path.fill)
        if path.line is not None:
            line = [*points, points[0]] if path.closed else points
            draw.line(line, fill=path.line, width=max(1, round(path.width * ratio)), joint="curve")
    for text in still.texts:
        _text(draw, text, ratio)
    shown = drawn.resize((width, height), Image.Resampling.LANCZOS)
    out = BytesIO()
    shown.save(out, format="PNG")
    return StillPicture(data=out.getvalue(), width=width, height=height)


def _text(draw: ImageDraw, text: StillText, ratio: float) -> None:
    from PIL import ImageFont

    size = max(TEXT_MIN_PIXELS * SUPERSAMPLE, round(text.size * ratio))
    font = ImageFont.truetype(str(font_files(LATIN).regular), size)
    x, y = text.at
    draw.text((x * ratio, y * ratio), text.text, fill=text.colour, font=font, anchor=ANCHORS[text.anchor])
