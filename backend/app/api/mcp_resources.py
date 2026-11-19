from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from app.data.answer_kit import answer_kit, answer_view
from app.data.contributor_kit import SITE_SKILL_PATH, contributor_skill, design_tokens
from app.research.mcp_ask import ANSWER_VIEW_MIME, ANSWER_VIEW_URI

from .mcp_protocol import INVALID_PARAMS, RESOURCE_NOT_FOUND, RequestError

__all__ = [
    "ANSWER_KIT_URI",
    "ANSWER_VIEW_URI",
    "CONTRIBUTOR_SKILL_URI",
    "DESIGN_TOKENS_URI",
    "RESOURCES",
    "VIEW_META",
    "resource_list",
    "resource_read",
    "resource_templates",
]

CONTRIBUTOR_SKILL_URI = "kalavigyan://skills/kalavigyan-contributor/SKILL.md"
DESIGN_TOKENS_URI = "kalavigyan://design/tokens.json"
ANSWER_KIT_URI = "kalavigyan://design/answer-kit.md"
MARKDOWN = "text/markdown"
JSON = "application/json"
VIEW_META: Mapping[str, Any] = MappingProxyType(
    {"ui": {"prefersBorder": True, "csp": {"connectDomains": [], "resourceDomains": []}}}
)


@dataclass(frozen=True)
class Resource:
    uri: str
    name: str
    title: str
    description: str
    mime_type: str
    text: Callable[[], str]
    meta: Mapping[str, Any] = field(default_factory=dict)

    def listed(self, site: str) -> dict[str, Any]:
        listed = {
            "uri": self.uri,
            "name": self.name,
            "title": self.title,
            "description": self.description.format(site=site),
            "mimeType": self.mime_type,
            "size": len(self.text().encode("utf-8")),
        }
        return {**listed, "_meta": dict(self.meta)} if self.meta else listed

    def contents(self) -> dict[str, Any]:
        content = {"uri": self.uri, "mimeType": self.mime_type, "text": self.text()}
        return {**content, "_meta": dict(self.meta)} if self.meta else content


RESOURCES: Mapping[str, Resource] = MappingProxyType(
    {
        resource.uri: resource
        for resource in (
            Resource(
                CONTRIBUTOR_SKILL_URI,
                "kalavigyan-contributor",
                "The KalaVigyan contributor skill",
                "The method for researching and proposing to KalaVigyan, for agents that load skills: the tools "
                "in order, what counts as a source, verbatim quotes with locators, one fact per sentence, the "
                "fields and the page checklist. Also at {site}" + SITE_SKILL_PATH + ".",
                MARKDOWN,
                contributor_skill,
            ),
            Resource(
                DESIGN_TOKENS_URI,
                "kalavigyan-design-tokens",
                "The KalaVigyan design tokens",
                "The design system's tokens (Alum & Indigo): colours by role for light, dark and high contrast, "
                "type, spacing, motion and the components' specs, for agents that draw KalaVigyan content "
                "themselves.",
                JSON,
                design_tokens,
            ),
            Resource(
                ANSWER_KIT_URI,
                "kalavigyan-answer-kit",
                "How a KalaVigyan answer is drawn",
                "For agents that draw an ask result themselves: the order of an answer, its sections, citation "
                "clusters, component cards, sources and credit, with the light and dark tokens they use.",
                MARKDOWN,
                answer_kit,
            ),
            Resource(
                ANSWER_VIEW_URI,
                "kalavigyan-answer-view",
                "A KalaVigyan answer",
                "The MCP App that draws an ask result in KalaVigyan's design, from the result's structured data "
                "alone: it loads nothing from the network and shows every text as text.",
                ANSWER_VIEW_MIME,
                answer_view,
                VIEW_META,
            ),
        )
    }
)


def resource_list(site: str) -> dict[str, Any]:
    return {"resources": [resource.listed(site) for resource in RESOURCES.values()]}


def resource_templates() -> dict[str, Any]:
    return {"resourceTemplates": []}


def resource_read(params: Mapping[str, Any]) -> dict[str, Any]:
    uri = params.get("uri")
    if not isinstance(uri, str):
        raise RequestError(INVALID_PARAMS, "resources/read needs the uri of a resource")
    resource = RESOURCES.get(uri)
    if resource is None:
        raise RequestError(RESOURCE_NOT_FOUND, f"no resource has the uri {uri}; resources/list gives them")
    return {"contents": [resource.contents()]}
