import uuid

from fastapi.testclient import TestClient

from app.api import media_deps as media_deps_module
from app.core.deps import get_current_user
from app.main import create_app
from app.media.jobs import MediaDeps
from app.models import User
from app.providers.router import RouterError

from .fakes import (
    BUNDLE_KEY,
    NOW,
    STAGE_ID,
    THIN_STAGE_ID,
    USER_ID,
    FakeBudget,
    FakeLinks,
    MemoryMedia,
    claim,
    stage,
    stage_claims,
)


def client(memory: MemoryMedia, *, role: str = "STUDENT", budget: FakeBudget | None = None) -> TestClient:
    app = create_app()
    learner = User(id=USER_ID, name="Meera Rao", email="meera@example.org", role=role)
    deps = MediaDeps(
        store=memory, budget=budget or FakeBudget(), links=FakeLinks(), bundle_key=BUNDLE_KEY, now=NOW
    )
    app.dependency_overrides[media_deps_module.media_deps] = lambda: deps
    app.dependency_overrides[get_current_user] = lambda: learner
    return TestClient(app)


def memory() -> MemoryMedia:
    found = MemoryMedia()
    found.stages[STAGE_ID] = stage()
    found.stages[THIN_STAGE_ID] = stage(THIN_STAGE_ID, ordinal=7)
    found.claims[STAGE_ID] = stage_claims()
    found.claims[THIN_STAGE_ID] = [claim(uuid.UUID(int=3), "One fact.")]
    return found


def body(key: str = "media:route-test-key-0001", **changes: object) -> dict:
    return {"kind": "IMAGE", "stageId": str(STAGE_ID), "idempotencyKey": key, **changes}


def test_options_answer_the_contract_shape() -> None:
    answer = client(memory()).get("/api/media/options", params={"craftSlug": "Kutch-Ajrakh"})
    assert answer.status_code == 200
    assert answer.json() == {
        "craft": {"slug": "Kutch-Ajrakh", "name": "Kutch Ajrakh", "path": "/crafts/Kutch-Ajrakh"},
        "kinds": [{"kind": "IMAGE", "remainingToday": 5}],
        "stages": [{"stageId": str(STAGE_ID), "kinds": ["IMAGE"]}],
    }
    assert client(memory()).get("/api/media/options", params={"craftSlug": "Nothing"}).status_code == 404


def test_a_new_job_is_accepted_and_a_repeat_answers_ok() -> None:
    http = client(memory())
    first = http.post("/api/media/jobs", json=body())
    again = http.post("/api/media/jobs", json=body())
    assert (first.status_code, again.status_code) == (202, 200)
    assert first.json()["id"] == again.json()["id"]
    assert first.json()["status"] == "QUEUED" and first.json()["pollAfterSeconds"] == 3
    read = http.get(f"/api/media/jobs/{first.json()['id']}")
    assert read.status_code == 200 and read.json()["id"] == first.json()["id"]
    assert http.get(f"/api/media/jobs/{uuid.uuid4()}").status_code == 404


def test_refusals_carry_their_status_and_wait_hints() -> None:
    http = client(memory())
    assert http.post("/api/media/jobs", json=body(kind="VIDEO")).status_code == 403
    assert http.post("/api/media/jobs", json=body(stageId=str(THIN_STAGE_ID))).status_code == 409
    assert http.post("/api/media/jobs", json=body(claimIds=[str(uuid.uuid4())])).status_code == 422
    assert http.post("/api/media/jobs", json=body(styleHint="with community elders")).status_code == 422
    for n in range(3):
        assert http.post("/api/media/jobs", json=body(f"media:route-busy-key-{n:04d}")).status_code == 202
    busy = http.post("/api/media/jobs", json=body("media:route-busy-key-0099"))
    assert busy.status_code == 429 and busy.headers["retry-after"] == "30"


def test_a_reached_budget_answers_503_with_the_router_s_sentence() -> None:
    refusal = RouterError("ceiling", "The monthly budget for images and video has been reached.")
    answer = client(memory(), budget=FakeBudget(refuse_hold=refusal)).post("/api/media/jobs", json=body())
    assert answer.status_code == 503
    assert answer.json()["detail"] == "The monthly budget for images and video has been reached."
