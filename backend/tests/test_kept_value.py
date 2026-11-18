import asyncio

import pytest

from app.core.kept_value import KeptValue


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Builds:
    def __init__(self) -> None:
        self.count = 0

    async def __call__(self) -> str:
        self.count += 1
        await asyncio.sleep(0)
        return f"build {self.count}"


def test_a_kept_value_is_built_once_within_its_lifetime_and_again_after() -> None:
    clock, builds = Clock(), Builds()
    kept = KeptValue[str](lifetime_seconds=300, clock=clock)

    async def run() -> list[str]:
        first = await kept.value(builds)
        clock.now += 299.9
        second = await kept.value(builds)
        clock.now += 0.1
        third = await kept.value(builds)
        return [first, second, third]

    assert asyncio.run(run()) == ["build 1", "build 1", "build 2"]
    assert builds.count == 2


def test_callers_arriving_together_share_one_build() -> None:
    builds = Builds()
    kept = KeptValue[str](lifetime_seconds=60, clock=Clock())

    async def run() -> list[str]:
        return list(await asyncio.gather(*(kept.value(builds) for _ in range(5))))

    assert asyncio.run(run()) == ["build 1"] * 5
    assert builds.count == 1


def test_a_failed_build_keeps_nothing() -> None:
    kept = KeptValue[str](lifetime_seconds=60, clock=Clock())
    builds = Builds()

    async def broken() -> str:
        raise RuntimeError("database away")

    async def run() -> str:
        with pytest.raises(RuntimeError):
            await kept.value(broken)
        return await kept.value(builds)

    assert asyncio.run(run()) == "build 1"


@pytest.mark.parametrize("lifetime", [0, -5])
def test_a_kept_value_needs_a_positive_lifetime(lifetime: float) -> None:
    with pytest.raises(ValueError, match="positive number of seconds"):
        KeptValue[str](lifetime_seconds=lifetime)
