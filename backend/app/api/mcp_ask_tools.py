from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Self

from pydantic import Field, ValidationError, model_validator

from app.core.db import release_connection
from app.core.errors import InvalidInput
from app.core.mcp_scopes import ASK_SCOPE, CONTRIBUTE_SCOPE
from app.core.roles import role_value
from app.models import User
from app.research.crafts import QUESTION_MAX_CHARS, SLUG_MAX_CHARS
from app.research.depth import default_depth
from app.research.image_contributions import CLAIMS_MAX
from app.research.mcp_ask import ANSWER_VIEW_URI, AskedAnswer, asked_answer
from app.research.upload_links import (
    SlotDeclaration,
    UploadSlot,
    UploadStart,
    slot_upload_url,
    upload_page_url,
)
from app.research.vocabulary import AnswerLanguage, Depth
from app.services import upload_links
from app.services.answering import AnswerAsk
from app.services.explainer_history import UnknownExplainer

from .mcp_ask_run import (
    AskTools,
    ask_refusal,
    asker_reading_style,
    run_to_the_end,
    throttle_refusal,
    withheld_terms,
)
from .mcp_tool_base import DATA_NOTE, WRITES, Arguments, Tool, ToolContext
from .oauth_hosts import endpoints_or_none

__all__ = ["ASK_TOOLS", "START_IMAGE_UPLOAD", "Ask", "StartImageUpload", "ViewedTool", "ask_tool"]

SIGN_IN = "This tool needs a signed-in connection."
NOT_KEPT = "The answer was written but could not be read back. Open your answers on the site."
ASK_DESCRIPTION = (
    "Ask KalaVigyan a question about a craft in the signed-in person's name, as they would on the site, and get "
    "the finished answer: the question, the craft, each section with its cited sentences (each with the ids of "
    "the facts and sources it rests on and its citation numbers), the registered components placed in it by "
    "label, the sources with their licences, and the link to the same answer on the site. It runs our research "
    "and writing pipeline to the end and counts against the person's asks and AI budget exactly like the site, "
    "so it can take several minutes; allow up to ten. Clients that render MCP Apps draw it in KalaVigyan's "
    "design from the ui resource it names; otherwise show the answer_url, or draw it yourself with the "
    "kalavigyan://design/answer-kit.md resource. Name KalaVigyan and the Centre wherever you show it."
)
START_DESCRIPTION = (
    "Start giving a picture (a photograph, a drawing or an AI-made illustration) of a craft, for one to twenty "
    "of its facts and optionally one of its stages. The picture travels outside the chat: this returns a "
    "single-use link to KalaVigyan, valid for 30 minutes and tied to this signed-in person, where they sign in, "
    "declare what the picture is (for an AI image the tool, model and prompt) and that they hold the rights, "
    "and drop the file, from a phone too. An agent with a shell may instead pass the declaration here, after "
    "the person has confirmed it, and gets a presigned upload_url for the same slot: PUT the file's bytes to "
    "it. Whichever is used first closes the slot. An AI image is always shown as an illustration, never as a "
    "photograph, and never of a real person, place or object."
)
SHELL_STEP = (
    "PUT the picture's bytes to upload_url within 30 minutes, for example curl --upload-file picture.png "
    "'<upload_url>'; or send the person the link. The slot works once."
)
LINK_STEP = (
    "Send the person the link. They sign in, declare the picture and its rights, and drop the file within 30 "
    "minutes; it works once."
)


class Ask(Arguments):
    question: str = Field(
        min_length=2, max_length=QUESTION_MAX_CHARS, description="The question, as the person asked it"
    )
    craft_slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=SLUG_MAX_CHARS,
        description="A slug from find_crafts; when absent the craft is found from the question",
    )
    any_craft: bool = Field(default=False, description="Ask across crafts rather than about one craft")
    depth: Depth | None = Field(
        default=None, description="How deep to answer; the person's own default when absent"
    )
    language: AnswerLanguage | None = Field(
        default=None, description="The answer's language; English when absent"
    )

    @model_validator(mode="after")
    def _one_craft_or_any(self) -> Self:
        if self.any_craft and self.craft_slug is not None:
            raise ValueError("ask about one craft or any craft, not both")
        return self


class StartImageUpload(Arguments):
    craft_slug: str = Field(min_length=1, max_length=SLUG_MAX_CHARS, description="A slug from find_crafts")
    stage_id: uuid.UUID | None = Field(
        default=None, description="One of the craft's stages, when it shows one"
    )
    claim_ids: list[uuid.UUID] = Field(
        min_length=1,
        max_length=CLAIMS_MAX,
        description="The ids of the facts the picture shows, from get_facts",
    )
    declaration: SlotDeclaration | None = Field(
        default=None,
        description=(
            "Only for an agent that will upload the file itself, and only after the person confirmed it: origin "
            "PHOTOGRAPH, DRAWING or AI_GENERATED, generator and prompt for an AI image, caption, altText, "
            "rightsConfirmed true (they took or made it, or hold the right to share it, and agree that the Centre "
            "publishes it without their name, which cannot be revoked once approved) and termsVersion 2026-11-19"
        ),
    )


@dataclass(frozen=True)
class ViewedTool(Tool):
    view_uri: str = ANSWER_VIEW_URI

    def listed(self) -> dict[str, Any]:
        view = {"resourceUri": self.view_uri, "visibility": ["model", "app"]}
        return {**super().listed(), "_meta": {"ui": view, "ui/resourceUri": self.view_uri}}


def ask_tool(tools: AskTools) -> Tool:
    async def run(context: ToolContext, arguments: Ask) -> AskedAnswer:
        user = _signed_in(context)
        ask = await _asked(context, user, arguments)
        outcome = await run_to_the_end(ask, user, context.index, tools)
        if outcome.problem is not None or outcome.answer_id is None:
            raise InvalidInput(outcome.problem or NOT_KEPT)
        try:
            document = await tools.stored(context.session, outcome.answer_id, user.id)
        except UnknownExplainer:
            raise InvalidInput(NOT_KEPT) from None
        return asked_answer(document, site=context.site, data_note=DATA_NOTE)

    return ViewedTool("ask", "Ask KalaVigyan", ASK_DESCRIPTION, Ask, AskedAnswer, run, ASK_SCOPE, WRITES)


async def _asked(context: ToolContext, user: User, arguments: Ask) -> AnswerAsk:
    depth = arguments.depth or default_depth(user)
    refusal = await ask_refusal(context.session, user, depth)
    if refusal is not None:
        raise InvalidInput(refusal)
    style = await asker_reading_style(context.session, user)
    throttled = throttle_refusal(user)
    if throttled is not None:
        raise InvalidInput(throttled)
    await release_connection(context.session)
    return AnswerAsk(
        question=arguments.question,
        depth=depth,
        craft_slug=arguments.craft_slug,
        any_craft=arguments.any_craft,
        language=arguments.language,
        user_id=user.id,
        role=role_value(user),
        withheld_terms=withheld_terms(user),
        reading_style=style,
    )


async def _start_image_upload(context: ToolContext, arguments: StartImageUpload) -> UploadStart:
    user = _signed_in(context)
    slot = _slot(arguments)
    issued = await upload_links.start_upload(
        context.session, user, slot, arguments.declaration, now=datetime.now(UTC)
    )
    endpoints = endpoints_or_none()
    upload_url = (
        None
        if issued.slot_token is None or endpoints is None
        else slot_upload_url(endpoints.issuer, issued.slot_token)
    )
    return UploadStart(
        link=upload_page_url(context.site, issued.link_token),
        expires_at=issued.expires_at,
        upload_url=upload_url,
        craft=issued.craft,
        stage=issued.stage,
        facts=issued.facts,
        declared=arguments.declaration is not None,
        next_step=LINK_STEP if upload_url is None else SHELL_STEP,
    )


def _slot(arguments: StartImageUpload) -> UploadSlot:
    try:
        return UploadSlot(
            craft_slug=arguments.craft_slug, stage_id=arguments.stage_id, claim_ids=arguments.claim_ids
        )
    except ValidationError as refused:
        raise InvalidInput("; ".join(str(problem["msg"]) for problem in refused.errors())) from None


def _signed_in(context: ToolContext) -> User:
    if context.user is None:
        raise InvalidInput(SIGN_IN)
    return context.user


START_IMAGE_UPLOAD = Tool(
    "start_image_upload",
    "Start giving a picture",
    START_DESCRIPTION,
    StartImageUpload,
    UploadStart,
    _start_image_upload,
    CONTRIBUTE_SCOPE,
    WRITES,
)
ASK_TOOLS: tuple[Tool, ...] = (ask_tool(AskTools()), START_IMAGE_UPLOAD)
