from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from pydantic import ValidationError

from app.composer.material_cards import CardBrief, CardChoice, CardStatement
from app.research.blocks import ExplainerSentence
from app.research.blocks_matter import MaterialCardBlock
from app.research.citations import Citation
from app.research.explainer import Block
from app.research.quotes import quote_occurs
from app.research.vocabulary import FACT_LEVELS
from app.science.records import KnownClaim

from .answer_events import CitedClaims
from .craft_matter import CraftMatter, GlossaryTerm, MaterialRows, first_naming, section_sentences

__all__ = [
    "CARD_STATEMENTS_MAX",
    "MATERIAL_CARDS_MAX",
    "CardOffer",
    "card_offers",
    "material_card",
    "material_term",
]

logger = logging.getLogger(__name__)

MATERIAL_CARDS_MAX = 3
CARD_STATEMENTS_MAX = 10


@dataclass(frozen=True)
class CardOffer:
    ref: str
    material: MaterialRows
    statements: Mapping[str, KnownClaim]

    def brief(self) -> CardBrief:
        term = material_term(self.material)
        return CardBrief(
            ref=self.ref,
            name=self.material.name,
            names=_local_names(term),
            role=_agreed_role(self.material),
            statements=tuple(CardStatement(ref, claim.text) for ref, claim in self.statements.items()),
        )


def card_offers(matter: CraftMatter, blocks: Sequence[Block], cited: CitedClaims) -> list[CardOffer]:
    sentences = section_sentences(blocks)
    named: list[tuple[int, MaterialRows]] = []
    for material in matter.materials:
        position = first_naming(sentences, material.surfaces(), (term.key for term in material.terms))
        if position is not None:
            named.append((position, material))
    named.sort(key=lambda pair: pair[0])
    offers = []
    for material in (material for _, material in named):
        ref = f"m{len(offers) + 1}"
        claims = _offered_claims(material, matter, cited)
        if claims:
            offers.append(CardOffer(ref, material, {f"{ref}.c{n}": c for n, c in enumerate(claims, 1)}))
        if len(offers) == MATERIAL_CARDS_MAX:
            break
    return offers


def material_card(offer: CardOffer, choice: CardChoice, *, block_id: str) -> MaterialCardBlock | None:
    facts = _chosen(offer, choice.facts, taken=set())
    handling = _chosen(offer, choice.handling, taken={claim.id for claim in facts})
    if not facts:
        logger.info("the %s card has no stored fact left and is not shown", offer.material.name)
        return None
    sentences = [_sentence(f"{block_id}.{n}", claim) for n, claim in enumerate([*facts, *handling], 1)]
    term = material_term(offer.material)
    compound = offer.material.compound
    linked = compound if compound is not None and compound.pubchem_cid is not None else None
    try:
        return MaterialCardBlock(
            id=block_id,
            kind="material_card",
            version=1,
            reuse=None,
            material_id=offer.material.material_id,
            compound_id=compound.id if compound is not None else None,
            term_key=term.key if term is not None else None,
            name=offer.material.name,
            material_kind=offer.material.kind,
            role=_agreed_role(offer.material),
            formula=linked.formula if linked is not None else None,
            pubchem_cid=linked.pubchem_cid if linked is not None else None,
            wikidata_id=term.wikidata_id if term is not None else None,
            local_names=list(_local_names(term)),
            facts=sentences[: len(facts)],
            handling=sentences[len(facts) :],
        )
    except ValidationError as refused:
        logger.warning("the %s card is refused: %s", offer.material.name, refused)
        return None


def material_term(material: MaterialRows) -> GlossaryTerm | None:
    named = [term for term in material.terms if quote_occurs(term.label.casefold(), material.name.casefold())]
    return max(named, key=lambda term: (len(term.label), term.key), default=None)


def _offered_claims(material: MaterialRows, matter: CraftMatter, cited: CitedClaims) -> list[KnownClaim]:
    own = [matter.records.claims.get(claim_id) for use in material.uses for claim_id in use.claim_ids]
    mentioning = [
        _known(view.id, view.text, view.level, view.citations)
        for view in cited.views.values()
        if any(quote_occurs(surface.casefold(), view.text.casefold()) for surface in material.surfaces())
    ]
    found: dict[uuid.UUID, KnownClaim] = {}
    for claim in [*own, *mentioning]:
        if claim is not None and claim.level in FACT_LEVELS:
            found.setdefault(claim.id, claim)
    return list(found.values())[:CARD_STATEMENTS_MAX]


def _chosen(offer: CardOffer, refs: Iterable[str], *, taken: set[uuid.UUID]) -> list[KnownClaim]:
    chosen: list[KnownClaim] = []
    for ref in refs:
        claim = offer.statements.get(ref)
        if claim is None:
            logger.info("the %s card drops %r: not one of its stored statements", offer.material.name, ref)
            continue
        if claim.id in taken:
            continue
        taken.add(claim.id)
        chosen.append(claim)
    return chosen


def _sentence(sentence_id: str, claim: KnownClaim) -> ExplainerSentence:
    return ExplainerSentence(
        id=sentence_id, text=claim.text, level=claim.level, citations=list(claim.citations), terms=[]
    )


def _known(
    claim_id: uuid.UUID, text: str, level: str, citations: Iterable[Mapping[str, object]]
) -> KnownClaim:
    return KnownClaim(claim_id, text, level, tuple(Citation.model_validate(c) for c in citations))


def _agreed_role(material: MaterialRows) -> str | None:
    roles = {use.role for use in material.uses}
    return roles.pop() if len(roles) == 1 else None


def _local_names(term: GlossaryTerm | None) -> tuple[str, ...]:
    if term is None:
        return ()
    kept: dict[str, str] = {}
    for name in term.local_names:
        if name.strip():
            kept.setdefault(name.strip().casefold(), name.strip())
    return tuple(kept.values())
