from enum import StrEnum
from typing import Annotated, Any, Literal

import pytest
from pydantic import BaseModel, Field

from app.api.mcp_prompts import PROMPTS, prompt_list
from app.api.mcp_protocol import SERVER_INSTRUCTIONS
from app.api.mcp_schemas import compact, input_schema
from app.api.mcp_tool_base import READ_ONLY, Arguments
from app.api.mcp_tools import TOOLS
from app.core.config import get_settings
from app.data.contributor_kit import CONTRIBUTOR_SKILL_PATH
from app.data.skill_library import reference_text

from .listing_policy import described, description_problems, missing_title, untyped
from .modern_client import FILES, bare_context, legacy, modern, result_of

ADMIN = bare_context(scopes=frozenset({"read", "review"}))
MODERN, LEGACY = ERAS = ("2026-07-28", "2025-11-25")
FLAGGED = {
    "propose_dataset": ("proposal",),
    "propose_source": ("proposal",),
    "propose_structure": ("proposal",),
    "supply_source": ("identity", "access"),
}
OLD_DESCRIPTIONS = (
    ("propose_facts", "Read get_facts first: a held fact is refused."),
    ("propose_page", "Preview it first with preview_page: while the latest preview fails, it is refused."),
    (
        "give_pictures",
        "Ask the person first, in their words: that they took or made the picture; never fill the "
        "declaration in for them.",
    ),
    ("get_proposal", "Tell a person a fact is on the page only when readers.shown is true."),
    (
        "edit_draft",
        "Its place in the page playbook (playbook/1): open it at step 4; next_step names what follows.",
    ),
    ("preview_page", "A failure fails rule 28. guide hands over the checklist page of each failed rule."),
    ("report_site_gap", "A gap is the site's, never the person's: say so once, then go on building."),
    ("list_components", "Search it before you fill a spec by hand: one keyed to a concept is shared."),
    ("list_components", "The component cookbook (cookbook/1) says which tool makes each kind."),
    ("ask", "Otherwise show the answer_url, or draw it with the kalavigyan://design/answer-kit.md resource."),
    ("compose_component", "The result is finished components to place with edit_draft's add."),
)
DESCRIBING = (
    ("give_pictures", "Accepted: PNG, JPEG, WebP or AVIF as they are; GIF as its first frame."),
    ("propose_dataset", "The record names a sheet when a workbook's table is not its first sheet."),
    ("preview_page", "It returns pictures of the first screen at both widths and of each chapter."),
    ("read_source", "Reads a source, a DOI's open copy as the Unpaywall REST API finds it."),
    ("lookup", "A PubChem CID, or a Wikidata qid such as Q12345"),
)
LEFT_TO_THE_PLAYBOOK = (
    "`design-critique/1`",
    "`read_pictures`",
    "`read_token`",
    "`compose_component`",
    "next draft",
)
LEFT_TO_THE_SKILL = (
    "`readers.shown` is true",
    "Never fill in a picture's declaration",
    "test every quote before you propose it",
    "`list_components` first",
    "say once that it is KalaVigyan's gap",
    "`kalavigyan://admin/published-content.md`",
    "`kalavigyan://design/answer-kit.md`",
)
READ_SOURCE_APIS = (
    "Unpaywall REST API (https://unpaywall.org/products/api)",
    "Availability API, https://archive.org/help/wayback_api.php",
    "Save Page Now (https://web.archive.org/save)",
    "the publisher's page",
)


class Shade(StrEnum):
    INDIGO = "indigo"
    MADDER = "madder"


class Part(BaseModel):
    name: str


class Left(BaseModel):
    side: Literal["left"]


class Right(BaseModel):
    side: Literal["right"]


class Sample(Arguments):
    part: Part
    maybe: Part | None = None
    shade: Shade
    either: Annotated[Left | Right, Field(discriminator="side")]
    key: int | str | None = None
    parts: list[Part] = Field(default_factory=list)


@pytest.fixture
def uploads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "mcp_file_uploads_enabled", True)


async def listed(era: str) -> list[dict[str, Any]]:
    message = modern("tools/list", capabilities=FILES) if era == MODERN else legacy("tools/list")
    tools = (await result_of(message, ADMIN))["tools"]
    assert {tool["name"] for tool in tools} == set(TOOLS)
    return tools


@pytest.mark.parametrize("era", ERAS)
async def test_every_parameter_of_every_listed_tool_has_a_type(era: str, uploads: None) -> None:
    tools = {tool["name"]: tool for tool in await listed(era)}
    assert [where for name, tool in tools.items() for where in untyped(tool["inputSchema"], name)] == []
    for name, parameters in FLAGGED.items():
        for parameter in parameters:
            assert tools[name]["inputSchema"]["properties"][parameter]["type"] == "object", (name, parameter)
    for name in ("supply_source", "propose_dataset"):
        assert ("file" in tools[name]["inputSchema"]["properties"]) is (era == MODERN), (era, name)


def test_a_reference_a_nullable_one_a_choice_and_a_union_are_typed_once_for_every_tool() -> None:
    assert untyped(compact(Sample.model_json_schema())) == [
        "schema.part",
        "schema.maybe",
        "schema.shade",
        "schema.either",
        "schema.key",
    ]
    properties = input_schema(Sample)["properties"]
    assert {name: properties[name]["type"] for name in properties} == {
        "part": "object",
        "maybe": ["object", "null"],
        "shade": "string",
        "either": "object",
        "key": ["integer", "string", "null"],
        "parts": "array",
    }
    assert properties["parts"]["items"]["type"] == "object" and "$ref" in properties["part"]
    assert untyped(input_schema(Sample)) == []


@pytest.mark.parametrize("era", ERAS)
async def test_every_listed_tool_carries_its_title_as_an_annotation_with_its_hints(
    era: str, uploads: None
) -> None:
    for tool in await listed(era):
        assert not missing_title(tool) and tool["annotations"]["title"] == TOOLS[tool["name"]].title
        hints = (tool["annotations"]["readOnlyHint"], tool["annotations"]["destructiveHint"])
        assert all(isinstance(hint, bool) for hint in hints), tool["name"]


def test_a_listing_without_its_title_annotation_or_with_another_is_refused() -> None:
    assert missing_title({"title": "Find crafts", "annotations": dict(READ_ONLY)})
    assert missing_title({"title": "Find crafts", "annotations": {**READ_ONLY, "title": "Craft finder"}})
    assert not missing_title({"title": "Find crafts", "annotations": {**READ_ONLY, "title": "Find crafts"}})


@pytest.mark.parametrize("era", ERAS)
async def test_every_tool_and_parameter_description_only_describes(era: str, uploads: None) -> None:
    found = {
        where: problems
        for tool in await listed(era)
        for where, text in described(tool)
        if (problems := description_problems(text, tool["name"], TOOLS))
    }
    assert found == {}


@pytest.mark.parametrize(("name", "text"), OLD_DESCRIPTIONS)
def test_the_policy_refuses_what_the_old_descriptions_said(name: str, text: str) -> None:
    assert description_problems(text, name, TOOLS), text


@pytest.mark.parametrize(("name", "text"), DESCRIBING)
def test_the_policy_passes_a_sentence_that_only_describes(name: str, text: str) -> None:
    assert description_problems(text, name, TOOLS) == []


def test_read_source_names_the_services_it_reads_with_their_documentation() -> None:
    description = TOOLS["read_source"].description
    for named in READ_SOURCE_APIS:
        assert named in description, named


def test_the_guidance_the_descriptions_left_is_where_an_agent_reads_it_unaided() -> None:
    assert "playbook/1" in SERVER_INSTRUCTIONS and "kalavigyan-contributor" in SERVER_INSTRUCTIONS
    playbook = reference_text("playbook")
    skill = CONTRIBUTOR_SKILL_PATH.read_text(encoding="utf-8")
    assert [said for said in LEFT_TO_THE_PLAYBOOK if said not in playbook] == []
    assert [said for said in LEFT_TO_THE_SKILL if said not in skill] == []


def test_no_prompt_is_listed_as_a_tool_or_lends_a_tool_its_description() -> None:
    prompts = prompt_list()["prompts"]
    assert set(PROMPTS).isdisjoint(TOOLS) and {prompt["name"] for prompt in prompts} == set(PROMPTS)
    assert {prompt["description"] for prompt in prompts}.isdisjoint(
        tool.description for tool in TOOLS.values()
    )


def named_properties(node: Any, name: str) -> list[dict[str, Any]]:
    if isinstance(node, list):
        return [found for item in node for found in named_properties(item, name)]
    if not isinstance(node, dict):
        return []
    own = node.get("properties")
    found = [own[name]] if isinstance(own, dict) and isinstance(own.get(name), dict) else []
    return found + [each for value in node.values() for each in named_properties(value, name)]


@pytest.mark.parametrize("era", ERAS)
async def test_a_section_is_typed_in_a_draft_s_add_and_in_a_bundle_and_adds_no_tool(
    era: str, uploads: None
) -> None:
    tools = {tool["name"]: tool for tool in await listed(era)}
    assert not [name for name in tools if "section" in name]
    schema = tools["edit_draft"]["inputSchema"]
    added = named_properties(schema, "sections")
    assert [(part["type"], part["maxItems"]) for part in added] == [("array", 16)]
    assert "takes the place of the field's published section" in added[0]["description"]
    sentences = named_properties(schema, "sentences")
    assert sentences and all(found["type"] == "array" for found in sentences)
    assert named_properties(schema, "claim_ids") and not named_properties(schema, "claimIds")
    for name in ("preview_page", "propose_page"):
        bundle = tools[name]["inputSchema"]["properties"]["bundle"]
        assert bundle["properties"]["sections"] == {
            "type": "array",
            "items": {"type": "object"},
            "maxItems": 16,
        }
        assert "sections ({field, sentences [{text, claim_ids}]})" in bundle["description"]
        assert "section" in tools[name]["description"]
