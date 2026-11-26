from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.core.mcp_scopes import CONTRIBUTE_SCOPE
from app.core.rate_limit import SITE_GAPS
from app.research.page_proposals import PageSubject
from app.research.site_gaps import EVIDENCE_MAX, GAP_KINDS, GAP_MEANINGS, FiledGap, SiteGap
from app.services.site_gaps import record_gap

from .mcp_tool_base import WORK, WRITES, Arguments, Tool, ToolContext, contributor
from .proposal_limits import refuse_tool_when_spent

__all__ = ["DESCRIPTION", "GAP_TOOLS", "NEXT_STEP", "ReportSiteGap"]

DESCRIPTION = (
    "Files what KalaVigyan could not do for a page being built: a kind no component draws, a tool that is "
    "missing, a bound that stops the page, or a part the site draws wrongly. It takes the page, the gap's kind, "
    "what the page needed, what was tried and the evidence: a refused call's message, the Kutch Ajrakh label "
    "it would match, a preview's finding. It reaches the KalaVigyan team and its Admins; nothing on the page "
    "changes."
)
FILED = "Filed for the KalaVigyan team, who read it with the Admins: {meaning}."
NEXT_STEP = (
    "Tell the person once that this is KalaVigyan's gap, not theirs to fix, and go on building the rest of "
    "the page."
)
KINDS_SAID = "; ".join(f"{kind}: {meaning}" for kind, meaning in GAP_MEANINGS.items())


class ReportSiteGap(Arguments):
    subject: PageSubject | None = Field(default=None, description="The page {kind, slug} being built")
    kind: Literal[*GAP_KINDS] = Field(description=KINDS_SAID)
    wanted: str = Field(min_length=10, max_length=600, description="What the page needed and could not have")
    tried: str | None = Field(default=None, min_length=1, max_length=600, description="What was tried")
    evidence: list[str] = Field(
        min_length=1, max_length=EVIDENCE_MAX, description="Each piece of evidence, quoted as it was met"
    )


async def _report_site_gap(context: ToolContext, arguments: ReportSiteGap) -> FiledGap:
    user = contributor(context, "report_site_gap", "report a gap")
    await refuse_tool_when_spent(SITE_GAPS, user)
    gap = SiteGap.model_validate(arguments.model_dump())
    client = context.caller.client_name if context.caller is not None else None
    await record_gap(context.session, user, gap, client=client)
    return FiledGap(
        filed=True, kind=gap.kind, message=FILED.format(meaning=GAP_MEANINGS[gap.kind]), next_step=NEXT_STEP
    )


GAP_TOOLS: tuple[Tool, ...] = (
    Tool(
        "report_site_gap",
        "Report what the site could not do",
        DESCRIPTION,
        ReportSiteGap,
        FiledGap,
        _report_site_gap,
        CONTRIBUTE_SCOPE,
        WRITES,
        group=WORK,
    ),
)
