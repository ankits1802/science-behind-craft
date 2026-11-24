from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Literal

from pydantic import Field

from app.models.page_previews import PREVIEW_DRAWINGS

from .base import ContractModel
from .monograph_document import MonographDocument
from .page_report_rules import OPENING, PICTURE_KIND

__all__ = [
    "BROWSER",
    "BUSY",
    "CHAPTERS_SHOWN_MAX",
    "CHAPTER_SCALE",
    "CHAPTER_VIEW_HEIGHT",
    "CHECKED",
    "DESKTOP_WIDTH",
    "DRAWING_STATES",
    "ELSEWHERE",
    "FAILED",
    "FIRST_SCREEN_SCALES",
    "IMAGE_BYTES_MAX",
    "INTERACTIVE_KINDS",
    "JPEG_QUALITY",
    "MAP_KINDS",
    "PAGE_LABEL",
    "PHONE_WIDTH",
    "PICTURE_HOSTS",
    "QUEUE_SECONDS",
    "REFUSED",
    "RENDERER_HEALTH_PATH",
    "RENDERER_PATH",
    "RENDER_PASS_HEADER",
    "RENDER_SECONDS",
    "ROLES",
    "TIMEOUT",
    "UNMADE",
    "UNMADE_REASONS",
    "UNREACHABLE",
    "VIEW_HEIGHTS",
    "WIDTHS",
    "DrawingReport",
    "DrawnImage",
    "DrawnProblem",
    "RenderPlan",
    "RenderRequest",
    "RenderResult",
    "RenderUnmade",
    "RenderedComponent",
    "RenderedImage",
    "component_role",
    "image_bytes",
    "kept_images",
    "render_plan",
]

RENDERER_PATH = "/render"
RENDERER_HEALTH_PATH = "/health"
RENDER_PASS_HEADER = "x-kv-render-pass"
PHONE_WIDTH = 390
DESKTOP_WIDTH = 1440
WIDTHS = (PHONE_WIDTH, DESKTOP_WIDTH)
VIEW_HEIGHTS: Mapping[int, int] = MappingProxyType({PHONE_WIDTH: 844, DESKTOP_WIDTH: 900})
FIRST_SCREEN_SCALES: Mapping[int, float] = MappingProxyType({PHONE_WIDTH: 1.0, DESKTOP_WIDTH: 0.5})
CHAPTER_VIEW_HEIGHT = 1600
CHAPTER_SCALE = 0.4
JPEG_QUALITY = 55
CHAPTERS_SHOWN_MAX = 12
IMAGE_BYTES_MAX = 1_000_000
RENDER_SECONDS = 35.0
QUEUE_SECONDS = 5.0
PROBLEMS_MAX = 60
PAGE_LABEL = "page"
PICTURE_HOSTS = ("upload.wikimedia.org",)
CHART_KINDS = frozenset({"chart"})
MAP_KINDS = frozenset({"map_layer", "map_sequence", "timeline_map", "why_here"})
INTERACTIVE_KINDS = frozenset(
    {
        "reaction_player",
        "dip_player",
        "stage_player",
        "experiment_lab",
        "choice_toggle",
        "molecule_3d",
        "model_explainer",
        "process_replay",
    }
)
PICTURE, CHART, MAP, INTERACTIVE, FIGURE = ROLES = ("picture", "chart", "map", "interactive", "figure")
CHECKED, FAILED, UNMADE = DRAWING_STATES = PREVIEW_DRAWINGS
UNREACHABLE, BUSY, TIMEOUT, REFUSED, BROWSER, ELSEWHERE = UNMADE_REASONS = (
    "UNREACHABLE",
    "BUSY",
    "TIMEOUT",
    "REFUSED",
    "BROWSER",
    "ELSEWHERE",
)

Role = Literal[*ROLES]
DrawingState = Literal[*DRAWING_STATES]
UnmadeReason = Literal[*UNMADE_REASONS]


class RenderedComponent(ContractModel):
    label: str = Field(min_length=1, max_length=200)
    role: Role
    placed: bool


class RenderPlan(ContractModel):
    components: list[RenderedComponent] = Field(max_length=400)
    masthead: str | None = None
    chapters: list[str] = Field(default_factory=list, max_length=40)


class RenderRequest(ContractModel):
    preview_url: str = Field(min_length=1, max_length=2048)
    render_pass: str = Field(min_length=1, max_length=200)
    plan: RenderPlan


class DrawnProblem(ContractModel):
    width: int = Field(ge=1)
    label: str
    problem: str


class RenderedImage(ContractModel):
    name: str
    caption: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    data: str


class RenderResult(ContractModel):
    problems: list[DrawnProblem] = Field(max_length=2 * PROBLEMS_MAX)
    images: list[RenderedImage]
    blocked: list[str] = Field(default_factory=list)
    seconds: float = Field(ge=0)


class RenderUnmade(ContractModel):
    reason: UnmadeReason
    message: str


class DrawnImage(ContractModel):
    name: str
    caption: str
    width: int
    height: int
    bytes: int = Field(ge=0)


class DrawingReport(ContractModel):
    state: DrawingState
    widths: list[int]
    problems: list[DrawnProblem]
    images: list[DrawnImage]
    blocked: list[str] = Field(default_factory=list)
    reason: str | None = None


def component_role(kind: str) -> str:
    if kind == PICTURE_KIND:
        return PICTURE
    if kind in MAP_KINDS:
        return MAP
    if kind in CHART_KINDS:
        return CHART
    return INTERACTIVE if kind in INTERACTIVE_KINDS else FIGURE


def render_plan(document: MonographDocument) -> RenderPlan:
    content = document.content
    placed = {entry.ref for entry in content.layout if entry.kind == "component"}
    components = [
        RenderedComponent(label=c.label, role=component_role(c.kind), placed=c.label in placed)
        for c in content.components
    ]
    masthead = next(
        (c.label for c in content.components if c.kind == PICTURE_KIND and c.chapter == OPENING),
        None,
    )
    chapters = dict.fromkeys(entry.chapter for entry in content.layout)
    return RenderPlan(
        components=components,
        masthead=masthead,
        chapters=[key for key in chapters if key != OPENING],
    )


def image_bytes(image: RenderedImage) -> int:
    return len(base64.b64decode(image.data, validate=True))


def kept_images(images: Sequence[RenderedImage], *, most: int = IMAGE_BYTES_MAX) -> list[RenderedImage]:
    kept: list[RenderedImage] = []
    total = 0
    for image in images:
        size = image_bytes(image)
        if total + size > most:
            continue
        kept.append(image)
        total += size
    return kept
