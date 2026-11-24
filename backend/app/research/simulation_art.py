from __future__ import annotations

import re
from collections.abc import Iterable, Iterator

from .art_kit import parts_named_by
from .drawing_roles import DRAWING_ROLES, INDIGO, MATERIAL_ROLES, css_declarations
from .drawn_art import KIT_POINTER, UI_SIZES_PX, drawn_art_problems
from .sandbox_markup import SandboxProblem
from .simulation_art_markup import ArtMarkup

__all__ = [
    "ART_RULE",
    "FACES",
    "REDUCED_MOTION_FLAG",
    "simulation_art_problems",
]

ART_RULE = "ART"
DRAWING_KIND = "drawing"
FIGURE_KEY = "figure"
FACES = frozenset({"var(--font-ui)", "var(--font-reading)", "inherit"})
REDUCED_MOTION_FLAG = "reducedMotion"
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
BORDER = re.compile(r"^border(?:-(?:top|right|bottom|left|block|inline)(?:-(?:start|end))?)?(?:-color)?$")
VAR = re.compile(r"var\(\s*--([a-z0-9-]+)")
BARE_VAR = re.compile(r"var\(\s*--[a-z0-9-]+\s*\)")
LITERAL = re.compile(
    r"#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\("
    r"|\b(?:white|black|red|green|blue|yellow|orange|purple|pink|brown|gr[ae]y|maroon|navy|teal|olive|lime"
    r"|aqua|cyan|magenta|fuchsia|silver|gold|beige|ivory|khaki|tan|crimson|coral|salmon|tomato|violet"
    r"|indigo|turquoise|wheat|linen|snow)\b",
    re.IGNORECASE,
)
SCRIPT_LITERAL = re.compile(
    r"([\"'`])\s*(?:#[0-9a-f]{3,8}|(?:rgba?|hsla?|hwb|oklch|oklab)\([^\"'`]*\))\s*\1", re.IGNORECASE
)
SCRIPT_MATERIAL = re.compile(r"var\(\s*--((?:dye|dip)-[a-z0-9-]+)")
PIXELS = re.compile(r"(\d+(?:\.\d+)?)px\b")
FONT_SIZE = re.compile(r"(?<![\w.-])(\d+(?:\.\d+)?)(px|r?em|%|pt|vw|vh)\b")
TIMERS = re.compile(r"(?<![\w$.])(?:setInterval|setTimeout|requestAnimationFrame)\s*\(")
NUMBER = re.compile(r"^(\d*\.?\d+)(%)?$")
SIZES = ", ".join(str(size) for size in UI_SIZES_PX)


def simulation_art_problems(html: str) -> list[SandboxProblem]:
    markup = ArtMarkup()
    markup.feed(html)
    markup.close()
    found = [
        *_colour_problems(markup),
        *_type_problems(markup.styles),
        *_rest_problems(markup.styles),
        *_motion_problems(markup.scripts),
        *_pictured_problems(markup.pictured),
        *drawn_art_problems(DRAWING_KIND, {FIGURE_KEY: markup.drawings}, {}),
    ]
    return [SandboxProblem(ART_RULE, detail) for detail in dict.fromkeys(found)]


def _declarations(styles: Iterable[str]) -> Iterator[tuple[str, str]]:
    for style in styles:
        yield from css_declarations(style)


def _colour_problems(markup: ArtMarkup) -> Iterator[str]:
    for name, value in _declarations(markup.styles):
        if name in COLOUR_PROPERTIES or BORDER.match(name):
            yield from _painted(value, control=True)
    for value in markup.paints:
        yield from _painted(value, control=False)
    for script in markup.scripts:
        for match in SCRIPT_LITERAL.finditer(script):
            yield f"the script paints {match.group(0)}; name a design role, var(--ink-1) and the like, instead"
        for match in SCRIPT_MATERIAL.finditer(script):
            yield _material(match.group(1))


def _painted(value: str, *, control: bool) -> Iterator[str]:
    if " ".join(value.split()).casefold() in PLAIN:
        return
    for match in LITERAL.finditer(BARE_VAR.sub(" ", value)):
        yield (
            f"names the colour {match.group(0)!r}; name a design role instead: var(--ink-1) to var(--ink-3), "
            "var(--rule), var(--rule-strong), var(--ground), var(--raised), var(--sunk), a --chart-* role, "
            "and var(--indigo) only on a control"
        )
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


def _rest_problems(styles: Iterable[str]) -> Iterator[str]:
    for name, value in _declarations(styles):
        found = NUMBER.match(value.strip()) if name == "opacity" else None
        if found is None:
            continue
        amount = float(found.group(1)) / (100 if found.group(2) else 1)
        if amount < 1:
            yield (
                f"rests at opacity {value.strip()}: every end state is the default style, so the first paint "
                "shows the finished figure and nothing waits faded for Play"
            )


def _motion_problems(scripts: Iterable[str]) -> Iterator[str]:
    for script in scripts:
        if TIMERS.search(script) and REDUCED_MOTION_FLAG not in script:
            yield (
                "times its motion without reading document.documentElement.dataset.reducedMotion, which the "
                "frame sets under either reduced-motion switch; under it nothing moves and Play steps one stage "
                "a press"
            )


def _pictured_problems(labels: Iterable[str]) -> Iterator[str]:
    for label in labels:
        for part, word in parts_named_by(label):
            yield f"a picture said to show {word} ({label!r}) is the kit's {part} part, which the site draws; {KIT_POINTER}"
