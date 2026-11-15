import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.routes import knowledge
from app.main import create_app
from app.services import knowledge_view

NOTICE_SHA256 = "fe8d668470b89bfb16a2737dd6df82a931a8c90a95a7adbd42f3568e8bec6be4"


def test_privacy_notice_version_moves_with_its_text() -> None:
    assert knowledge.notice_sha256() == NOTICE_SHA256, "the notice changed: bump NOTICE_VERSION and this hash"


def test_privacy_notice_is_public_and_fills_the_contact() -> None:
    client = TestClient(create_app())
    response = client.get("/api/privacy/notice")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == knowledge.NOTICE_VERSION
    assert "{contact}" not in body["body"]
    assert body["title"]


def test_protected_knowledge_routes_need_a_session() -> None:
    client = TestClient(create_app())
    assert client.get("/api/crafts/kutch-ajrakh/profile").status_code == 401
    assert client.get("/api/map/crafts").status_code == 401
    assert client.get("/api/answers/config").status_code == 401
    assert client.post("/api/answers/stream", json={"question": "why indigo"}).status_code == 401


def test_sse_frames_one_json_line_per_event() -> None:
    frame = knowledge.sse("sentence", {"text": "a\nb", "n": 1})
    name, data, blank = frame.split("\n", 2)
    assert name == "event: sentence"
    assert json.loads(data.removeprefix("data: ")) == {"text": "a\nb", "n": 1}
    assert blank == "\n"


def test_alias_match_prefers_the_longest_name() -> None:
    ajrakh, kutch, bagh = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    rows = [("ajrakh", ajrakh), ("kutch ajrakh", kutch), ("bagh print", bagh)]
    assert knowledge_view.match_aliases("Why is Kutch Ajrakh dyed twice?", rows) == [kutch]
    assert knowledge_view.match_aliases("How is Ajrakh washed?", rows) == [ajrakh]
    assert knowledge_view.match_aliases("What is block printing?", rows) == []


def test_alias_match_reports_ties_as_ambiguous() -> None:
    one, two = uuid.uuid4(), uuid.uuid4()
    rows = [("dhokra", one), ("dhokra", two)]
    assert sorted(knowledge_view.match_aliases("dhokra casting", rows), key=str) == sorted(
        [one, two], key=str
    )


def test_alias_match_needs_whole_words() -> None:
    craft = uuid.uuid4()
    assert knowledge_view.match_aliases("embroidered cloth", [("embroidery", craft)]) == []


def test_sections_follow_the_reading_order() -> None:
    views = [
        knowledge_view.ClaimView(uuid.uuid4(), "c", "PROVISIONAL", "MECHANISM", None),
        knowledge_view.ClaimView(uuid.uuid4(), "a", "PROVISIONAL", "TRADITION", None),
        knowledge_view.ClaimView(uuid.uuid4(), "b", "VERIFIED", "MATERIAL", None),
    ]
    ordered = [v.text for v in knowledge_view.order_claims(views)]
    assert ordered == ["a", "b", "c"]


def test_follow_ups_skip_what_was_answered() -> None:
    items = knowledge.follow_ups("Ajrakh", ["Materials and tools", "Process"])
    assert len(items) == 3
    assert all("Ajrakh" in item for item in items)
    assert not any("materials" in item for item in items)


@pytest.mark.parametrize("mode", ["HYBRID", "DEEP"])
def test_unlisted_modes_are_refused(mode: str) -> None:
    assert mode not in knowledge.ANSWER_MODES
