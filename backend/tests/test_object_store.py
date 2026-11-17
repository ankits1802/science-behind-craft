import io

import boto3
import pytest
from botocore.config import Config
from botocore.response import StreamingBody
from botocore.stub import Stubber

from app.core.errors import ExternalFailure
from app.services.object_store import ObjectStore

BUCKET = "kalavigyan-media-example"
KEY = "media/narration/" + "a" * 64 + "/narration.json"


def stubbed() -> tuple[ObjectStore, Stubber]:
    client = boto3.client(
        "s3",
        region_name="ap-south-1",
        aws_access_key_id="test-only-access-key",
        aws_secret_access_key="test-only-secret-not-real",
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )
    return ObjectStore(bucket=BUCKET, region="ap-south-1", client=client), Stubber(client)


async def test_reading_an_object_returns_its_bytes() -> None:
    store, stub = stubbed()
    body = b'{"schemaVersion":1}'
    stub.add_response(
        "get_object", {"Body": StreamingBody(io.BytesIO(body), len(body))}, {"Bucket": BUCKET, "Key": KEY}
    )
    with stub:
        assert await store.get(KEY) == body


async def test_a_missing_object_reads_as_nothing() -> None:
    store, stub = stubbed()
    stub.add_client_error("get_object", service_error_code="NoSuchKey", http_status_code=404)
    with stub:
        assert await store.get(KEY) is None


async def test_a_refused_read_fails_loudly() -> None:
    store, stub = stubbed()
    stub.add_client_error("get_object", service_error_code="AccessDenied", http_status_code=403)
    with stub, pytest.raises(ExternalFailure) as failure:
        await store.get(KEY)
    assert failure.value.kind == "auth" and "AccessDenied" in str(failure.value)
