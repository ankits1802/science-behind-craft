import json
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.curation.dossier import Dossier, parse_dossier
from app.curation.dossier_text import dossier_text
from app.curation.reviewed_sections import ReviewedSection
from app.services.dossier_diff import dossier_changes

from .import_support import checked

SLUG = "Bagru-Hand-Block-Print"
REVIEWER = uuid.UUID("5ec7f000-0000-4000-8000-000000000001")
CLAIM = uuid.UUID("5ec7f000-0000-4000-8000-0000000000c1")
REVIEWED_AT = datetime(2026, 11, 28, 15, 0, tzinfo=UTC)


def _section(field: str, text: str = "Alum fixes the red on the cotton.") -> ReviewedSection:
    return ReviewedSection.model_validate(
        {
            "field": field,
            "version": 3,
            "sentences": [{"text": text, "claimIds": [str(CLAIM)]}],
            "reviewedBy": str(REVIEWER),
            "reviewedAt": REVIEWED_AT.isoformat(),
        }
    )


def _git() -> Dossier:
    dossier = checked(SLUG).dossier
    assert dossier is not None
    return dossier


def test_a_dossier_without_reviewed_sections_writes_no_sections_part() -> None:
    git = _git()
    assert git.sections == []
    assert "sections" not in json.loads(dossier_text(git))


def test_a_reviewed_section_is_written_and_read_back_unchanged() -> None:
    carried = _git().model_copy(update={"sections": [_section("CHEMISTRY")]})
    text = dossier_text(carried)
    written = json.loads(text)["sections"]
    assert written == [
        {
            "field": "CHEMISTRY",
            "version": 3,
            "sentences": [{"text": "Alum fixes the red on the cotton.", "claimIds": [str(CLAIM)]}],
            "reviewedBy": str(REVIEWER),
            "reviewedAt": "2026-11-28T15:00:00Z",
        }
    ]
    assert parse_dossier(text).sections == carried.sections


def test_a_dossier_carries_one_reviewed_section_a_field() -> None:
    body = json.loads(dossier_text(_git()))
    body["sections"] = [
        json.loads(_section("CHEMISTRY").model_dump_json(by_alias=True)),
        json.loads(
            _section("CHEMISTRY", "Another sentence of the same field.").model_dump_json(by_alias=True)
        ),
    ]
    with pytest.raises(ValidationError, match="one reviewed section a field; CHEMISTRY has more"):
        Dossier.model_validate(body)
    body["sections"] = body["sections"][:1]
    assert [section.field for section in Dossier.model_validate(body).sections] == ["CHEMISTRY"]


def test_the_diff_names_a_reviewed_section_added_or_changed_by_its_field() -> None:
    git = _git()
    stored = git.model_copy(update={"sections": [_section("CHEMISTRY")]})
    assert "sections: added CHEMISTRY" in dossier_changes(stored, git)
    edited = git.model_copy(update={"sections": [_section("CHEMISTRY", "A sentence written again.")]})
    assert "sections: changed CHEMISTRY (sentences)" in dossier_changes(edited, stored)
    assert not [line for line in dossier_changes(stored, stored) if line.startswith("sections")]
