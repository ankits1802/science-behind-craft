from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal, Self

from pydantic import Field, field_serializer, model_validator

from app.core.errors import InvalidInput, NotConfigured
from app.core.mcp_scopes import CONTRIBUTE_SCOPE
from app.research.base import ContractModel
from app.research.crafts import SLUG_MAX_CHARS
from app.research.page_proposals import PageComponent
from app.services.compose_components import COMPOSED_KINDS, ComposeDeps, compose_component
from app.services.compose_held import About

from .mcp_guide_steps import HandedGuide, storyboard_guide
from .mcp_studio_arguments import STUDIO_DOES, StudioArguments
from .mcp_tool_base import LOOKS, PAGES, Arguments, Tool, ToolContext, contributor

__all__ = [
    "COMPOSE_COMPONENT",
    "COMPOSE_TOOLS",
    "ComposeAbout",
    "ComposeComponent",
    "ComposeReply",
    "compose_tools",
]

NAME = "compose_component"
ENTRY_KEY = r"^[A-Z]\d{2,4}$"
SLUG = r"^[A-Za-z0-9-]+$"
ONE_ABOUT = "name at most one of stage, reaction, material and compound"
DESCRIPTION = (
    "A helper of the page playbook's step 6 (playbook/1): it can save the work of a figure you designed, and its "
    "result is yours to take, change or set aside for a coded figure. Compose a craft's own interactive from "
    "the facts and structure its page holds, as the server builds "
    "it: reaction_player from its stored reactions in the order of their stages, dip_player from its stages in "
    "a bath with their colour after, drawn as the depicted colour of the dye, mordant or resist named, molecule_3d "
    "from a compound its materials name with PubChem's 3D conformer (atoms, bonds, turned and zoomed by "
    "pointer, touch and keyboard), experiment_lab from the alternatives its facts compare, with a toggle for "
    "each. Every state and label cites only that craft's own facts; nothing is borrowed from another page. "
    "about narrows it to one stage, reaction or material key (get_facts gives them) or a compound's CID. The "
    "result is finished components ({proposal, cites}) to place with edit_draft's add, with your task_key set "
    "on the proposal; preview_page, then propose_page. When the facts are not enough it composes nothing and "
    "missing lists exactly which facts or structure to propose first; left_out names what it could not "
    "draw, each a stage, reaction, material or compound to compose again with about once its facts are held, "
    "or a figure to code. guide hands over the storyboard's pages."
)
COMPOSED = "Composed {count} component{s} for {slug} from its own facts."
REFUSED = "Nothing was composed for {slug}: propose what missing lists first, then compose again."
PLACE = (
    "Add the components to the page's draft with edit_draft (add.components, as they are), set task_key on "
    "the proposal if you claimed one, or set them aside where your own design says it better. Build the "
    "page's other figures (coded figures and the kinds of the cookbook, cookbook/1), lay the page out, call "
    "preview_page and read every picture of the report before propose_page; if propose_page names a close "
    "match, propose it again as a VARIANT that extends it."
)
PROPOSE = (
    "Propose each item of missing with propose_facts or propose_structure, then call compose_component again."
)


class ComposeAbout(Arguments):
    stage: str | None = Field(default=None, pattern=ENTRY_KEY, description="A stage key, such as S03")
    reaction: str | None = Field(default=None, pattern=ENTRY_KEY, description="A reaction key, such as R01")
    material: str | None = Field(default=None, pattern=ENTRY_KEY, description="A material key, such as M05")
    compound: int | None = Field(default=None, ge=1, description="A PubChem CID one of its materials holds")

    @model_validator(mode="after")
    def _one_at_most(self) -> Self:
        given = [
            value for value in (self.stage, self.reaction, self.material, self.compound) if value is not None
        ]
        if len(given) > 1:
            raise ValueError(ONE_ABOUT)
        return self

    def about(self) -> About:
        return About(stage=self.stage, reaction=self.reaction, material=self.material, compound=self.compound)


class ComposeComponent(StudioArguments):
    craft: str = Field(min_length=1, max_length=SLUG_MAX_CHARS, pattern=SLUG, description="The craft's slug")
    kind: Literal[*COMPOSED_KINDS] = Field(description=f"One of {', '.join(COMPOSED_KINDS)}")
    about: ComposeAbout | None = Field(default=None, description="What it is about, at most one key")


class ComposeReply(ContractModel):
    craft: str
    kind: str
    composed: bool
    components: list[PageComponent] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    left_out: list[str] = Field(default_factory=list)
    message: str
    next_step: str
    notices: list[str] = Field(default_factory=list)
    guide: HandedGuide

    @field_serializer("components")
    def _as_edit_draft_takes_them(self, components: list[PageComponent]) -> list[dict[str, Any]]:
        return [component.model_dump(mode="json", by_alias=False) for component in components]


def _run(deps: ComposeDeps) -> Callable[[ToolContext, ComposeComponent], Awaitable[ComposeReply]]:
    async def run(context: ToolContext, arguments: ComposeComponent) -> ComposeReply:
        contributor(context, NAME, STUDIO_DOES)
        about = arguments.about.about() if arguments.about is not None else About()
        try:
            result = await compose_component(context.session, deps, arguments.craft, arguments.kind, about)
        except NotConfigured as missing:
            raise InvalidInput(missing.message) from None
        count = len(result.components)
        said = COMPOSED.format(count=count, s="" if count == 1 else "s", slug=arguments.craft)
        return ComposeReply(
            craft=arguments.craft,
            kind=arguments.kind,
            composed=result.composed,
            components=list(result.components),
            missing=list(result.missing),
            left_out=list(result.left_out),
            message=said if result.composed else REFUSED.format(slug=arguments.craft),
            next_step=PLACE if result.composed else PROPOSE,
            notices=arguments.notices(),
            guide=storyboard_guide(),
        )

    return run


def compose_tools(deps: ComposeDeps) -> tuple[Tool, ...]:
    return (
        Tool(
            NAME,
            "Compose a craft's own interactive",
            DESCRIPTION,
            ComposeComponent,
            ComposeReply,
            _run(deps),
            CONTRIBUTE_SCOPE,
            LOOKS,
            group=PAGES,
        ),
    )


COMPOSE_TOOLS = compose_tools(ComposeDeps())
COMPOSE_COMPONENT = COMPOSE_TOOLS[0]
