from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from app.research.quotes import QUOTE_OVERLAP_MIN, quote_overlap

from .dossier import Dossier
from .entity_rules import claim_quotes
from .figures import figure_gaps
from .limits import DISCIPLINE_CLAIMS_MIN
from .problems import Problem
from .sentences import single_sentence

__all__ = ["overview_problems"]


def overview_problems(dossier: Dossier) -> list[Problem]:
    found = []
    for where, sentence in dossier.overview.located_sentences():
        found += [
            Problem(where, message)
            for message in _sentence_messages(dossier, sentence.text, sentence.claim_ids)
        ]
    for index, fact in enumerate(dossier.overview.key_facts):
        gaps = figure_gaps(fact.value, claim_quotes(dossier, fact.claim_ids))
        if gaps:
            found.append(
                Problem(f"overview.keyFacts.{index}", f"{', '.join(gaps)} appears in no quote of its claims")
            )
    counts = Counter(claim.discipline for claim in dossier.claims if not claim.hypothesis)
    found += [
        Problem(
            f"overview.{section.discipline}",
            f"a section needs at least {DISCIPLINE_CLAIMS_MIN} claims of its discipline; "
            f"{section.discipline} has {counts[section.discipline]}",
        )
        for section in dossier.overview.sections
        if counts[section.discipline] < DISCIPLINE_CLAIMS_MIN
    ]
    return found


def _sentence_messages(dossier: Dossier, text: str, claim_ids: Sequence[str]) -> list[str]:
    quotes = claim_quotes(dossier, claim_ids)
    claim_texts = [dossier.claim(claim_id).text for claim_id in claim_ids]
    messages = [] if single_sentence(text) else ["is not one sentence ending in a full stop"]
    gaps = figure_gaps(text, quotes)
    if gaps:
        messages.append(f"{', '.join(gaps)} appears in no quote of its claims")
    overlap = quote_overlap(text, [*claim_texts, *quotes])
    if overlap < QUOTE_OVERLAP_MIN:
        messages.append(
            f"only {overlap:.0%} of its content words are in its claims and their quotes; "
            "a sentence adds no fact its claims do not state"
        )
    return messages
