from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from app.research.blocks import ExplainerSentence, named_in, stated_texts

__all__ = [
    "AIR_CUE",
    "BODY_WORDS",
    "CHEMICAL_CUE",
    "COLOUR_WORDS",
    "CUED_MORDANTS",
    "DIP_CONTEXT",
    "DIP_COUNT",
    "DYE_WORDS",
    "FERMENTED_CUE",
    "FIBRE_WORDS",
    "FIRING_CONTEXT",
    "INSOLUBLE",
    "KETO_COLOURS",
    "KETO_COMPOUNDS",
    "KETO_NAMES",
    "LEUCO_COLOURS",
    "LEUCO_COMPOUNDS",
    "LEUCO_NAMES",
    "LOST_WAX_CUES",
    "METAL_ANY",
    "METAL_WORDS",
    "MORDANT_COLOURS",
    "MORDANT_WORDS",
    "NEGATION",
    "NO_MORDANT",
    "OXIDISING_CUE",
    "REDUCING_CUE",
    "SHADE_WORDS",
    "SOLUBLE",
    "TEMPERATURE",
    "VAT_CONTENTS",
    "first_named",
    "named_once",
    "names_any",
    "names_first",
    "says",
]

MORDANT_WORDS = ("alum", "iron", "tin", "chrome")
CUED_MORDANTS = ("tin", "chrome")
MORDANT_COLOURS = ("red", "black", "yellow", "pink", "purple", "brown", "orange", "violet", "maroon")
COLOUR_WORDS = (
    "red",
    "black",
    "blue",
    "yellow",
    "green",
    "pink",
    "purple",
    "brown",
    "orange",
    "violet",
    "maroon",
    "white",
)
DYE_WORDS = ("madder", "alizarin", "al root", "chay root", "lac", "cochineal", "turmeric", "logwood")
FIBRE_WORDS = ("cotton", "silk", "wool", "linen", "jute", "cloth", "fabric")
NO_MORDANT = re.compile(r"\b(?:no|without(?: a| any)?) mordants?\b|\bunmordanted\b")
NEGATION = re.compile(r"\b(?:no|not|never|without|cannot)\b")

AIR_CUE = re.compile(r"\b(?:oxygen|air|oxidi[sz](?:e|es|ed|ing|ation))\b")
FERMENTED_CUE = re.compile(r"\bferment")
CHEMICAL_CUE = re.compile(r"\bhydros(?:ulphite|ulfite)?\b|\bcaustic soda\b|\bdithionite\b")
VAT_CONTENTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "FERMENTED": (
        ("lime",),
        ("dates",),
        ("soda",),
        ("jaggery", "molasses"),
        ("bran",),
        ("henna",),
        ("sagikhar", "sajikhar"),
        ("casiatora seed", "casatoria seeds", "kuwadia na beej"),
    ),
    "CHEMICAL": (
        ("sodium hydrosulphite", "sodium hydrosulfite", "hydros"),
        ("caustic soda",),
        ("sodium dithionite",),
        ("lime",),
    ),
}
KETO_NAMES = ("indigo blue", "indigotin", "indigo")
LEUCO_NAMES = ("leucoindigo", "leuco-indigo", "indigo white")
KETO_COLOURS = ("blue",)
LEUCO_COLOURS = ("yellow", "green", "white", "colourless")
KETO_COMPOUNDS = ("indigo", "indigotin")
LEUCO_COMPOUNDS = ("leucoindigo", "indigo white")
INSOLUBLE = re.compile(r"\binsoluble\b|\bnot soluble\b|\bdoes not dissolve\b|\bdo not dissolve\b")
SOLUBLE = re.compile(r"(?<!not )\bsoluble\b|(?<!not )\bdissolves\b")
NUMBER = r"[1-8]|one|two|three|four|five|six|seven|eight"
DIP_COUNT = re.compile(
    rf"\b({NUMBER})(?:\s+(?:or|to)\s+(?:{NUMBER}))?\s+(?:times|dips|immersions)\b", re.IGNORECASE
)
DIP_CONTEXT = re.compile(r"\b(?:indigo|vat|blue)\b")
SHADE_WORDS = (
    "darkest",
    "darker",
    "dark",
    "deepest",
    "deeper",
    "deep",
    "lightest",
    "lighter",
    "light",
    "palest",
    "pale",
)

METAL_WORDS = ("brass", "bronze", "bell metal", "copper", "silver", "gold", "white metal")
METAL_ANY = re.compile(r"\b(?:metal|brass|bronze|copper|silver|gold)\b")
LOST_WAX_CUES: dict[str, tuple[re.Pattern[str], ...]] = {
    "MODEL": (re.compile(r"\bwax\b"), re.compile(r"\b(?:model(?:s|led|ling)?|shaped|core|threads?)\b")),
    "JACKET": (
        re.compile(r"\bclay\b"),
        re.compile(r"\b(?:coat(?:s|ed|ing)?|covered|layers?|jacket|moulds?)\b"),
    ),
    "BURNOUT": (
        re.compile(
            r"\bwax\b[^.]{0,60}\b(?:melt(?:s|ed|ing)? out|runs? out|flows? out|drain(?:s|ed)?(?: out)?"
            r"|burn(?:s|t|ed)? (?:out|away))\b"
            r"|\b(?:melt(?:s|ed|ing)?|drain(?:s|ed)?|burn(?:s|t|ed)?) out (?:the )?wax\b"
        ),
    ),
    "POUR": (re.compile(r"\b(?:molten|poured|pouring|pours?)\b"), METAL_ANY),
    "BREAK_OUT": (re.compile(r"\b(?:broken|breaks?)\b"), re.compile(r"\b(?:moulds?|clay|casting|cast)\b")),
}

FIRING_CONTEXT = re.compile(r"\bfir(?:e|ed|es|ing)\b|\bkilns?\b")
OXIDISING_CUE = re.compile(r"\boxidi[sz]ing\b|\boxidation\b|\bplenty of air\b|\bfree flow of air\b")
REDUCING_CUE = re.compile(r"\breduc(?:ing|tion)\b|\bstarved of air\b|\bsmok(?:e|ed|y)\b|\bsmother")
BODY_WORDS = ("terracotta", "earthenware", "stoneware", "clay", "pottery", "pots", "pot")
TEMPERATURE = re.compile(r"\b\d{3,4}\s*(?:°\s?c\b|degrees?(?:\s+(?:celsius|centigrade|c))?\b)", re.IGNORECASE)


def says(sentence: ExplainerSentence, pattern: re.Pattern[str]) -> bool:
    return any(pattern.search(text.casefold()) for text in stated_texts(sentence))


def names_any(sentence: ExplainerSentence, words: Iterable[str]) -> bool:
    return any(named_in(word, sentence) for word in words)


def names_first(sentences: Sequence[ExplainerSentence], words: Sequence[str]) -> str | None:
    return next((word for word in words if any(named_in(word, sentence) for sentence in sentences)), None)


def named_once(sentence: ExplainerSentence, words: Sequence[str]) -> str | None:
    named = [word for word in words if named_in(word, sentence)]
    return named[0] if len(named) == 1 else None


def first_named(sentences: Sequence[ExplainerSentence], words: Sequence[str]) -> str | None:
    counts = {word: sum(1 for sentence in sentences if named_in(word, sentence)) for word in words}
    best = max(counts.values(), default=0)
    return next((word for word in words if best and counts[word] == best), None)
