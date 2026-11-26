import hashlib
from typing import Any

import pytest

from app.api.mcp_guides import bar_text, guide_sheets
from app.api.mcp_skills import ajrakh_skill_text, frontmatter
from app.data.skill_library import REFERENCES, SKILL_FILES
from app.services.bar_references import worked_chapters

from .modern_client import SKILLS, bare_context, error_of, legacy, modern, result_of

CONTRIBUTOR = "skill://kalavigyan-contributor/SKILL.md"
AJRAKH = "skill://kalavigyan-ajrakh/SKILL.md"
LISTED = [
    CONTRIBUTOR,
    "skill://kalavigyan-datasets/SKILL.md",
    "skill://kalavigyan-interactives/SKILL.md",
    "skill://kalavigyan-design/SKILL.md",
    AJRAKH,
]
DESCRIPTION_MAX = 1024
TRIGGERS = ("build or deepen a KalaVigyan page", "propose facts", "deliver a figure")


async def listed() -> list[dict[str, Any]]:
    result = await result_of(modern("skills/list", capabilities=SKILLS), bare_context())
    assert (result["resultType"], result["ttlMs"], result["cacheScope"]) == ("complete", 300_000, "public")
    return result["skills"]


async def read_text(uri: str, *, modern_client: bool = True) -> str:
    asked = {"uri": uri}
    message = (
        modern("resources/read", asked, capabilities=SKILLS)
        if modern_client
        else legacy("resources/read", asked)
    )
    result = await result_of(message, bare_context())
    (content,) = result["contents"]
    assert (content["uri"], content["mimeType"]) == (uri, "text/markdown")
    return content["text"]


def resource_uri(skill_uri: str) -> str:
    name, _, path = skill_uri.removeprefix("skill://").partition("/")
    if name == "kalavigyan-contributor" and path.startswith("references/"):
        return f"kalavigyan://skills/{path}"
    return f"kalavigyan://skills/{name}/{path}"


async def test_the_five_skills_are_listed_each_with_its_frontmatter_and_whole_manifest() -> None:
    skills = await listed()
    assert [skill["uri"] for skill in skills] == LISTED
    for skill in skills:
        name = skill["uri"].removeprefix("skill://").split("/")[0]
        assert skill["frontmatter"]["name"] == name
        assert 0 < len(skill["frontmatter"]["description"]) <= DESCRIPTION_MAX
        assert skill["resources"][0]["uri"] == skill["uri"]
        for resource in skill["resources"]:
            data = (await read_text(resource["uri"])).encode("utf-8")
            assert resource["size"] == len(data), resource["uri"]
            assert resource["digest"] == "sha256:" + hashlib.sha256(data).hexdigest(), resource["uri"]
        entry = await read_text(skill["uri"])
        assert frontmatter(entry) == skill["frontmatter"]


async def test_the_contributor_skill_carries_the_playbook_the_cookbook_and_the_other_references() -> None:
    contributor = next(skill for skill in await listed() if skill["uri"] == CONTRIBUTOR)
    files = [
        resource["uri"].removeprefix("skill://kalavigyan-contributor/")
        for resource in contributor["resources"]
    ]
    assert files[0] == "SKILL.md"
    assert {"references/playbook.md", "references/cookbook.md"} <= set(files)
    assert set(files[1:]) == {f"references/{reference.file_name}" for reference in REFERENCES.values()}


async def test_each_skill_file_is_the_very_text_a_client_without_the_extension_reads_as_a_resource() -> None:
    served = [skill for skill in await listed() if skill["uri"] != AJRAKH]
    files = [resource["uri"] for skill in served for resource in skill["resources"]]
    assert len(files) == 1 + len(REFERENCES) + len(SKILL_FILES)
    for uri in files:
        assert await read_text(uri) == await read_text(resource_uri(uri), modern_client=False), uri


async def test_ajrakh_worked_through_is_the_bar_and_each_chapter_its_guide_serves() -> None:
    ajrakh = next(skill for skill in await listed() if skill["uri"] == AJRAKH)
    chapters = [resource["uri"] for resource in ajrakh["resources"][1:]]
    assert chapters == [f"skill://kalavigyan-ajrakh/chapters/{chapter}.md" for chapter in worked_chapters()]
    entry = await read_text(AJRAKH)
    assert entry == ajrakh_skill_text() and bar_text() in entry
    for chapter in worked_chapters():
        whole = "".join(sheet.text for sheet in guide_sheets(f"ajrakh-{chapter}"))
        assert await read_text(f"skill://kalavigyan-ajrakh/chapters/{chapter}.md") == whole, chapter
        assert f"`chapters/{chapter}.md`" in entry


async def test_a_client_without_the_extension_still_gets_every_skill_as_a_resource() -> None:
    resources = {
        resource["uri"]
        for resource in (await result_of(legacy("resources/list"), bare_context()))["resources"]
    }
    assert "kalavigyan://skills/kalavigyan-contributor/SKILL.md" in resources
    assert {
        f"kalavigyan://skills/references/{reference.file_name}" for reference in REFERENCES.values()
    } <= resources
    assert set(SKILL_FILES) <= resources
    assert all(not uri.startswith("skill://") for uri in resources)


async def test_skills_get_answers_by_uri_and_refuses_what_it_does_not_serve() -> None:
    result = await result_of(modern("skills/get", {"uri": CONTRIBUTOR}, capabilities=SKILLS), bare_context())
    assert result["skill"] == next(skill for skill in await listed() if skill["uri"] == CONTRIBUTOR)
    assert result["cacheScope"] == "public"
    for asked in ({"uri": "skill://kalavigyan-nothing/SKILL.md"}, {}):
        refused = await error_of(modern("skills/get", asked, capabilities=SKILLS), bare_context())
        assert refused["code"] == -32602
    missing = await error_of(
        modern("resources/read", {"uri": "skill://kalavigyan-contributor/references/nowhere.md"}),
        bare_context(),
    )
    assert missing["code"] == -32602


@pytest.mark.parametrize("uri", [CONTRIBUTOR, AJRAKH])
async def test_the_description_tells_an_agent_to_load_it_for_pages_facts_and_figures(uri: str) -> None:
    description = next(skill for skill in await listed() if skill["uri"] == uri)["frontmatter"]["description"]
    for trigger in TRIGGERS:
        assert trigger in description, trigger


@pytest.mark.parametrize(
    "text",
    [
        "name: x\n---\n",
        "---\nname: x\ndescription: one: two\n---\n",
        "---\nname: x\ndescription: words # a comment\n---\n",
        "---\nname: x\nname: y\n---\n",
        "---\nname: x\ndescription: 'quoted'\n---\n",
    ],
)
def test_the_frontmatter_reader_refuses_what_a_yaml_reader_would_read_otherwise(text: str) -> None:
    with pytest.raises(ValueError):
        frontmatter(text)
