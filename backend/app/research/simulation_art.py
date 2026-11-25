from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from html import unescape

from .art_kit import parts_named_by
from .drawing_roles import DRAWING_ROLES, INDIGO, MATERIAL_ROLES, css_declarations
from .drawn_art import KIT_POINTER, UI_SIZES_PX, drawn_art_problems
from .drawn_paints import CUSTOM_PREFIX
from .sandbox_markup import SandboxProblem
from .simulation_art_markup import PAINT_ATTRIBUTES, REST_PROPERTIES, ArtMarkup

__all__ = [
    "ART_RULE",
    "FACES",
    "FRAME_FLAG",
    "REDUCED_MOTION_FLAG",
    "TIMERS",
    "simulation_art_problems",
]

ART_RULE = "ART"
DRAWING_KIND = "drawing"
FIGURE_KEY = "figure"
FACES = frozenset({"var(--font-ui)", "var(--font-reading)", "inherit"})
REDUCED_MOTION_FLAG = "reducedMotion"
REDUCED_MOTION_ATTRIBUTE = "data-reduced-motion"
STYLE_ATTRIBUTE = "style"
PLAIN = frozenset({"none", "transparent", "currentcolor", "inherit", "initial", "unset"})
COLOUR_PROPERTIES = frozenset(
    {
        "color",
        "background",
        "background-color",
        "fill",
        "stroke",
        "stop-color",
        "flood-color",
        "lighting-color",
        "caret-color",
        "accent-color",
        "outline",
        "outline-color",
        "box-shadow",
        "text-shadow",
        "text-decoration",
        "text-decoration-color",
        "column-rule",
        "column-rule-color",
    }
)
NAMED_COLOURS = (
    "aliceblue|antiquewhite|aqua|aquamarine|azure|beige|bisque|black|blanchedalmond|blue|blueviolet|brown"
    "|burlywood|cadetblue|chartreuse|chocolate|coral|cornflowerblue|cornsilk|crimson|cyan|darkblue|darkcyan"
    "|darkgoldenrod|darkgray|darkgreen|darkgrey|darkkhaki|darkmagenta|darkolivegreen|darkorange|darkorchid"
    "|darkred|darksalmon|darkseagreen|darkslateblue|darkslategray|darkslategrey|darkturquoise|darkviolet"
    "|deeppink|deepskyblue|dimgray|dimgrey|dodgerblue|firebrick|floralwhite|forestgreen|fuchsia|gainsboro"
    "|ghostwhite|gold|goldenrod|gray|green|greenyellow|grey|honeydew|hotpink|indianred|indigo|ivory|khaki"
    "|lavender|lavenderblush|lawngreen|lemonchiffon|lightblue|lightcoral|lightcyan|lightgoldenrodyellow"
    "|lightgray|lightgreen|lightgrey|lightpink|lightsalmon|lightseagreen|lightskyblue|lightslategray"
    "|lightslategrey|lightsteelblue|lightyellow|lime|limegreen|linen|magenta|maroon|mediumaquamarine"
    "|mediumblue|mediumorchid|mediumpurple|mediumseagreen|mediumslateblue|mediumspringgreen|mediumturquoise"
    "|mediumvioletred|midnightblue|mintcream|mistyrose|moccasin|navajowhite|navy|oldlace|olive|olivedrab"
    "|orange|orangered|orchid|palegoldenrod|palegreen|paleturquoise|palevioletred|papayawhip|peachpuff|peru"
    "|pink|plum|powderblue|purple|rebeccapurple|red|rosybrown|royalblue|saddlebrown|salmon|sandybrown"
    "|seagreen|seashell|sienna|silver|skyblue|slateblue|slategray|slategrey|snow|springgreen|steelblue|tan"
    "|teal|thistle|tomato|turquoise|violet|wheat|white|whitesmoke|yellow|yellowgreen"
)
BORDER = re.compile(r"^border(?:-(?:top|right|bottom|left|block|inline)(?:-(?:start|end))?)?(?:-color)?$")
VAR = re.compile(r"var\(\s*--([a-z0-9-]+)")
BARE_VAR = re.compile(r"var\(\s*--[a-z0-9-]+\s*\)")
CHANNEL_PREFIX = "c-"
PAGE_TOKENS = DRAWING_ROLES | frozenset(token for face in FACES for token in VAR.findall(face))
LITERAL = re.compile(
    rf"#[0-9a-f]{{3,8}}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\(|\b(?:{NAMED_COLOURS})\b",
    re.IGNORECASE,
)
SCRIPT_LITERAL = re.compile(
    r"([\"'`])\s*(?:#[0-9a-f]{3,8}|(?:rgba?|hsla?|hwb|oklch|oklab)\([^\"'`]*\))\s*\1", re.IGNORECASE
)
SCRIPT_MATERIAL = re.compile(r"var\(\s*--((?:dye|dip)-[a-z0-9-]+)")
SCRIPT_ATTRIBUTE_PAINT = re.compile(
    r"setAttribute(?:NS)?\s*\(\s*(?:null\s*,\s*)?([\"'`])([\w-]+)\1\s*,\s*([\"'`])((?:(?!\3).)*)\3"
)
SCRIPT_STYLE_PAINT = re.compile(r"\.\s*style\s*\.\s*([A-Za-z]+)\s*=\s*([\"'`])((?:(?!\2).)*)\2")
SCRIPT_PROPERTY_PAINT = re.compile(
    r"\.\s*setProperty\s*\(\s*([\"'`])([\w-]+)\1\s*,\s*([\"'`])((?:(?!\3).)*)\3"
)
SCRIPT_CSS_TEXT = re.compile(r"\.\s*cssText\s*=\s*([\"'`])((?:(?!\1).)*)\1")
CAMEL = re.compile(r"[A-Z]")
PIXELS = re.compile(r"(\d+(?:\.\d+)?)px\b")
FONT_SIZE = re.compile(r"(?<![\w.-])(\d+(?:\.\d+)?)(px|r?em|%|pt|vw|vh)\b")
TIMERS = re.compile(r"(?<![\w$.])(?:setInterval|setTimeout|requestAnimationFrame)\s*\(")
FRAME_FLAG = re.compile(
    rf"\.\s*dataset\s*(?:\.\s*{REDUCED_MOTION_FLAG}(?![\w$])|\[\s*([\"'`]){REDUCED_MOTION_FLAG}\1\s*\])"
    rf"|\.\s*getAttribute\s*\(\s*([\"'`]){REDUCED_MOTION_ATTRIBUTE}\2\s*\)"
)
MOVING_ELEMENTS = frozenset(
    {"animate", "animatetransform", "animatemotion", "animatecolor", "set", "marquee"}
)
SCRIPT_MOTION = re.compile(
    r"\.\s*animate\s*\(|\.\s*beginElement(?:At)?\s*\(|(?<![\w$.])(?:Animation|KeyframeEffect)\s*\("
)
UNREAD_DRAWINGS = frozenset({"canvas"})
DATA_IMAGE = re.compile(r"data\s*:\s*image/", re.IGNORECASE)
SCRIPT_DRAWING = re.compile(r"(?<![\w$])(?:getContext|OffscreenCanvas|createElementNS)(?![\w$])")
NUMBER = re.compile(r"^(\d*\.?\d+)(%)?$")
SIZES = ", ".join(str(size) for size in UI_SIZES_PX)
STILL_STEPS = (
    "under either reduced-motion switch nothing moves, so the figure rests finished and Play steps it from a "
    "timer that reads document.documentElement.dataset.reducedMotion"
)


def simulation_art_problems(html: str) -> list[SandboxProblem]:
    markup = ArtMarkup()
    markup.feed(html)
    markup.close()
    found = [
        *_colour_problems(markup),
        *_type_problems(markup.styles),
        *_rest_problems(markup),
        *_motion_problems(markup),
        *_unread_drawing_problems(markup),
        *_pictured_problems(markup.pictured),
        *_data_image_problems(html),
        *drawn_art_problems(DRAWING_KIND, {FIGURE_KEY: markup.drawings}, {}),
    ]
    return [SandboxProblem(ART_RULE, detail) for detail in dict.fromkeys(found)]


def _declarations(styles: Iterable[str]) -> Iterator[tuple[str, str]]:
    for style in styles:
        yield from css_declarations(style)


def _colour_problems(markup: ArtMarkup) -> Iterator[str]:
    for name, value in _declarations(markup.styles):
        yield from _declared_paint_problems(name, value)
    for value in markup.paints:
        yield from _painted(value, control=False)
    for script in markup.scripts:
        for match in SCRIPT_LITERAL.finditer(script):
            yield f"the script paints {match.group(0)}; name a design role, var(--ink-1) and the like, instead"
        for match in SCRIPT_MATERIAL.finditer(script):
            yield _material(match.group(1))
        yield from _script_paint_problems(script)


def _script_paint_problems(script: str) -> Iterator[str]:
    for match in SCRIPT_ATTRIBUTE_PAINT.finditer(script):
        name, value = match.group(2).casefold(), match.group(4)
        if name in PAINT_ATTRIBUTES:
            yield from _painted(value, control=False)
        elif name == STYLE_ATTRIBUTE:
            yield from _style_paint_problems(value)
    for match in SCRIPT_STYLE_PAINT.finditer(script):
        named = CAMEL.sub(lambda capital: f"-{capital.group(0).lower()}", match.group(1))
        yield from _declared_paint_problems(named, match.group(3))
    for match in SCRIPT_PROPERTY_PAINT.finditer(script):
        yield from _declared_paint_problems(match.group(2).casefold(), match.group(4))
    for match in SCRIPT_CSS_TEXT.finditer(script):
        yield from _style_paint_problems(match.group(2))


def _style_paint_problems(style: str) -> Iterator[str]:
    for name, value in css_declarations(style):
        yield from _declared_paint_problems(name, value)


def _declared_paint_problems(name: str, value: str) -> Iterator[str]:
    if name.startswith(CUSTOM_PREFIX):
        yield from _custom_property_problems(name[len(CUSTOM_PREFIX) :], value)
    elif name in COLOUR_PROPERTIES or BORDER.match(name):
        yield from _painted(value, control=True)


def _custom_property_problems(token: str, value: str) -> Iterator[str]:
    if token.removeprefix(CHANNEL_PREFIX) in PAGE_TOKENS or INDIGO.match(token):
        yield (
            f"declares --{token}, a token the frame takes from the page, so a paint that names it would not be "
            "the role it says; name the design role as the page draws it and declare no token of the design"
        )
        return
    yield from _literal_problems(value)
    for role in VAR.findall(value):
        if role in MATERIAL_ROLES:
            yield _material(role)


def _literal_problems(value: str) -> Iterator[str]:
    for match in LITERAL.finditer(BARE_VAR.sub(" ", value)):
        yield (
            f"names the colour {match.group(0)!r}; name a design role instead: var(--ink-1) to var(--ink-3), "
            "var(--rule), var(--rule-strong), var(--ground), var(--raised), var(--sunk), a --chart-* role, "
            "and var(--indigo) only on a control"
        )


def _painted(value: str, *, control: bool) -> Iterator[str]:
    if " ".join(value.split()).casefold() in PLAIN:
        return
    yield from _literal_problems(value)
    for role in VAR.findall(value):
        if role in MATERIAL_ROLES:
            yield _material(role)
        elif INDIGO.match(role) and not control:
            yield f"--{role} is indigo, which means a control a reader can press, never a drawing"
        elif role not in DRAWING_ROLES and not INDIGO.match(role):
            yield f"--{role} is not one of the design's roles"


def _material(role: str) -> str:
    return f"paints --{role} by hand, which the site's kit draws textured, framed and named in a key; {KIT_POINTER}"


def _type_problems(styles: Iterable[str]) -> Iterator[str]:
    for name, value in _declarations(styles):
        if name == "font-family" and " ".join(value.split()) not in FACES:
            yield f"sets text in {value!r}; set it in var(--font-ui) or var(--font-reading)"
        if name == "font-size" and value.strip() != "inherit":
            yield from _size_problems(value)
        if name == "font":
            yield from _font_problems(value)


def _size_problems(value: str) -> Iterator[str]:
    sizes = FONT_SIZE.findall(value)
    if not sizes or any(unit != "px" or float(size) not in UI_SIZES_PX for size, unit in sizes):
        yield f"sets text at {value.strip()!r}, off the type scale; set it at {SIZES} px"


def _font_problems(value: str) -> Iterator[str]:
    compact = " ".join(value.split())
    if compact in PLAIN:
        return
    size = PIXELS.search(compact)
    if size is None:
        yield from _size_problems(compact)
        return
    yield from _size_problems(size.group(0))
    face = compact[size.end() :].split(" ", 1)[1] if " " in compact[size.end() :] else ""
    if face not in FACES:
        yield f"sets text in {face or compact!r}; set it in var(--font-ui) or var(--font-reading)"


def _rest_problems(markup: ArtMarkup) -> Iterator[str]:
    for name, value in (*_declarations(markup.styles), *markup.rests):
        found = NUMBER.match(value.strip()) if name in REST_PROPERTIES else None
        if found is None:
            continue
        amount = float(found.group(1)) / (100 if found.group(2) else 1)
        if amount < 1:
            yield (
                f"rests at {name} {value.strip()}: every end state is the default style, so the first paint "
                "shows the finished figure and nothing waits faded for Play"
            )


def _motion_problems(markup: ArtMarkup) -> Iterator[str]:
    for tag in dict.fromkeys(tag for tag in markup.tags if tag in MOVING_ELEMENTS):
        yield f"moves by <{tag}>, which neither reduced-motion switch stops; {STILL_STEPS}"
    for script in markup.scripts:
        for match in SCRIPT_MOTION.finditer(script):
            moved = " ".join(match.group(0).split())
            yield f"moves by the Web Animations API ({moved}), which neither reduced-motion switch stops; {STILL_STEPS}"
        if TIMERS.search(script) and not FRAME_FLAG.search(script):
            yield (
                "times its motion without reading document.documentElement.dataset.reducedMotion, which the "
                "frame sets under either reduced-motion switch; under it nothing moves and Play steps one stage "
                "a press"
            )


def _unread_drawing_problems(markup: ArtMarkup) -> Iterator[str]:
    for tag in dict.fromkeys(tag for tag in markup.tags if tag in UNREAD_DRAWINGS):
        yield f"draws on a <{tag}>, which the bar cannot read; draw the figure as static inline svg with a viewBox"
    for script in markup.scripts:
        for match in SCRIPT_DRAWING.finditer(script):
            yield (
                f"builds its drawing in the script ({match.group(0)}); draw the figure as static inline svg and "
                "let the script change only its attributes and text"
            )


def _data_image_problems(html: str) -> Iterator[str]:
    if DATA_IMAGE.search(unescape(html)):
        yield (
            "shows a data: image, which the bar cannot read as a drawing and neither reduced-motion switch "
            "holds still; draw the figure as static inline svg with a viewBox"
        )


def _pictured_problems(labels: Iterable[str]) -> Iterator[str]:
    for label in labels:
        for part, word in parts_named_by(label):
            yield f"a picture said to show {word} ({label!r}) is the kit's {part} part, which the site draws; {KIT_POINTER}"
