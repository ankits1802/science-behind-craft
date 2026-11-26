from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.errors import InvalidInput
from app.core.rate_limit import IMAGE_UPLOADS
from app.models import ImageContribution, UploadLink, User
from app.research.image_contributions_give import GivenPicture
from app.research.image_intake import IMAGE_BYTES_MAX
from app.research.image_intake_types import ACCEPTED_TYPES
from app.research.upload_links import slot_upload_url
from app.services import upload_links

from .mcp_files import FileArgument, Staged
from .mcp_picture_arguments import UPLOADED, GivePictures, slot_declaration, upload_slot
from .mcp_tool_base import ToolContext, signed_in
from .oauth_hosts import endpoints_or_none
from .proposal_limits import refuse_tool_when_spent

__all__ = ["PICTURE_FILES", "received_pictures"]

FILES_DESCRIPTION = (
    "The photographs themselves, sent without passing through the chat: one for each picture that sets "
    "upload true, in the same order, each at most 10 MB, screened and declared as that picture says"
)
UNMATCHED = (
    "files holds {files} photographs and pictures sets upload true {uploads} times; give one file for each "
    "picture that sets upload true, in the same order"
)
UNDECLARED = (
    "photographs sent as files need the declaration the person confirmed in the chat and their words of "
    "confirmation, as pictures given in the call do"
)
NO_UPLOADS = "Pictures cannot be uploaded to this server right now; give them by their link or in the call."
NOT_ARRIVED = (
    "Picture {position}'s photograph has not arrived or did not pass its screening, so none was given."
)
SEPARATOR = ":"


async def _staged(context: ToolContext, arguments: GivePictures) -> list[Staged]:
    user = signed_in(context)
    uploads = arguments.placed(UPLOADED)
    if len(uploads) != len(context.files):
        raise InvalidInput(UNMATCHED.format(files=len(context.files), uploads=len(uploads)))
    if arguments.declaration is None or arguments.confirmation is None:
        raise InvalidInput(UNDECLARED)
    endpoints = endpoints_or_none()
    if endpoints is None:
        raise InvalidInput(NO_UPLOADS)
    staged: list[Staged] = []
    for (position, picture), file in zip(uploads, context.files, strict=True):
        slot = upload_slot(arguments.craft_slug, picture)
        declaration = slot_declaration(arguments.declaration, picture)
        await refuse_tool_when_spent(IMAGE_UPLOADS, user)
        issued = await upload_links.start_upload(context.session, user, slot, declaration, now=_now())
        if issued.slot_token is None or issued.link_id is None:
            raise InvalidInput(UNDECLARED)
        url = slot_upload_url(endpoints.issuer, issued.slot_token)
        ref = f"{position}{SEPARATOR}{issued.link_id}"
        staged.append(Staged(file_id=file.id, url=url, ref=ref, expires_at=issued.expires_at))
    return staged


async def received_pictures(context: ToolContext, user: User) -> list[GivenPicture]:
    pictures = []
    for ref in context.uploaded.values():
        position, _, link_id = ref.partition(SEPARATOR)
        link = await context.session.get(UploadLink, uuid.UUID(link_id))
        if link is None or link.userId != user.id or link.contributionId is None:
            raise InvalidInput(NOT_ARRIVED.format(position=position))
        row = await context.session.get(ImageContribution, link.contributionId)
        if row is None:
            raise InvalidInput(NOT_ARRIVED.format(position=position))
        pictures.append(GivenPicture(position=int(position), contribution_id=row.id, status=row.status))
    return pictures


def _now() -> datetime:
    return datetime.now(UTC)


PICTURE_FILES = FileArgument(
    name="files",
    accept=ACCEPTED_TYPES,
    max_size=IMAGE_BYTES_MAX,
    stage=_staged,
    many=True,
    description=FILES_DESCRIPTION,
)
