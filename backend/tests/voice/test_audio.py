import io
import struct
import wave

import pytest

from app.core.errors import InvalidInput, Refused
from app.voice.audio import upload_floor_seconds, wav_seconds


def wav(seconds: float, *, rate: int = 16_000, channels: int = 1, width: int = 2) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(width)
        out.setframerate(rate)
        out.writeframes(b"\x00" * int(seconds * rate) * channels * width)
    return buffer.getvalue()


def test_a_wav_lasts_its_frames_over_its_rate() -> None:
    assert wav_seconds(wav(2.5)) == pytest.approx(2.5)
    assert wav_seconds(wav(1.0, rate=48_000, channels=2)) == pytest.approx(1.0)


def test_a_wav_is_charged_its_length_rounded_up() -> None:
    assert upload_floor_seconds(wav(12.2), "audio/wav") == 13
    assert upload_floor_seconds(wav(60.0, rate=8_000), "audio/wav") == 60


def test_a_wav_over_a_minute_is_refused_whatever_its_size() -> None:
    with pytest.raises(Refused) as refused:
        upload_floor_seconds(wav(61.0, rate=8_000, width=1), "audio/wav")
    assert refused.value.reason == "too_long"


def test_a_wav_that_lies_about_its_data_size_is_measured_by_what_it_holds() -> None:
    honest = wav(3.0)
    swollen = honest[:40] + struct.pack("<I", 0xFFFFFFFF) + honest[44:]
    assert wav_seconds(swollen) == pytest.approx(3.0)


def test_a_compressed_wav_or_a_stray_file_is_refused() -> None:
    compressed = bytearray(wav(1.0))
    compressed[20:22] = struct.pack("<H", 0x55)
    for body in (bytes(compressed), b"OggS" + b"\x00" * 64, b"RIFF\x00\x00\x00\x00WAVE"):
        with pytest.raises(InvalidInput):
            wav_seconds(body)


def test_compressed_audio_is_charged_at_least_its_bytes_over_5000_a_second() -> None:
    assert upload_floor_seconds(b"x", "audio/webm") == 1
    assert upload_floor_seconds(b"x" * 50_001, "audio/ogg") == 11
    assert upload_floor_seconds(b"x" * 300_000, "audio/mp4") == 60


def test_compressed_audio_above_the_minute_ceiling_is_refused() -> None:
    with pytest.raises(Refused):
        upload_floor_seconds(b"x" * 300_001, "audio/webm")
