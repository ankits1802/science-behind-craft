import uuid
from dataclasses import replace
from datetime import timedelta

import pytest

from app.core.errors import NotConfigured, Refused
from app.media.bundle import bundle_key, opened_bundle, sealed_bundle
from app.media.records import JobRecord

from .fakes import ALUM_CLAIM, BUNDLE_KEY, NOW, PA_CLAIM, STAGE_ID, USER_ID


def job() -> JobRecord:
    return JobRecord(
        id=uuid.UUID("9af1da3c-f6c8-547b-b0e8-ca47cd798604"),
        kind="IMAGE",
        status="QUEUED",
        requested_by=USER_ID,
        stage_id=STAGE_ID,
        claim_ids=(PA_CLAIM, ALUM_CLAIM),
        style_hint=None,
        prompt="Draw one stage.",
        prompt_hash="a" * 64,
        model="gemini-3.1-flash-image",
        alt_text="Alt.",
        attempts=0,
        asset_id=None,
        hold_id=None,
        bundle=None,
        error=None,
        created_at=NOW,
        updated_at=NOW,
    )


def sealed() -> dict:
    return sealed_bundle(BUNDLE_KEY, job(), role="STUDENT", now=NOW)


def test_a_sealed_bundle_opens_for_its_own_job_and_names_the_role() -> None:
    bundle = sealed()
    assert set(bundle) == {"tool", "args", "requester", "target", "expiresAt", "mac"}
    assert opened_bundle(BUNDLE_KEY, bundle, job(), now=NOW + timedelta(hours=1)) == "STUDENT"


@pytest.mark.parametrize(
    "tampered",
    [
        {"claim_ids": (PA_CLAIM,)},
        {"prompt": "Draw a temple."},
        {"model": "gemini-nano-banana-2.1"},
        {"style_hint": "soft light"},
        {"stage_id": uuid.uuid4()},
        {"requested_by": uuid.uuid4()},
        {"kind": "VIDEO"},
    ],
)
def test_a_job_changed_after_sealing_is_refused(tampered: dict) -> None:
    with pytest.raises(Refused) as refused:
        opened_bundle(BUNDLE_KEY, sealed(), replace(job(), **tampered), now=NOW)
    assert refused.value.reason == "bundle_mismatch"


def test_a_bundle_edited_in_place_fails_its_hmac() -> None:
    bundle = sealed()
    bundle["requester"] = {**bundle["requester"], "role": "MASTER_ADMIN"}
    with pytest.raises(Refused) as refused:
        opened_bundle(BUNDLE_KEY, bundle, job(), now=NOW)
    assert refused.value.reason == "bundle_forged"


def test_a_bundle_sealed_under_another_key_is_forged() -> None:
    bundle = sealed_bundle(b"another-test-only-key-with-32-characters", job(), role="STUDENT", now=NOW)
    with pytest.raises(Refused) as refused:
        opened_bundle(BUNDLE_KEY, bundle, job(), now=NOW)
    assert refused.value.reason == "bundle_forged"


def test_an_expired_or_missing_bundle_is_refused() -> None:
    with pytest.raises(Refused) as expired:
        opened_bundle(BUNDLE_KEY, sealed(), job(), now=NOW + timedelta(hours=24))
    assert expired.value.reason == "bundle_expired"
    with pytest.raises(Refused) as missing:
        opened_bundle(BUNDLE_KEY, None, job(), now=NOW)
    assert missing.value.reason == "bundle_missing"


def test_the_bundle_key_must_be_set_and_long_enough() -> None:
    with pytest.raises(NotConfigured):
        bundle_key(None)
    with pytest.raises(NotConfigured):
        bundle_key("short")
    assert bundle_key("k" * 32) == b"k" * 32
