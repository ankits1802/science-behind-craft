import json
from datetime import UTC, datetime

import pytest

from app.core.errors import InvalidInput
from app.services.molecule_conformers import CONFORMER_LEAF, ConformerCache
from app.services.naming import molecule_key
from app.sources.reference.pubchem import PubChemAdapter

from ..sources.recorded import Recorder, Reply, fixed_clock, recorded, source_http
from ..voice.listen_fakes import MemoryObjects

CHECKED_AT = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
PUG = "pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid"
ALIZARIN_KEY = "media/molecules/6293/conformer.json"
ALIZARIN_SDF = recorded("pubchem_conformer.sdf").decode("ascii").strip()


def pubchem(routes: dict[str, Reply]) -> tuple[PubChemAdapter, Recorder]:
    recorder = Recorder(routes)
    return PubChemAdapter(source_http(recorder, "pubchem"), clock=fixed_clock()), recorder


def cache(objects: MemoryObjects, routes: dict[str, Reply]) -> tuple[ConformerCache, Recorder]:
    adapter, recorder = pubchem(routes)
    return ConformerCache(objects=objects, source=adapter, clock=lambda: CHECKED_AT), recorder


def test_a_conformer_is_filed_under_its_cid() -> None:
    assert molecule_key(6293, CONFORMER_LEAF) == ALIZARIN_KEY
    with pytest.raises(InvalidInput):
        molecule_key(0, CONFORMER_LEAF)
    with pytest.raises(InvalidInput):
        molecule_key(6293, "nested/conformer.json")


async def test_a_miss_fetches_through_the_pubchem_adapter_and_keeps_the_record() -> None:
    objects = MemoryObjects()
    first, recorder = cache(objects, {f"{PUG}/6293/record/SDF": Reply("pubchem_conformer.sdf")})
    assert await first.conformer(6293) == ALIZARIN_SDF
    assert len(recorder.requests) == 1
    body, content_type = objects.stored[ALIZARIN_KEY]
    assert content_type == "application/json"
    assert json.loads(body) == {
        "schemaVersion": 1,
        "pubchemCid": 6293,
        "sdf": ALIZARIN_SDF,
        "checkedAt": "2026-11-17T10:00:00Z",
    }


async def test_a_cache_hit_makes_no_second_call() -> None:
    objects = MemoryObjects()
    first, _ = cache(objects, {f"{PUG}/6293/record/SDF": Reply("pubchem_conformer.sdf")})
    await first.conformer(6293)
    second, recorder = cache(objects, {})
    assert await second.conformer(6293) == ALIZARIN_SDF
    assert recorder.requests == []


async def test_a_missing_conformer_is_kept_as_missing_and_not_asked_again() -> None:
    objects = MemoryObjects()
    first, _ = cache(objects, {f"{PUG}/24856/record/SDF": Reply("pubchem_conformer_missing.txt", status=404)})
    assert await first.conformer(24856) is None
    assert json.loads(objects.stored["media/molecules/24856/conformer.json"][0])["sdf"] is None
    second, recorder = cache(objects, {})
    assert await second.conformer(24856) is None
    assert recorder.requests == []


@pytest.mark.parametrize(
    "stored",
    [
        b"not json",
        json.dumps(
            {"schemaVersion": 1, "pubchemCid": 6294, "sdf": None, "checkedAt": "2026-11-17T10:00:00Z"}
        ).encode(),
    ],
    ids=["off its shape", "another compound"],
)
async def test_a_stored_record_that_is_not_this_compound_s_is_fetched_again(stored: bytes) -> None:
    objects = MemoryObjects(stored={ALIZARIN_KEY: (stored, "application/json")})
    again, recorder = cache(objects, {f"{PUG}/6293/record/SDF": Reply("pubchem_conformer.sdf")})
    assert await again.conformer(6293) == ALIZARIN_SDF
    assert len(recorder.requests) == 1
    assert json.loads(objects.stored[ALIZARIN_KEY][0])["pubchemCid"] == 6293
