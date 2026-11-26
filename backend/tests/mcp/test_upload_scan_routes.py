import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from app.models import DatasetUpload, User
from app.services import dataset_proposals as proposals, malware_scan
from app.services.malware_scan import ClamdScanner, ScannerDown

from ..upload_scanners import EICAR, EICAR_SIGNATURE
from .test_proposal_limits import DATASET
from .test_upload_link_routes import LINK, SLOT, VIEW, Session, answering, client

TABLE = b"district,artisans\nKachchh,412\n"
SLOT_TOKEN = "kvds_" + "c" * 43
OWNER = User(id=uuid.UUID(int=41), name="Meera Rao", email="meera@example.org", role="RESEARCHER")


def held_slot(monkeypatch: pytest.MonkeyPatch, data: bytes) -> list[bytes]:
    parsed: list[bytes] = []
    row = DatasetUpload(
        id=uuid.UUID(int=5),
        userId=OWNER.id,
        record={**DATASET, "sha256": hashlib.sha256(data).hexdigest()},
        sha256=hashlib.sha256(data).hexdigest(),
        expiresAt=datetime.now(UTC) + timedelta(minutes=20),
    )

    async def slot(session: Any, digest: str) -> DatasetUpload:
        return row

    async def owner(session: Any, upload: DatasetUpload, now: datetime) -> User:
        return OWNER

    def read(data: bytes, proposal: Any) -> Any:
        parsed.append(data)
        raise AssertionError("the table was read before its scan answered")

    monkeypatch.setattr(proposals, "_slot", slot)
    monkeypatch.setattr(proposals, "_live_owner", owner)
    monkeypatch.setattr(proposals, "_parsed", read)
    return parsed


def scanner_down(monkeypatch: pytest.MonkeyPatch, folder: Path) -> None:
    monkeypatch.setattr(malware_scan, "upload_scanner", lambda: ClamdScanner(str(folder / "absent.ctl")))


def test_a_table_sent_while_the_scanner_is_down_is_refused_unread_and_nothing_is_kept(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parsed = held_slot(monkeypatch, TABLE)
    scanner_down(monkeypatch, tmp_path)
    session = Session()
    response = client(None, session).put(f"/api/dataset-uploads/{SLOT_TOKEN}", content=TABLE)
    assert response.status_code == 503 and "not answering" in response.json()["detail"]
    assert parsed == [] and session.ended == ["rollback"]


def test_a_table_carrying_the_eicar_test_file_is_refused_by_its_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = TABLE + EICAR.encode("ascii")
    parsed = held_slot(monkeypatch, data)
    session = Session()
    response = client(None, session).put(f"/api/dataset-uploads/{SLOT_TOKEN}", content=data)
    assert response.status_code == 422
    assert (
        response.json()["detail"] == f"The file was refused: the malware scan found {EICAR_SIGNATURE} in it."
    )
    assert parsed == [] and session.ended == ["rollback"]


@pytest.mark.parametrize(
    ("service", "route", "role"),
    [
        ("app.services.upload_links.fill_slot", f"/api/upload-links/slots/{SLOT}", None),
        (
            "app.services.supplied_sources.fill_supplied_slot",
            "/api/knowledge/supplied-sources/slots/kvss_t",
            None,
        ),
        (
            "app.services.image_contributions.receive_file",
            f"/api/contributions/images/{uuid.UUID(int=7)}/file",
            "RESEARCHER",
        ),
    ],
)
def test_every_upload_route_answers_503_when_the_scanner_is_down(
    monkeypatch: pytest.MonkeyPatch, service: str, route: str, role: str | None
) -> None:
    async def down(*args: Any, **kwargs: Any) -> Any:
        raise ScannerDown(malware_scan.DOWN)

    monkeypatch.setattr(service, down)
    monkeypatch.setattr("app.api.routes.upload_links.media_bucket", lambda: "bucket")
    monkeypatch.setattr("app.api.routes.image_contributions.media_bucket", lambda: "bucket")
    session = Session()
    response = client(role, session).put(route, content=b"png-bytes")
    assert response.status_code == 503 and response.json()["detail"] == malware_scan.DOWN
    assert session.ended == ["rollback"]


def test_with_the_scanner_down_every_other_path_keeps_working(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scanner_down(monkeypatch, tmp_path)
    answering(monkeypatch, "link_view", VIEW)
    signed_in = client("RESEARCHER", Session())
    assert signed_in.get("/health").status_code == 200
    assert signed_in.get(f"/api/upload-links/{LINK}").status_code == 200
