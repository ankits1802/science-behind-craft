from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from .contributor_kit import CONTRIBUTOR_SKILL_PATH

__all__ = [
    "CONTRACTS",
    "CONTRACTS_DIR",
    "CRITIQUE_REFERENCE",
    "DESIGN_SKILL",
    "INDEX_PATH",
    "INDEX_URI",
    "REFERENCES",
    "REFERENCES_DIR",
    "SKILL_ENTRY",
    "SKILL_FILES",
    "SKILL_URI_PREFIX",
    "Contract",
    "Reference",
    "SkillFile",
    "contract_text",
    "demoted",
    "prompt_reference",
    "reference_text",
    "server_index",
    "skill_file_text",
]

CONTRIBUTOR_DIR = CONTRIBUTOR_SKILL_PATH.parent
REFERENCES_DIR = CONTRIBUTOR_DIR / "references"
REFERENCE_URI_PREFIX = "kalavigyan://skills/references/"
REFERENCE_SITE_PREFIX = "/skills/references/"
CONTRACTS_DIR = CONTRIBUTOR_DIR / "contracts"
CONTRACT_URI_PREFIX = "kalavigyan://contracts/"
CONTRACT_REPOSITORY_PREFIX = "docs/contracts/"
INDEX_PATH = CONTRIBUTOR_DIR / "index.md"
INDEX_URI = "kalavigyan://index.md"
SKILL_URI_PREFIX = "kalavigyan://skills/"
SKILL_SITE_PREFIX = "/skills/"
SKILL_ENTRY = "SKILL.md"
DATASETS_SKILL = "kalavigyan-datasets"
INTERACTIVES_SKILL = "kalavigyan-interactives"
DESIGN_SKILL = "kalavigyan-design"
CRITIQUE_REFERENCE = "design-critique"
HEADING = re.compile(r"^(#+) ", re.MULTILINE)


@dataclass(frozen=True)
class Reference:
    name: str
    title: str
    holds: str

    @property
    def file_name(self) -> str:
        return f"{self.name}.md"

    @property
    def path(self) -> Path:
        return REFERENCES_DIR / self.file_name

    @property
    def uri(self) -> str:
        return REFERENCE_URI_PREFIX + self.file_name

    @property
    def site_path(self) -> str:
        return REFERENCE_SITE_PREFIX + self.file_name


REFERENCES: Mapping[str, Reference] = MappingProxyType(
    {
        reference.name: reference
        for reference in (
            Reference(
                "playbook",
                "The page playbook",
                "The order an agent follows to build a page to the Kutch Ajrakh bar without being told how: what "
                "to read before each step, what to compose, code and fill, what to ask the person, when a page is "
                "done and what to do when the site falls short",
            ),
            Reference(
                "cookbook",
                "The component cookbook",
                "Every component kind a page can carry: what it shows, when a page needs it, where Kutch Ajrakh "
                "uses it, which tool makes it, the facts it needs, how to place it and how to check it in the "
                "preview",
            ),
            Reference(
                "page-checklist",
                "The page checklist",
                "The 29 rules every craft, family, category and answer page meets, and the three lists each "
                "page derives first",
            ),
            Reference(
                CRITIQUE_REFERENCE,
                "The designer's critique",
                "How an agent reads its own preview's pictures as a designer before proposing: the rubric drawn "
                "from the design system and Kutch Ajrakh's chapters, the notes it writes chapter by chapter and "
                "how it records them with the next preview",
            ),
            Reference(
                "sources",
                "What counts as a source",
                "How sources are chosen, graded A to D and recorded, and the licences that let their material "
                "be shown",
            ),
            Reference(
                "quotes",
                "Quotes and locators",
                "Verbatim quotes, their locators and the one-fact-per-sentence rules every fact follows",
            ),
            Reference("fields", "The fields", "The sixteen fields a fact is filed under and what each holds"),
            Reference(
                "components",
                "Authoring a component",
                "Choosing among the 25 kinds a contributor delivers and their declared specs, units and citations "
                "in a spec, depicted materials, and the design rules for a contributed figure",
            ),
            Reference(
                "datasets",
                "Datasets",
                "The open datasets behind charts, tables, timelines and map layers: licences, provenance, units, "
                "projection, simplification, delivery and checks",
            ),
        )
    }
)


@dataclass(frozen=True)
class Contract:
    name: str
    title: str
    holds: str

    @property
    def file_name(self) -> str:
        return f"{self.name}.md"

    @property
    def path(self) -> Path:
        return CONTRACTS_DIR / self.file_name

    @property
    def uri(self) -> str:
        return CONTRACT_URI_PREFIX + self.file_name

    @property
    def repository_path(self) -> str:
        return CONTRACT_REPOSITORY_PREFIX + self.file_name


CONTRACTS: Mapping[str, Contract] = MappingProxyType(
    {
        contract.name: contract
        for contract in (
            Contract(
                "knowledge-writes",
                "The knowledge write path",
                "How a proposed fact, structure item, source and layout are checked and stored: the gates, "
                "their reasons, the queue, idempotency keys, trust tiers and the hourly limits",
            ),
            Contract(
                "open-work",
                "Open work and the method on the MCP server",
                "Tasks and their keys, reservations, stewardship, delivered components and pages, previews, "
                "the prompts and resources, and the source tools",
            ),
            Contract(
                "component-specs-general",
                "The declared component kinds",
                "The five kinds that take a declared spec (drawing, chart, fact_table, timeline, map_layer), "
                "one kind per job: their specs, units, citations, dataset cells and the checks a delivered spec passes",
            ),
            Contract(
                "image-contributions",
                "Picture contributions",
                "How a picture is given: the declaration, the formats accepted, the screens it passes, review "
                "and where an approved picture is drawn",
            ),
            Contract(
                "mcp-ask-and-upload",
                "Asking and uploading over MCP",
                "The ask tool, the answer view, single-use upload links and give_pictures",
            ),
        )
    }
)


@dataclass(frozen=True)
class SkillFile:
    skill: str
    name: str
    title: str
    holds: str

    @property
    def path(self) -> Path:
        return CONTRIBUTOR_DIR / self.skill / self.name

    @property
    def uri(self) -> str:
        return f"{SKILL_URI_PREFIX}{self.skill}/{self.name}"

    @property
    def site_path(self) -> str:
        return f"{SKILL_SITE_PREFIX}{self.skill}/{self.name}"

    @property
    def resource_name(self) -> str:
        if self.name == SKILL_ENTRY:
            return self.skill
        return f"{self.skill}-{PurePosixPath(self.name).stem}"


SKILL_FILES: Mapping[str, SkillFile] = MappingProxyType(
    {
        skill_file.uri: skill_file
        for skill_file in (
            SkillFile(
                DATASETS_SKILL,
                SKILL_ENTRY,
                "The KalaVigyan datasets skill",
                "The method for the data behind KalaVigyan's charts, tables, timelines and map layers: open "
                "datasets and their licences, provenance, units and projection, and how a dataset becomes a "
                "delivered component",
            ),
            SkillFile(
                INTERACTIVES_SKILL,
                SKILL_ENTRY,
                "The KalaVigyan interactives skill",
                "The method for a craft family's flagship interactive: its mechanism chosen from held facts, "
                "its states storyboarded with their citations, the kind that carries it, what a state may show, "
                "rest and motion, keyboard and phone, how crafts borrow it and how it is proven",
            ),
            SkillFile(
                INTERACTIVES_SKILL,
                "references/flagships.md",
                "The family flagships",
                "The nine families' candidate flagships, the facts each already holds for each state, the task "
                "to claim and what each still lacks",
            ),
            SkillFile(
                INTERACTIVES_SKILL,
                "references/storyboard.md",
                "The storyboard of a flagship",
                "The form a flagship is storyboarded in before any drawing, and a filled one",
            ),
            SkillFile(
                DESIGN_SKILL,
                SKILL_ENTRY,
                "The KalaVigyan design system skill",
                "The design system every KalaVigyan screen, figure and page is built in (Alum & Indigo): its "
                "principles, non-negotiables, tokens by role, type and scripts, motion, components, page "
                "templates, copy, accessibility and traps, the same text the site's own developers read",
            ),
            SkillFile(
                DESIGN_SKILL,
                "references/SYSTEM.md",
                "The KalaVigyan design system in full",
                "The whole design system: every token in the four themes, ramps, maps, type tables, scripts, "
                "every component's states, page templates and the decisions behind them",
            ),
        )
    }
)


@cache
def reference_text(name: str) -> str:
    return REFERENCES[name].path.read_bytes().decode("utf-8")


@cache
def contract_text(name: str) -> str:
    return CONTRACTS[name].path.read_bytes().decode("utf-8")


@cache
def server_index() -> str:
    return INDEX_PATH.read_bytes().decode("utf-8")


def prompt_reference(name: str) -> str:
    return demoted(reference_text(name))


def demoted(text: str) -> str:
    return HEADING.sub(r"#\1 ", text).strip()


@cache
def skill_file_text(uri: str) -> str:
    return SKILL_FILES[uri].path.read_bytes().decode("utf-8")
