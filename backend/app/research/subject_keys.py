from __future__ import annotations

import re
import unicodedata
from typing import Annotated

from pydantic import AfterValidator

from app.core.errors import InvalidInput

__all__ = [
    "SUBJECT_JOINER",
    "TERM_KEY_MAX_CHARS",
    "TOPIC_KEY_MAX_CHARS",
    "TOPIC_NAMESPACES",
    "TermKey",
    "TopicKey",
    "subject_slug",
    "term_key",
    "topic_key",
]

TOPIC_NAMESPACES = (
    "craft",
    "process",
    "stage",
    "material",
    "reaction",
    "compound",
    "water",
    "soil",
    "climate",
    "region",
    "history",
    "design",
    "economy",
    "health",
    "ecology",
    "society",
    "policy",
    "concept",
)
SUBJECT_JOINER = "+"
TERM_KEY_MAX_CHARS = 120
TOPIC_KEY_MAX_CHARS = 200
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
NOT_SLUG = re.compile(r"[^a-z0-9]+")
TERM_KEY = re.compile(rf"^{SLUG}$")
TOPIC_KEY = re.compile(rf"^(?P<namespace>[a-z]+):(?P<subjects>{SLUG}(?:\+{SLUG})*)$")


def subject_slug(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    bare = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()
    slug = NOT_SLUG.sub("-", bare).strip("-")
    if not slug:
        raise InvalidInput(f"{text!r} has no Latin letters or digits to key on")
    return slug


def topic_key(namespace: str, *subjects: str) -> str:
    if namespace not in TOPIC_NAMESPACES:
        raise InvalidInput(f"Unknown topic namespace {namespace!r}")
    if not subjects:
        raise InvalidInput("A topic key names at least one subject")
    slugs = sorted({subject_slug(subject) for subject in subjects})
    key = f"{namespace}:{SUBJECT_JOINER.join(slugs)}"
    if len(key) > TOPIC_KEY_MAX_CHARS:
        raise InvalidInput(f"A topic key is at most {TOPIC_KEY_MAX_CHARS} characters")
    return key


def term_key(label: str) -> str:
    key = subject_slug(label)
    if len(key) > TERM_KEY_MAX_CHARS:
        raise InvalidInput(f"A term key is at most {TERM_KEY_MAX_CHARS} characters")
    return key


def _checked_topic_key(value: str) -> str:
    found = TOPIC_KEY.fullmatch(value)
    if found is None or found["namespace"] not in TOPIC_NAMESPACES:
        raise ValueError(f"{value!r} is not <namespace>:<subject> with a known namespace")
    subjects = found["subjects"].split(SUBJECT_JOINER)
    if value != topic_key(found["namespace"], *subjects) or len(set(subjects)) != len(subjects):
        raise ValueError(f"{value!r} lists its subjects once each, sorted")
    return value


def _checked_term_key(value: str) -> str:
    if len(value) > TERM_KEY_MAX_CHARS or not TERM_KEY.fullmatch(value):
        raise ValueError(f"{value!r} is not a term key (lower-case letters and digits joined by hyphens)")
    return value


TopicKey = Annotated[str, AfterValidator(_checked_topic_key)]
TermKey = Annotated[str, AfterValidator(_checked_term_key)]
