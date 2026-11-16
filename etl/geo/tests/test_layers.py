import numpy as np
import pytest
import requests
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from geo_etl.layers import soilgrids, with_retries


def outcomes(*steps):
    queue = list(steps)
    calls: list[int] = []

    def call():
        calls.append(len(calls) + 1)
        step = queue.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    return call, calls


def test_with_retries_returns_once_a_transient_error_clears(sleeps):
    call, calls = outcomes(ValueError("a"), ValueError("b"), 42)
    assert with_retries(call, retry_on=(ValueError,)) == 42
    assert calls == [1, 2, 3]
    assert sleeps == [5.0, 10.0]


def test_with_retries_raises_the_fourth_error(sleeps):
    call, calls = outcomes(*(ValueError(f"attempt {n}") for n in range(1, 6)))
    with pytest.raises(ValueError, match="attempt 4"):
        with_retries(call, retry_on=(ValueError,))
    assert calls == [1, 2, 3, 4]
    assert sleeps == [5.0, 10.0, 15.0]


def test_with_retries_lets_other_errors_through_at_once(sleeps):
    call, calls = outcomes(KeyError("not retried"), 42)
    with pytest.raises(KeyError):
        with_retries(call, retry_on=(ValueError,))
    assert calls == [1]
    assert sleeps == []


def geotiff(rows: int, cols: int, value: int) -> bytes:
    with MemoryFile() as memory:
        transform = from_origin(0.0, rows * soilgrids.CELL, soilgrids.CELL, soilgrids.CELL)
        profile = {"driver": "GTiff", "height": rows, "width": cols, "count": 1, "dtype": "int16"}
        with memory.open(**profile, transform=transform) as dataset:
            dataset.write(np.full((rows, cols), value, dtype="int16"), 1)
        return bytes(memory.getbuffer())


def test_soilgrids_coverage_retries_a_tile_of_the_wrong_shape(monkeypatch, sleeps):
    bodies = [geotiff(2, 2, 1), geotiff(3, 2, 250)]

    def fake_get(url, **kwargs):
        made = requests.Response()
        made.status_code = 200
        made._content = bodies.pop(0)
        return made

    monkeypatch.setattr(soilgrids.requests, "get", fake_get)
    block = soilgrids.coverage("clay", "0-5cm", "mean", (0.0, 0.0, 500.0, 750.0))
    assert block.shape == (3, 2)
    assert (block == 250).all()
    assert sleeps == [5.0]
