from __future__ import annotations

import math

__all__ = [
    "channels",
    "contrast",
    "delinear",
    "delta_e",
    "fmt_oklch",
    "from_oklch",
    "hex_to_oklab",
    "hex_to_rgb",
    "linear",
    "luminance",
    "oklch",
    "rgb_to_hex",
]


def hex_to_rgb(colour: str) -> tuple[float, float, float]:
    digits = colour.lstrip("#")
    red, green, blue = (int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return red, green, blue


def _byte(value: float) -> int:
    return max(0, min(255, round(value * 255)))


def rgb_to_hex(red: float, green: float, blue: float) -> str:
    return f"#{_byte(red):02X}{_byte(green):02X}{_byte(blue):02X}"


def linear(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def delinear(value: float) -> float:
    return 12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055


def luminance(colour: str) -> float:
    red, green, blue = (linear(x) for x in hex_to_rgb(colour))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first: str, second: str) -> float:
    one, two = luminance(first), luminance(second)
    high, low = max(one, two), min(one, two)
    return (high + 0.05) / (low + 0.05)


def hex_to_oklab(colour: str) -> tuple[float, float, float]:
    red, green, blue = (linear(x) for x in hex_to_rgb(colour))
    long_cone = 0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue
    mid_cone = 0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue
    short_cone = 0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue
    lc, mc, sc = long_cone ** (1 / 3), mid_cone ** (1 / 3), short_cone ** (1 / 3)
    return (
        0.2104542553 * lc + 0.7936177850 * mc - 0.0040720468 * sc,
        1.9779984951 * lc - 2.4285922050 * mc + 0.4505937099 * sc,
        0.0259040371 * lc + 0.7827717662 * mc - 0.8086757660 * sc,
    )


def oklab_to_hex(lightness: float, green_red: float, blue_yellow: float) -> str:
    lc = lightness + 0.3963377774 * green_red + 0.2158037573 * blue_yellow
    mc = lightness - 0.1055613458 * green_red - 0.0638541728 * blue_yellow
    sc = lightness - 0.0894841775 * green_red - 1.2914855480 * blue_yellow
    long_cone, mid_cone, short_cone = lc**3, mc**3, sc**3
    red = 4.0767416621 * long_cone - 3.3077115913 * mid_cone + 0.2309699292 * short_cone
    green = -1.2684380046 * long_cone + 2.6097574011 * mid_cone - 0.3413193965 * short_cone
    blue = -0.0041960863 * long_cone - 0.7034186147 * mid_cone + 1.7076147010 * short_cone
    return rgb_to_hex(delinear(max(0, red)), delinear(max(0, green)), delinear(max(0, blue)))


def oklch(colour: str) -> tuple[float, float, float]:
    lightness, green_red, blue_yellow = hex_to_oklab(colour)
    chroma = math.hypot(green_red, blue_yellow)
    hue = math.degrees(math.atan2(blue_yellow, green_red)) % 360
    return lightness, chroma, hue


def from_oklch(lightness: float, chroma: float, hue: float) -> str:
    return oklab_to_hex(lightness, chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue)))


def fmt_oklch(colour: str) -> str:
    lightness, chroma, hue = oklch(colour)
    return f"oklch({lightness:.3f} {chroma:.3f} {hue:.1f})"


def delta_e(first: str, second: str) -> float:
    return 100 * math.dist(hex_to_oklab(first), hex_to_oklab(second))


def channels(colour: str) -> str:
    return " ".join(str(round(v * 255)) for v in hex_to_rgb(colour))
