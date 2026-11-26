from __future__ import annotations

import base64
import binascii
import uuid
from datetime import UTC, datetime

from pydantic import Field

from app.core.errors import ExternalFailure, InvalidInput
from app.core.mcp_scopes import CONTRIBUTE_SCOPE
from app.core.rate_limit import COMPONENT_PROPOSALS
from app.models import DatasetUpload, EnvDataset, User
from app.research.dataset_proposals import (
    TABLE_BYTES_MAX,
    TABLE_TYPES,
    DatasetProposal,
    DatasetReply,
    DatasetUploadStart,
    upload_types,
    upload_url,
)
from app.research.map_layer_proposals import LAYER_TYPES
from app.services.candidate_sources import proposal_fetcher
from app.services.dataset_proposals import issue_dataset_slot, proposal_problems

from .mcp_argument_names import SnakeBodyArguments
from .mcp_files import FileArgument, FileInput, Staged
from .mcp_tool_base import OPEN_WRITES, PROPOSING, Tool, ToolContext, contributor
from .oauth_hosts import endpoints_or_none
from .proposal_limits import refuse_tool_when_spent

__all__ = ["DATASET_TOOLS", "PROPOSE_DATASET", "ProposeDataset"]

DESCRIPTION = (
    "Propose an open dataset whose rows a component draws: its record (code, title, publisher, edition, version, "
    "period, native_resolution, crs, licence with licence_url, attribution, redistributable, citation with doi, "
    "landing_url, url of the file, the file's sha256, and sheet when a workbook's table is not its first sheet). The "
    "gates check the licence is open and redistributable, the code is new and the landing page is reachable, then "
    "return a single-use upload slot: PUT the table (UTF-8 CSV, or an .xlsx workbook with its values saved and no "
    "macros; a header row, at most 20000 rows) to upload_url within 30 minutes; it is scanned for malware and its "
    "SHA-256 checked before the table is stored. A chart, fact_table or map_layer then names the dataset's code "
    "as dataset and each value's row and column as its cell, and the gates check every value against its stored "
    "row. A new map layer adds layer and PUTs WGS 84 GeoJSON, held for a reviewer (datasets guide, Map layers over "
    "MCP)."
)
UPLOADS_OFF = "Dataset uploads are not open on this server right now."
CHECKS_UNAVAILABLE = (
    "The checks could not run just now and nothing was stored; call propose_dataset again later."
)
UPLOAD_STEP = (
    "PUT the CSV or .xlsx file to upload_url (curl -T file.csv <upload_url>) before the slot expires."
)
LAYER_UPLOAD_STEP = (
    "PUT the GeoJSON file to upload_url (curl -T layer.geojson <upload_url>) before the slot expires."
)
REFUSED = "The dataset was not taken: {problems}."
FILE_DESCRIPTION = (
    "The dataset's file itself, sent without passing through the chat: its table as UTF-8 CSV or an .xlsx "
    "workbook (the sheet the record names, or the first), or a new map layer's GeoJSON, at most 5 MB, the very "
    "file whose sha256 the record gives"
)
OTHER_FILE = "The file's SHA-256 is not the sha256 the record declares; send the dataset's own file."
NOT_ARRIVED = "The dataset's file has not arrived or did not pass its checks, so nothing was stored."
STORED = "The file arrived and passed its checks: the dataset {code} is stored; cite its rows by its code."
LAYER_STORED = "The file arrived and passed its checks: the layer {code} is stored for a reviewer."


class ProposeDataset(SnakeBodyArguments):
    proposal: DatasetProposal = Field(description="The dataset's record, as the datasets guide lists it")


async def _propose(context: ToolContext, arguments: ProposeDataset) -> DatasetReply:
    user = contributor(context, "propose_dataset", "propose datasets")
    if context.uploaded:
        return await _arrived(context, user)
    proposal = arguments.proposal
    endpoints = await _checked(context, user, proposal)
    if isinstance(endpoints, DatasetReply):
        return endpoints
    issued = await issue_dataset_slot(context.session, user, proposal, now=datetime.now(UTC))
    upload = DatasetUploadStart(
        upload_url=upload_url(endpoints, issued.token),
        upload_types=upload_types(proposal),
        expires_at=issued.expires_at,
    )
    step = UPLOAD_STEP if proposal.layer is None else LAYER_UPLOAD_STEP
    return DatasetReply(code=proposal.code, outcome="UPLOAD", message=step, upload=upload)


async def _checked(context: ToolContext, user: User, proposal: DatasetProposal) -> str | DatasetReply:
    await refuse_tool_when_spent(COMPONENT_PROPOSALS, user)
    endpoints = endpoints_or_none()
    if endpoints is None:
        raise InvalidInput(UPLOADS_OFF)
    try:
        async with proposal_fetcher() as fetcher:
            problems = await proposal_problems(context.session, fetcher, proposal)
    except ExternalFailure:
        raise InvalidInput(CHECKS_UNAVAILABLE) from None
    if problems:
        return DatasetReply(
            code=proposal.code, outcome="REFUSED", message=REFUSED.format(problems="; ".join(problems))
        )
    return endpoints.issuer


async def _staged(context: ToolContext, arguments: ProposeDataset) -> list[Staged]:
    user = contributor(context, "propose_dataset", "propose datasets")
    file, proposal = context.files[0], arguments.proposal
    if not _same_file(file, proposal.sha256):
        raise InvalidInput(OTHER_FILE)
    issuer = await _checked(context, user, proposal)
    if isinstance(issuer, DatasetReply):
        raise InvalidInput(issuer.message)
    issued = await issue_dataset_slot(context.session, user, proposal, now=datetime.now(UTC))
    if issued.upload_id is None:
        raise InvalidInput(UPLOADS_OFF)
    url = upload_url(issuer, issued.token)
    return [Staged(file_id=file.id, url=url, ref=str(issued.upload_id), expires_at=issued.expires_at)]


async def _arrived(context: ToolContext, user: User) -> DatasetReply:
    ref = next(iter(context.uploaded.values()))
    row = await context.session.get(DatasetUpload, uuid.UUID(ref))
    if row is None or row.userId != user.id or row.datasetId is None:
        raise InvalidInput(NOT_ARRIVED)
    dataset = await context.session.get(EnvDataset, row.datasetId)
    if dataset is None:
        raise InvalidInput(NOT_ARRIVED)
    layer = DatasetProposal.model_validate(row.record).layer is not None
    said = (LAYER_STORED if layer else STORED).format(code=dataset.code)
    return DatasetReply(code=dataset.code, outcome="STORED", message=said)


def _same_file(file: FileInput, sha256: str) -> bool:
    if file.digest is None:
        return True
    try:
        given = base64.urlsafe_b64decode(file.digest.value + "=" * (-len(file.digest.value) % 4))
    except binascii.Error, ValueError:
        return False
    return given.hex() == sha256.lower()


PROPOSE_DATASET = Tool(
    name="propose_dataset",
    title="Propose a dataset",
    description=DESCRIPTION,
    arguments=ProposeDataset,
    output=DatasetReply,
    run=_propose,
    scope=CONTRIBUTE_SCOPE,
    annotations=OPEN_WRITES,
    group=PROPOSING,
    files=FileArgument(
        name="file",
        accept=(*TABLE_TYPES, *LAYER_TYPES, ".csv", ".xlsx", ".geojson"),
        max_size=TABLE_BYTES_MAX,
        stage=_staged,
        description=FILE_DESCRIPTION,
    ),
)

DATASET_TOOLS = (PROPOSE_DATASET,)
