from __future__ import annotations

from datetime import datetime
from types import MappingProxyType
from typing import Any

from app.core.errors import InvalidInput
from app.core.roles import Capability, can
from app.models import PageDraft
from app.research.page_proposals import PageBundle, PageSubject
from app.research.supplied_sources import LOCATOR_MAX_CHARS, PASSAGE_MIN_CHARS, TEXT_MIN_CHARS
from app.services import craft_finder

from .mcp_input import Answer, Question, choice, yes_no
from .mcp_page_arguments import ONE_PAGE
from .mcp_tool_base import ToolContext

__all__ = [
    "PAGE_KEY",
    "SEND_KEY",
    "WORDS_KEY",
    "chosen_page",
    "contributes",
    "page_question",
    "send_question",
    "sent",
    "supplied_words",
    "words_question",
]

PAGE_KEY, SEND_KEY, WORDS_KEY = "page", "send", "words"
CONTRIBUTIONS = (
    ("page", "A whole page, built or deepened"),
    ("facts", "Facts and the sources they rest on"),
    ("figures", "Figures, maps and other components"),
    ("pictures", "Pictures of the craft"),
    ("sources", "A source only I can open"),
)
PART_NAMES = MappingProxyType({"structure": "structure items"})
PAGE_MESSAGE = (
    "Which craft's page is this for, and what would you like to give it? Everything else, how the page is "
    "researched, designed and built, is done for you."
)
SEND_MESSAGE = (
    "Send this page to KalaVigyan now? {kind} {slug}: {parts}. {preview} Once sent, every part goes through "
    "KalaVigyan's checks and review before readers see it."
)
PREVIEW_LINK = "Its private preview, open until {until}: {url}"
NO_PREVIEW = "It has no preview yet."
WORDS_MESSAGE = (
    "KalaVigyan cannot open “{title}” itself. Paste the words of it you want cited: a passage with where it "
    "stands, or the whole text. They are kept privately for reviewers; readers only ever see short quotes "
    "with their citation."
)
NO_CHOICE = "The person chose no page, so no draft was opened; ask them which craft they want to work on."
NO_CRAFT = "No craft matched “{craft}”; find_crafts searches by name, then call edit_draft with its subject."
CHOSEN = "The person chose {name} ({slug}) and wants to contribute {what}."
NOT_SENT = (
    "The person chose not to send the page yet, so nothing was proposed; ask what they want changed, "
    "then call propose_page again."
)
NO_WORDS = (
    "The person gave none of the source's words, so nothing was supplied; give its passages, its whole "
    "text or its file instead."
)
NEEDS_LOCATOR = "a passage under {chars} characters needs where it stands (its locator)"


def page_question() -> Question:
    craft = {
        "type": "string",
        "title": "Craft",
        "description": "The craft by its name, such as Kutch Ajrakh or Channapatna toys",
        "minLength": 2,
        "maxLength": 200,
    }
    what = choice(
        "What you want to contribute", "Choose the one closest to what you have in mind", CONTRIBUTIONS
    )
    return Question(
        PAGE_KEY,
        PAGE_MESSAGE,
        MappingProxyType({"craft": craft, "contribution": what}),
        ("craft", "contribution"),
    )


async def chosen_page(context: ToolContext) -> tuple[PageSubject, str]:
    answer = context.answers.get(PAGE_KEY)
    if answer is None:
        raise InvalidInput(ONE_PAGE)
    craft = answer.text("craft")
    if craft is None:
        raise InvalidInput(NO_CHOICE)
    found = await craft_finder.find_crafts(context.session, context.index, craft, site=context.site)
    if not found.crafts:
        raise InvalidInput(NO_CRAFT.format(craft=craft))
    best = found.crafts[0].craft
    labels = dict(CONTRIBUTIONS)
    what = labels.get(answer.text("contribution") or "", labels["page"]).lower()
    return PageSubject(kind="craft", slug=best.slug), CHOSEN.format(name=best.name, slug=best.slug, what=what)


def send_question(bundle: PageBundle, row: PageDraft | None, now: datetime) -> Question:
    counts = bundle.counts()
    parts = [f"{count} {PART_NAMES.get(part, part)}" for part, count in counts.items() if count]
    parts += ["a layout"] if bundle.layout is not None else []
    parts += ["a translation"] if bundle.translation is not None else []
    message = SEND_MESSAGE.format(
        kind=bundle.subject.kind,
        slug=bundle.subject.slug,
        parts=", ".join(parts) or "no parts",
        preview=_preview(row, now),
    )
    send = yes_no("Send it now", "Leave it ticked to send the page; untick it to keep working on it first")
    return Question(SEND_KEY, message, MappingProxyType({"send": send}), ("send",))


def sent(context: ToolContext) -> None:
    answer = context.answers.get(SEND_KEY)
    if answer is not None and not answer.says_yes("send"):
        raise InvalidInput(NOT_SENT)


def words_question(title: str) -> Question:
    text = {
        "type": "string",
        "title": "The source's words",
        "description": "The passages to cite, or the whole text, copied exactly",
        "minLength": PASSAGE_MIN_CHARS,
    }
    locator = {
        "type": "string",
        "title": "Where they stand",
        "description": f"Such as p. 14 or chapter 3; needed for a passage under {TEXT_MIN_CHARS} characters",
        "maxLength": LOCATOR_MAX_CHARS,
    }
    return Question(
        WORDS_KEY,
        WORDS_MESSAGE.format(title=title),
        MappingProxyType({"text": text, "locator": locator}),
        ("text",),
    )


def supplied_words(context: ToolContext) -> dict[str, Any]:
    answer: Answer | None = context.answers.get(WORDS_KEY)
    if answer is None:
        return {}
    text = answer.text("text")
    if text is None:
        raise InvalidInput(NO_WORDS)
    if len(text) >= TEXT_MIN_CHARS:
        return {"text": text}
    locator = answer.text("locator")
    if locator is None:
        raise InvalidInput(NEEDS_LOCATOR.format(chars=TEXT_MIN_CHARS))
    return {"passages": [{"text": text, "locator": locator}]}


def contributes(context: ToolContext) -> bool:
    user = context.user
    return user is not None and can(user, Capability.PROPOSE_KNOWLEDGE)


def _preview(row: PageDraft | None, now: datetime) -> str:
    if row is None or row.previewUrl is None or row.previewExpiresAt is None or row.previewExpiresAt <= now:
        return NO_PREVIEW
    return PREVIEW_LINK.format(until=row.previewExpiresAt.isoformat(timespec="minutes"), url=row.previewUrl)
