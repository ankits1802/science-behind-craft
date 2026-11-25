from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from app.models.component_kinds import DOCUMENT_KINDS, PIECE_KINDS
from app.research.vocabulary import CANONICAL_LANGUAGE

from .export_pdf_text import sentence_case
from .interface_words import ENGLISH_WORDS, InterfaceWords, reviewed_words
from .page_export_model import ExportText, Role, Run

__all__ = [
    "AT_REST",
    "BECOMES",
    "DRAWN",
    "DRAWN_IN",
    "ENGLISH_EXPORT_WORDS",
    "EXPORT_WORDS",
    "EXPORT_WORDS_PREFIX",
    "GIVEN_BY",
    "HOME",
    "KEY",
    "KIND_LABELS",
    "KIT_MOTION_NOTE",
    "OR",
    "PAPER_NOTES",
    "PICTURE",
    "PICTURE_CLOSED",
    "PICTURE_UNREAD",
    "READING",
    "ROUTE",
    "SOURCES",
    "SWATCHES",
    "ExportWord",
    "ExportWords",
    "export_words",
    "kind_word",
    "paper_note",
]

EXPORT_WORDS_PREFIX = "export."
PLAYS = "This part plays or answers on the page; its words are given here."
KIT_MOTION_NOTE = "On the page a panel's change plays when pressed; here each panel is drawn at rest."
PAPER_NOTES: Mapping[str, str] = MappingProxyType(
    {
        "reaction_player": (
            "On the page the reader steps through each reaction and scrubs between them; here every step is "
            "listed and the drawing rests on the step the page opens on."
        ),
        "dip_player": (
            "On the page the reader dips again and watches each dip deepen the colour; here the dips are listed "
            "in order and the drawing rests as the page opens."
        ),
        "stage_player": "On the page the stages play one after another; here they are listed in order.",
        "molecule_3d": "On the page the reader turns and zooms the model; here it is drawn as it rests.",
        "timeline_map": (
            "On the page the map moves through the years and each pin opens its entry; here it rests on its last "
            "year with every place pinned and numbered."
        ),
        "experiment_lab": "On the page the reader chooses an experiment; here every choice is listed.",
        "choice_toggle": "On the page the reader switches between the choices; here every choice is shown.",
        "map_sequence": "On the page the maps step one after another; here each is listed in order.",
        **dict.fromkeys(
            (
                "process_replay",
                "quiz",
                "ask_next",
                "generator",
                "audio_player",
                "voice",
                "film",
                "ai_video",
                "model_explainer",
                "explainer",
                "reading_level",
                "language_switch",
                "citation_tool",
            ),
            PLAYS,
        ),
    }
)
KIND_LABELS: Mapping[str, str] = MappingProxyType({"molecule_3d": "Molecule in 3D"})


@dataclass(frozen=True)
class ExportWord:
    key: str
    english: str


def paper_note(english: str) -> ExportWord:
    return ExportWord("export.paperNote", english)


def kind_word(kind: str) -> ExportWord:
    return ExportWord("export.kind", KIND_LABELS.get(kind) or sentence_case(kind))


SOURCES = ExportWord("export.heading", "Sources")
READING = ExportWord(
    "export.note", "{translated} of {passages} passages read in {label}; the others are shown in English."
)
PICTURE_UNREAD = ExportWord(
    "export.pictureNote",
    "The page shows this picture; it could not be read for this file, so it is given by its description "
    "and credit.",
)
PICTURE_CLOSED = ExportWord(
    "export.pictureNote",
    "The page shows this picture; its licence does not let it be copied into this file, so it is given by its "
    "description and credit.",
)
DRAWN = ExportWord("export.label", "Drawn")
GIVEN_BY = ExportWord("export.label", "Given by")
SWATCHES = ExportWord("export.label", "Swatches")
KEY = ExportWord("export.label", "Key")
PICTURE = ExportWord("export.label", "Picture")
HOME = ExportWord("export.phrase", "this craft's place")
AT_REST = ExportWord("export.phrase", "as the page opens")
DRAWN_IN = ExportWord("export.phrase", "drawn in the figure {title}")
BECOMES = ExportWord("export.phrase", "{before} becomes {after}")
OR = ExportWord("export.phrase", "{before} or {after}")
ROUTE = ExportWord("export.phrase", "{start} to {end}, {years}")
EXPORT_WORDS: tuple[ExportWord, ...] = (
    SOURCES,
    READING,
    PICTURE_UNREAD,
    PICTURE_CLOSED,
    DRAWN,
    GIVEN_BY,
    SWATCHES,
    KEY,
    PICTURE,
    HOME,
    AT_REST,
    DRAWN_IN,
    BECOMES,
    OR,
    ROUTE,
    paper_note(KIT_MOTION_NOTE),
    *(paper_note(note) for note in dict.fromkeys(PAPER_NOTES.values())),
    *(kind_word(kind) for kind in (*PIECE_KINDS, *DOCUMENT_KINDS)),
)


@dataclass(frozen=True)
class ExportWords:
    words: InterfaceWords = field(default=ENGLISH_WORDS)

    def said(self, word: ExportWord, **values: object) -> str:
        return self.words.said(word.key, word.english, **values)

    def lang(self, word: ExportWord) -> str | None:
        drawn = (
            self.words.language == CANONICAL_LANGUAGE or self.words.shown(word.key, word.english) is not None
        )
        return None if drawn else CANONICAL_LANGUAGE

    def run(self, word: ExportWord, **values: object) -> Run:
        return Run(self.said(word, **values), lang=self.lang(word))

    def label(self, word: ExportWord) -> Run:
        return Run(f"{self.said(word)}: ", lang=self.lang(word))

    def text(self, word: ExportWord, role: Role = "note", **values: object) -> ExportText:
        return ExportText(runs=(self.run(word, **values),), role=role, lang=self.lang(word))

    def labelled(self, word: ExportWord, value: str, role: Role = "note") -> ExportText:
        return ExportText(runs=(self.label(word), Run(value)), role=role)

    def kind(self, kind: str) -> str:
        return self.said(kind_word(kind))

    def made_from(self) -> list[list[str]]:
        shown = self.words.entries.values()
        return sorted(
            [entry.key, entry.english, entry.text]
            for entry in shown
            if entry.key.startswith(EXPORT_WORDS_PREFIX)
        )


ENGLISH_EXPORT_WORDS = ExportWords()


def export_words(language: str) -> ExportWords:
    return ExportWords(reviewed_words(language))
