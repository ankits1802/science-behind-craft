from __future__ import annotations

import re

__all__ = [
    "IDENTITY_CAPTION",
    "NEVER_STAGE_FIELDS",
    "refuse_identity_caption",
    "refuse_never_image_field",
]

NEVER_STAGE_FIELDS = frozenset(
    {
        ("WORKSHOP_PLAN_PARTICIPANTS_OPENING", "workshopPlan", "designerSignature"),
        ("WORKSHOP_PLAN_PARTICIPANTS_OPENING", "workshopPlan", "designerCv"),
        ("INSPECTION_CLOSING", "certificate", "signatureImage"),
        ("INSPECTION_CLOSING", "certificate", "certificateFile"),
    }
)
IDENTITY_CAPTION = re.compile(
    r"aadha+r|pehchan|identity[\s_-]*(?:cards?|documents?|proofs?)|(?<![a-z])id[\s_-]*(?:cards?|proofs?)(?![a-z])"
    r"|voter|(?<![a-z])pan[\s_-]*cards?(?![a-z])|passport|licen[cs]e|signature|consent"
    r"|finger ?print|thumb ?(?:print|impression)|passbook|cheque|bank ?(?:account|details|statement)"
    r"|\bifsc\b|\bupi\b",
    re.IGNORECASE,
)


def refuse_never_image_field(stage: str, entity: str, field: str) -> None:
    if (stage, entity, field) in NEVER_STAGE_FIELDS:
        raise ValueError(
            f"stage media {stage}.{entity}.{field} is a signature, CV or certificate, never sent"
        )


def refuse_identity_caption(item_id: str, caption: str | None) -> None:
    if caption and IDENTITY_CAPTION.search(caption):
        raise ValueError(
            f"image {item_id} is captioned as an identity document, signature, consent or bank detail"
        )
