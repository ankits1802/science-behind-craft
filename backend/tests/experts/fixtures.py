import json
import uuid
from collections.abc import Sequence
from typing import Any

from app.models import Source
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec
from app.services.answer_events import CitedClaims, cited_claims
from app.services.builder_interface import BuildAsk, BuilderTools
from app.services.knowledge_view import ClaimView
from app.services.section_blocks import KeptSentence, prose_block

from ..answering.fakes import stored_view
from ..planner.fakes import FakeModel
from ..research.fixtures import AJRAKH

QUESTION = "When did the Khatris bring Ajrakh to Kutch?"
MIGRATION = uuid.UUID("5a000000-0000-4000-8000-000000000001")
CLIENTELE = uuid.UUID("5a000000-0000-4000-8000-000000000002")


def source(number: int, kind: str, title: str, url: str) -> Source:
    return Source(
        id=uuid.UUID(f"50000000-0000-4000-8000-{number:012d}"),
        kind=kind,
        title=title,
        authors=[],
        year=None,
        doi=None,
        url=url,
        publisher=None,
        licence=None,
        attribution=None,
        reliability="B",
    )


GI = source(1, "GI_JOURNAL", "GI Journal No. 188", "https://ipindia.gov.in/gi-journal-188")
KHAMIR = source(2, "WEB_PAGE", "The Khatris and their community", "https://exhibitions-khamir.org/ajrakh")
SAHAPEDIA = source(3, "WEB_PAGE", "Ajrakh: An Introduction", "https://www.sahapedia.org/ajrakh")
SOURCES = {GI.id: GI, KHAMIR.id: KHAMIR, SAHAPEDIA.id: SAHAPEDIA}


def claim(number: int) -> uuid.UUID:
    return uuid.UUID(f"c1000000-0000-4000-8000-{number:012d}")


FOUR_HUNDRED = stored_view(
    claim(1),
    "The technique came to Kutch from Sindh some 400 years ago at the behest of the King of Kutch.",
    "PROVISIONAL",
    (101, GI, "came to Kutch from Sindh some 400 years ago at the behest of the King of Kutch", "p. 9"),
    concept_id=MIGRATION,
)
SEVENTH_CENTURY = stored_view(
    claim(2),
    "Khamir's account says Hindu Khatris fled Sindh to Kachchh in the 7th century after Arab invasion.",
    "PROVISIONAL",
    (102, KHAMIR, "During the 7th century, the Khatris of Sindh were Hindu.", None),
    concept_id=MIGRATION,
)
DHAMADKA = stored_view(
    claim(3),
    "Khatri craftsmen were invited to practise their art on the banks of the Dhamadka river.",
    "PROVISIONAL",
    (103, GI, "invited craftsmen from Khatri community to come and practice their art", "p. 9"),
    concept_id=MIGRATION,
)
CLIENTS = stored_view(
    claim(4),
    "Khatris made cloth for Maldharis and farming communities, trading cloth for produce, milk or ghee.",
    "PROVISIONAL",
    (104, SAHAPEDIA, "They produced cloth for maldharis (cattle herders)", None),
    concept_id=CLIENTELE,
)
BHARMALJI = stored_view(
    claim(5),
    "Rao Bharmalji I invited Khatri printers from Sindh and gave them land.",
    "REVIEWED",
    (105, SAHAPEDIA, "Rao Bharmalji - I (1586-1631), invited the cloth-printing Khatri artisans", None),
    concept_id=MIGRATION,
)
GUESS = stored_view(
    claim(6),
    "The Khatris may have printed in Kutch before the invitation.",
    "HYPOTHESIS",
    (106, KHAMIR, None, None),
    concept_id=MIGRATION,
)
VIEWS = (FOUR_HUNDRED, SEVENTH_CENTURY, DHAMADKA, CLIENTS, BHARMALJI, GUESS)


def cited(views: Sequence[ClaimView] = VIEWS) -> CitedClaims:
    return cited_claims(list(views), SOURCES)


def prose(section_id: str, views: Sequence[ClaimView], claims: CitedClaims) -> Any:
    sentences = [KeptSentence(view.text, (view.id,), (), False) for view in views]
    return prose_block(f"{section_id}.b1", sentences, claims)


def build_ask(
    seats: Sequence[str],
    *,
    discipline: str = "HISTORY",
    depth: str = "DETAILED",
    views: Sequence[ClaimView] = VIEWS,
) -> BuildAsk:
    claims = cited(views)
    shown = [view for view in views if view.level != "HYPOTHESIS"]
    request = PlanRequest(question=QUESTION, mode="HYBRID", craft=AJRAKH, depth=depth, seats=tuple(seats))
    spec = SectionSpec(id="s5", discipline=discipline, title="History", order=5)
    return BuildAsk(uuid.uuid4(), spec, request, (prose("s5", shown, claims),), claims)


def tools(model: Any) -> BuilderTools:
    return BuilderTools(sessions=None, live=None, plan_model=None, compose_model=model)


def said(view: ClaimView, text: str | None = None, quote: str | None = None) -> dict[str, Any]:
    stated = text or view.text
    return {"text": stated, "quotes": [{"source": str(view.id), "quote": quote or stated.rstrip(".")}]}


def take(seat: str, *sentences: dict[str, Any]) -> dict[str, Any]:
    return {"seat": seat, "take": list(sentences)}


def differ(seat: str, mine: ClaimView, other_seat: str, theirs: ClaimView) -> dict[str, str]:
    return {
        "seat": seat,
        "statement": str(mine.id),
        "otherSeat": other_seat,
        "otherStatement": str(theirs.id),
    }


def panel_model(views: Sequence[dict[str, Any]], differences: Sequence[dict[str, str]] = ()) -> FakeModel:
    return FakeModel([json.dumps({"views": list(views), "differences": list(differences)})])
