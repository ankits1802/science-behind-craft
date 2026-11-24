from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from .document_translation import DocumentTranslation
from .monograph_page import MonographContent, TextUnit
from .spec_texts import SpecText, spec_texts, with_spec_texts
from .translation_passages import is_translatable, passage_leaves, unit_hash, with_texts
from .vocabulary import ANSWER_LANGUAGE_SPECS, CANONICAL_LANGUAGE, text_direction

__all__ = ["NO_TRANSLATIONS", "ServedTranslations", "Variant", "translations_digest", "variant_content"]

DIGEST_SEPARATOR = ","


@dataclass(frozen=True)
class ServedTranslations:
    by_hash: Mapping[str, tuple[str, ...]] = field(default_factory=lambda: MappingProxyType({}))
    earlier: frozenset[str] = frozenset()
    digest: str = ""

    @property
    def empty(self) -> bool:
        return not self.by_hash


NO_TRANSLATIONS = ServedTranslations()


@dataclass(frozen=True)
class Variant:
    content: MonographContent
    translation: DocumentTranslation
    specs: Mapping[str, Mapping[str, Any]] = field(default_factory=lambda: MappingProxyType({}))


@dataclass
class _Tally:
    passages: int = 0
    translated: int = 0
    held: int = 0


def translations_digest(ids: Iterable[str]) -> str:
    joined = DIGEST_SEPARATOR.join(sorted(ids))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def variant_content(
    content: MonographContent,
    served: ServedTranslations,
    *,
    language: str,
    source_version: int,
    specs: Mapping[str, Mapping[str, Any]],
) -> Variant:
    tally = _Tally()
    units = {key: _shown(key, unit, served, language, tally) for key, unit in content.units.items()}
    shown_specs = {**specs, **_shown_specs(content, specs, served, tally)}
    translation = DocumentTranslation(
        source_version=source_version,
        script=ANSWER_LANGUAGE_SPECS[language].script,
        direction=text_direction(language),
        passages=tally.passages,
        translated=tally.translated,
        held=tally.held,
    )
    return Variant(
        content=content.model_copy(update={"units": units}), translation=translation, specs=shown_specs
    )


def _shown_specs(
    content: MonographContent,
    specs: Mapping[str, Mapping[str, Any]],
    served: ServedTranslations,
    tally: _Tally,
) -> dict[str, dict[str, Any]]:
    shown: dict[str, dict[str, Any]] = {}
    for component in content.components:
        spec = specs.get(component.label)
        if spec is None:
            continue
        given: list[tuple[SpecText, list[Any]]] = []
        for text in spec_texts(component.label, component.kind, spec):
            if not is_translatable(text.key, text.nodes):
                continue
            tally.passages += 1
            texts = served.by_hash.get(unit_hash(text.nodes, []))
            if texts is not None and len(texts) == len(passage_leaves(text.nodes)):
                tally.translated += 1
                given.append((text, with_texts(text.nodes, texts)))
            else:
                tally.held += text.key in served.earlier
        if given:
            shown[component.label] = with_spec_texts(spec, given)
    return shown


def _shown(key: str, unit: TextUnit, served: ServedTranslations, language: str, tally: _Tally) -> TextUnit:
    if not is_translatable(key, unit.nodes):
        return unit
    tally.passages += 1
    texts = served.by_hash.get(unit_hash(unit.nodes, unit.claim_ids))
    if texts is not None and len(texts) == len(passage_leaves(unit.nodes)):
        tally.translated += 1
        return unit.model_copy(update={"nodes": with_texts(unit.nodes, texts), "lang": language})
    tally.held += key in served.earlier
    return unit.model_copy(update={"lang": CANONICAL_LANGUAGE})
