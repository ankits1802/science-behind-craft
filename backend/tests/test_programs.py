import sys

import pytest

from app.core.errors import NotConfigured
from app.core.programs import run_program

ECHO = "import sys; data = sys.stdin.buffer.read(); sys.stdout.buffer.write(data[::-1]); sys.exit(3)"
SLOW = "import time; time.sleep(5)"


async def test_a_program_reads_its_input_and_answers_its_code_and_output() -> None:
    assert await run_program((sys.executable, "-c", ECHO), b"abc", seconds=10) == (3, b"cba")


async def test_a_program_not_installed_is_named_and_one_too_slow_is_stopped() -> None:
    with pytest.raises(NotConfigured, match="kv-no-such-program"):
        await run_program(("kv-no-such-program",), b"", seconds=1)
    with pytest.raises(TimeoutError):
        await run_program((sys.executable, "-c", SLOW), b"", seconds=0.5)
