from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

from pydantic import ValidationError

from app.core.errors import InvalidInput

from .base import ContractModel

__all__ = [
    "AGENT",
    "APPROVAL",
    "APPROVED_STATUS",
    "AUTO",
    "CONTRIBUTION",
    "LIVE_UNREVIEWED_STATUS",
    "PROPOSAL_ORIGINS",
    "PROPOSAL_OUTCOMES",
    "PUBLISHED",
    "REFUSED",
    "REFUSED_STATUS",
    "RESEARCH",
    "SWITCH_DEFAULTS",
    "SWITCH_MODES",
    "WAITING",
    "WAITING_STATUS",
    "Placement",
    "ProposalOrigin",
    "ProposalOutcome",
    "ReviewSwitch",
    "ReviewSwitchUpdate",
    "ReviewSwitchView",
    "SwitchMode",
    "placement",
    "refused_placement",
    "stored_switch",
]

RESEARCH = "RESEARCH"
CONTRIBUTION = "CONTRIBUTION"
AGENT = "AGENT"
PROPOSAL_ORIGINS = (RESEARCH, CONTRIBUTION, AGENT)
AUTO = "AUTO"
APPROVAL = "APPROVAL"
SWITCH_MODES = (AUTO, APPROVAL)
SWITCH_DEFAULTS: Mapping[str, str] = MappingProxyType(
    {RESEARCH: AUTO, CONTRIBUTION: APPROVAL, AGENT: APPROVAL}
)
PUBLISHED = "PUBLISHED"
WAITING = "WAITING"
REFUSED = "REFUSED"
PROPOSAL_OUTCOMES = (PUBLISHED, WAITING, REFUSED)
APPROVED_STATUS = "APPROVED"
LIVE_UNREVIEWED_STATUS = "IN_REVIEW"
WAITING_STATUS = "DRAFT"
REFUSED_STATUS = "REJECTED"

ProposalOrigin = Literal[*PROPOSAL_ORIGINS]
SwitchMode = Literal[*SWITCH_MODES]
ProposalOutcome = Literal[*PROPOSAL_OUTCOMES]


class ReviewSwitch(ContractModel):
    research: SwitchMode = SWITCH_DEFAULTS[RESEARCH]
    contribution: SwitchMode = SWITCH_DEFAULTS[CONTRIBUTION]
    agent: SwitchMode = SWITCH_DEFAULTS[AGENT]

    def mode(self, origin: str) -> str:
        if origin not in PROPOSAL_ORIGINS:
            raise InvalidInput(f"No review switch is kept for the origin {origin!r}")
        return str(getattr(self, origin.lower()))

    def stored(self) -> dict[str, str]:
        return {origin: self.mode(origin) for origin in PROPOSAL_ORIGINS}


class ReviewSwitchUpdate(ContractModel):
    research: SwitchMode | None = None
    contribution: SwitchMode | None = None
    agent: SwitchMode | None = None

    def applied_to(self, current: ReviewSwitch) -> ReviewSwitch:
        changes = {
            name: value for name, value in self.model_dump(by_alias=False).items() if value is not None
        }
        return current.model_copy(update=changes)


class ReviewSwitchView(ContractModel):
    current: ReviewSwitch
    defaults: ReviewSwitch = ReviewSwitch()


@dataclass(frozen=True)
class Placement:
    outcome: str
    status: str
    approved_at_once: bool
    queued: bool

    @property
    def live(self) -> bool:
        return self.outcome == PUBLISHED


def placement(mode: str, *, proposer_reviews: bool) -> Placement:
    if mode not in SWITCH_MODES:
        raise InvalidInput(f"The review switch has no mode {mode!r}")
    if proposer_reviews:
        return Placement(PUBLISHED, APPROVED_STATUS, approved_at_once=True, queued=False)
    if mode == AUTO:
        return Placement(PUBLISHED, LIVE_UNREVIEWED_STATUS, approved_at_once=False, queued=True)
    return Placement(WAITING, WAITING_STATUS, approved_at_once=False, queued=True)


def refused_placement() -> Placement:
    return Placement(REFUSED, REFUSED_STATUS, approved_at_once=False, queued=False)


def stored_switch(value: Any) -> ReviewSwitch:
    if value is None:
        return ReviewSwitch()
    if not isinstance(value, Mapping) or not set(value) <= set(PROPOSAL_ORIGINS):
        raise InvalidInput(f"The stored review switch {value!r} names origins outside {PROPOSAL_ORIGINS}")
    try:
        return ReviewSwitch.model_validate({origin.lower(): mode for origin, mode in value.items()})
    except ValidationError as error:
        raise InvalidInput(
            f"The stored review switch {value!r} holds a mode outside {SWITCH_MODES}"
        ) from error
