from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache, partial
from types import MappingProxyType
from typing import Any

from app.data.contributor_kit import contributor_skill
from app.data.skill_library import REFERENCES, SKILL_FILES, reference_text, skill_file_text
from app.research.bar_references import worked_topic
from app.services.bar_references import worked_chapters, worked_text

from .mcp_guides import bar_text
from .mcp_protocol import INVALID_PARAMS, RequestError

__all__ = [
    "AJRAKH_SKILL",
    "CONTRIBUTOR_SKILL",
    "SKILLS",
    "SKILL_ENTRY",
    "SKILL_SCHEME",
    "McpSkill",
    "SkillPart",
    "ajrakh_skill_text",
    "frontmatter",
    "is_skill_uri",
    "skill_get",
    "skill_list",
    "skill_read",
]

SKILL_SCHEME = "skill://"
SKILL_ENTRY = "SKILL.md"
MARKDOWN = "text/markdown"
CONTRIBUTOR_SKILL = "kalavigyan-contributor"
AJRAKH_SKILL = "kalavigyan-ajrakh"
FENCE = "---"
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX, DESCRIPTION_MAX = 64, 1024
PLAIN_START = re.compile(r"^[A-Za-z0-9(]")
NO_SKILL = "no skill has the uri {uri}; skills/list gives them"
NO_FILE = "no skill file has the uri {uri}; its skill's entry lists its files"
AJRAKH_DESCRIPTION = (
    "Kutch Ajrakh's page, the one the owner approved and the bar every KalaVigyan page is set beside, worked "
    "through chapter by chapter, with each chapter's text in order and every component with its kind, its spec, "
    "its place and the sentences around it. Load it whenever someone asks to build or deepen a KalaVigyan page, "
    "propose facts for one or deliver a figure, component, map, layout or picture for it, to see how Ajrakh's "
    "own facts called for each figure. Read it for the thinking and never as a template, since a page holds the "
    "figures its own craft's facts call for."
)
AJRAKH_CHAPTERS = (
    "\n## The chapters, worked through\n\n"
    "Each chapter of Kutch Ajrakh's page is a file of this skill, the same text the server serves as the guide "
    "named beside it:\n\n"
)


@dataclass(frozen=True)
class SkillPart:
    path: str
    text: Callable[[], str]


@dataclass(frozen=True)
class McpSkill:
    name: str
    parts: tuple[SkillPart, ...]

    @property
    def uri(self) -> str:
        return self.file_uri(SKILL_ENTRY)

    def file_uri(self, path: str) -> str:
        return f"{SKILL_SCHEME}{self.name}/{path}"

    def part(self, path: str) -> SkillPart | None:
        return next((part for part in self.parts if part.path == path), None)


def frontmatter(text: str) -> dict[str, str]:
    lines = text.split("\n")
    if not lines or lines[0] != FENCE or FENCE not in lines[1:]:
        raise ValueError("a SKILL.md opens with YAML frontmatter between two --- lines")
    held: dict[str, str] = {}
    for line in lines[1 : lines.index(FENCE, 1)]:
        key, colon, value = line.partition(": ")
        if (
            not colon
            or not key
            or key in held
            or not PLAIN_START.match(value)
            or ": " in value
            or " #" in value
        ):
            raise ValueError(f"the frontmatter line {line[:60]!r} is not one plain key: value")
        held[key] = value
    return held


def ajrakh_skill_text() -> str:
    head = f"{FENCE}\nname: {AJRAKH_SKILL}\ndescription: {AJRAKH_DESCRIPTION}\n{FENCE}\n\n"
    listed = "".join(
        f"- `chapters/{chapter}.md` (the guide `{worked_topic(chapter)}/1`)\n"
        for chapter in worked_chapters()
    )
    return head + bar_text() + AJRAKH_CHAPTERS + listed


def _contributor() -> McpSkill:
    references = tuple(
        SkillPart(f"references/{reference.file_name}", partial(reference_text, name))
        for name, reference in REFERENCES.items()
    )
    return McpSkill(CONTRIBUTOR_SKILL, (SkillPart(SKILL_ENTRY, contributor_skill), *references))


def _served(skill: str) -> McpSkill:
    files = [file for file in SKILL_FILES.values() if file.skill == skill]
    ordered = sorted(files, key=lambda file: file.name != SKILL_ENTRY)
    return McpSkill(
        skill, tuple(SkillPart(file.name, partial(skill_file_text, file.uri)) for file in ordered)
    )


def _ajrakh() -> McpSkill:
    chapters = tuple(
        SkillPart(f"chapters/{chapter}.md", partial(worked_text, chapter)) for chapter in worked_chapters()
    )
    return McpSkill(AJRAKH_SKILL, (SkillPart(SKILL_ENTRY, ajrakh_skill_text), *chapters))


def _registry() -> Mapping[str, McpSkill]:
    served = dict.fromkeys(file.skill for file in SKILL_FILES.values())
    skills = (_contributor(), *(_served(skill) for skill in served), _ajrakh())
    return MappingProxyType({skill.uri: skill for skill in skills})


SKILLS: Mapping[str, McpSkill] = _registry()


def skill_list() -> dict[str, Any]:
    return {"skills": [_entry(uri) for uri in SKILLS]}


def skill_get(params: Mapping[str, Any]) -> dict[str, Any]:
    uri = params.get("uri")
    if not isinstance(uri, str) or uri not in SKILLS:
        raise RequestError(INVALID_PARAMS, NO_SKILL.format(uri=uri))
    return {"skill": _entry(uri)}


def is_skill_uri(uri: Any) -> bool:
    return isinstance(uri, str) and uri.startswith(SKILL_SCHEME)


def skill_read(uri: str) -> dict[str, Any]:
    name, _, path = uri.removeprefix(SKILL_SCHEME).partition("/")
    skill = SKILLS.get(f"{SKILL_SCHEME}{name}/{SKILL_ENTRY}")
    part = None if skill is None else skill.part(path)
    if part is None:
        raise RequestError(INVALID_PARAMS, NO_FILE.format(uri=uri))
    return {"contents": [{"uri": uri, "mimeType": MARKDOWN, "text": part.text()}]}


@cache
def _entry(uri: str) -> dict[str, Any]:
    skill = SKILLS[uri]
    held = frontmatter(skill.parts[0].text())
    _check_names(skill, held)
    resources = []
    for part in skill.parts:
        data = part.text().encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        resources.append({"uri": skill.file_uri(part.path), "digest": f"sha256:{digest}", "size": len(data)})
    return {"uri": skill.uri, "frontmatter": held, "resources": resources}


def _check_names(skill: McpSkill, held: Mapping[str, str]) -> None:
    name, description = held.get("name", ""), held.get("description", "")
    if name != skill.name or len(name) > NAME_MAX or NAME.match(name) is None or "--" in name:
        raise ValueError(f"the skill {skill.name} names itself {name!r} in its frontmatter")
    if not 0 < len(description) <= DESCRIPTION_MAX:
        raise ValueError(f"the skill {skill.name}'s description is 1 to {DESCRIPTION_MAX} characters")
