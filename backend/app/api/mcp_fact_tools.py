from __future__ import annotations

from pydantic import Field

from app.core.errors import ExternalFailure, InvalidInput, Refused
from app.core.mcp_scopes import CONTRIBUTE_SCOPE
from app.core.rate_limit import FACT_PROPOSALS
from app.core.roles import Capability, can
from app.research.knowledge_writes import FactProposal, ProposalReply
from app.research.review_switch import AGENT

from .mcp_tool_base import WRITES, Arguments, Tool, ToolContext
from .proposal_deps import proposed
from .proposal_limits import refuse_tool_when_spent

__all__ = ["FACT_TOOLS", "PROPOSE_FACT", "ProposeFact"]

PROPOSE_DESCRIPTION = (
    "Propose one fact about a craft or a category in one field, with the verbatim quotes and sources that state "
    "it. Call get_facts for the craft and field first: a fact already held is refused. The gates fetch every "
    "source and re-find every quote, grade the source and read its licence, refuse a fact the subject already "
    "holds or one that adds nothing to its section, and keep a disagreement with a held fact as sources differ. "
    "The reply says whether the fact was published, waits for a reviewer, or was refused, with each gate's "
    "reasons. Name the field or corroboration task you claimed as taskKey: a fact that passes the gates "
    "completes it, and a refused one gives it back."
)
NEEDS_PROPOSER = "propose_fact needs an account of Researcher or above; this account cannot propose facts."
CHECKS_UNAVAILABLE = (
    "The checks could not run just now and nothing was stored; call propose_fact again later."
)


class ProposeFact(Arguments):
    proposal: FactProposal = Field(
        description=(
            "subject {kind craft or category, slug}, field, optional secondary fields, the statement (one "
            "sentence), sources [{url, title, licence, quotes [{text, locator}]}], and the taskKey you "
            "claimed"
        )
    )


async def _propose(context: ToolContext, arguments: ProposeFact) -> ProposalReply:
    user = context.user
    if user is None or not can(user, Capability.PROPOSE_KNOWLEDGE):
        raise InvalidInput(NEEDS_PROPOSER)
    refuse_tool_when_spent(FACT_PROPOSALS, user)
    try:
        return await proposed(context.session, arguments.proposal, user, AGENT)
    except Refused as refused:
        raise InvalidInput(refused.message) from None
    except ExternalFailure:
        raise InvalidInput(CHECKS_UNAVAILABLE) from None


PROPOSE_FACT = Tool(
    name="propose_fact",
    title="Propose a fact",
    description=PROPOSE_DESCRIPTION,
    arguments=ProposeFact,
    output=ProposalReply,
    run=_propose,
    scope=CONTRIBUTE_SCOPE,
    annotations=WRITES,
)

FACT_TOOLS = (PROPOSE_FACT,)
