import uuid
from typing import Any

import pytest

from app.api.mcp_compose_tools import ComposeComponent, compose_tools
from app.api.mcp_page_arguments import EditDraft
from app.api.mcp_tool_base import LOOKS, PAGES, ToolContext
from app.api.mcp_tools import TOOLS
from app.core.errors import InvalidInput
from app.core.mcp_scopes import CONTRIBUTE_SCOPE
from app.models import User
from app.services.compose_components import ComposeDeps
from app.services.compose_held import CraftHeld
from app.services.craft_resolver import CraftIndexStore

from ..compose.held import BAGRU, CONFORMER_SDF, SLUG

SITE = "https://kalavigyan.example"


class Conformers:
    def __init__(self) -> None:
        self.asked: list[int] = []

    async def conformer(self, cid: int) -> str | None:
        self.asked.append(cid)
        return CONFORMER_SDF if cid == 6293 else None


def deps(held: CraftHeld | None = BAGRU, conformers: Conformers | None = None) -> ComposeDeps:
    async def read(_session: Any, slug: str) -> CraftHeld | None:
        assert slug == SLUG
        return held

    async def opened() -> Conformers:
        return conformers or Conformers()

    return ComposeDeps(held=read, conformers=opened)


def context(role: str = "RESEARCHER") -> ToolContext:
    user = User(id=uuid.UUID(int=7), name="Contributor", email="c@example.org", role=role)
    return ToolContext(
        session=None, index=CraftIndexStore(), site=SITE, user=user, scopes=frozenset({"contribute"})
    )  # type: ignore[arg-type]


async def composed(
    arguments: dict[str, Any], held: CraftHeld | None = BAGRU, role: str = "RESEARCHER"
) -> dict[str, Any]:
    (tool,) = compose_tools(deps(held))
    reply = await tool.run(context(role), ComposeComponent.model_validate(arguments))
    return reply.model_dump(mode="json", by_alias=True)


def test_the_tool_sits_in_the_pages_group_beside_edit_draft_and_writes_nothing() -> None:
    tool = TOOLS["compose_component"]
    assert (tool.group, tool.scope, dict(tool.annotations)) == (PAGES, CONTRIBUTE_SCOPE, dict(LOOKS))
    assert not tool.commits and "outputSchema" not in tool.listed()
    kinds = tool.listed()["inputSchema"]["properties"]["kind"]["enum"]
    assert kinds == ["reaction_player", "dip_player", "molecule_3d", "experiment_lab", None]


async def test_a_composed_component_goes_into_a_draft_as_edit_draft_takes_it_with_no_notices() -> None:
    reply = await composed({"craft": SLUG, "kind": "reaction_player"})
    assert reply["composed"] and reply["missing"] == []
    (component,) = reply["components"]
    assert "craft_slug" in component["proposal"] and "craftSlug" not in component["proposal"]
    draft = EditDraft.model_validate(
        {"subject": {"kind": "craft", "slug": SLUG}, "add": {"components": [component]}}
    )
    assert draft.notices() == []
    assert draft.add is not None and draft.add.components[0].proposal.kind == "reaction_player"


async def test_a_molecule_reads_pubchem_s_conformer_once_for_each_compound() -> None:
    conformers = Conformers()
    (tool,) = compose_tools(deps(conformers=conformers))
    arguments = ComposeComponent.model_validate({"craft": SLUG, "kind": "molecule_3d"})
    reply = await tool.run(context(), arguments)
    assert reply.composed and conformers.asked == [62667, 6293]
    assert reply.left_out == ["a 3D conformer for Potassium alum (CID 62667): PubChem holds none"]


async def test_a_craft_without_a_curated_page_composes_nothing_and_is_told_what_to_propose() -> None:
    reply = await composed({"craft": SLUG, "kind": "dip_player"}, held=None)
    assert not reply["composed"] and reply["components"] == []
    assert reply["missing"][0].startswith(f"a curated page for {SLUG}")
    assert "propose_facts" in reply["nextStep"]


async def test_only_a_contributor_composes_and_at_most_one_key_narrows_it() -> None:
    with pytest.raises(InvalidInput, match="Researcher or above"):
        await composed({"craft": SLUG, "kind": "dip_player"}, role="STUDENT")
    with pytest.raises(ValueError, match="at most one"):
        ComposeComponent.model_validate(
            {"craft": SLUG, "kind": "dip_player", "about": {"stage": "S01", "material": "M01"}}
        )


async def test_with_no_kind_one_call_composes_every_kind_the_facts_allow_ready_for_edit_draft() -> None:
    reply = await composed({"craft": SLUG})
    assert reply["composed"] and reply["kind"] is None
    kinds = [component["proposal"]["kind"] for component in reply["components"]]
    assert {"reaction_player", "dip_player", "molecule_3d", "experiment_lab"} <= set(kinds)
    assert reply["message"].startswith(f"Composed {len(kinds)} components for {SLUG} from its own facts: ")
    draft = EditDraft.model_validate(
        {"subject": {"kind": "craft", "slug": SLUG}, "add": {"components": reply["components"]}}
    )
    assert draft.add is not None and len(draft.add.components) == len(kinds)


async def test_with_no_kind_each_kind_left_uncomposed_names_its_kind_beside_what_it_needs() -> None:
    reply = await composed({"craft": SLUG}, held=None)
    assert not reply["composed"] and reply["components"] == []
    assert [line.split(":", 1)[0] for line in reply["missing"]] == [
        "reaction_player",
        "dip_player",
        "molecule_3d",
        "experiment_lab",
    ]
    assert "propose_facts" in reply["nextStep"]
    with pytest.raises(ValueError, match="about narrows one kind"):
        ComposeComponent.model_validate({"craft": SLUG, "about": {"stage": "S01"}})
