import pytest

from app.core.errors import InvalidInput
from app.media.mp4 import boxes, video_facts, without_audio

from .mp4_builder import AUDIO_SAMPLE, FTYP, VIDEO_SAMPLE, box, movie


def stco_offsets(data: bytes) -> list[int]:
    found = []
    at = data.find(b"stco")
    while at != -1:
        count = int.from_bytes(data[at + 8 : at + 12])
        found += [int.from_bytes(data[at + 12 + 4 * i : at + 16 + 4 * i]) for i in range(count)]
        at = data.find(b"stco", at + 4)
    return found


def test_the_video_track_gives_size_and_duration() -> None:
    facts = video_facts(movie().data)
    assert (facts.width, facts.height, facts.duration_seconds, facts.has_audio) == (1280, 720, 8.0, True)


def test_stripping_audio_before_the_media_data_moves_every_chunk_offset_back() -> None:
    source = movie(moov_first=True)
    silent = without_audio(source.data)
    assert len(silent) == len(source.data) - source.audio_trak_size
    moved = source.video_offset - source.audio_trak_size
    assert stco_offsets(silent) == [moved]
    assert silent[moved : moved + 4] == VIDEO_SAMPLE
    assert not video_facts(silent).has_audio
    assert b"soun" not in silent


def test_stripping_audio_after_the_media_data_leaves_offsets_alone() -> None:
    source = movie(moov_first=False)
    silent = without_audio(source.data)
    assert stco_offsets(silent) == [source.video_offset]
    assert silent[source.video_offset : source.video_offset + 8] == VIDEO_SAMPLE + AUDIO_SAMPLE
    assert len(silent) == len(source.data) - source.audio_trak_size


def test_a_silent_movie_is_returned_unchanged() -> None:
    source = movie(audio=False)
    assert without_audio(source.data) == source.data


def test_fragmented_and_broken_files_are_refused() -> None:
    with pytest.raises(InvalidInput, match="fragmented"):
        video_facts(movie().data + box(b"moof", b""))
    with pytest.raises(InvalidInput, match="overruns"):
        boxes(FTYP + (500).to_bytes(4) + b"moov", 0, len(FTYP) + 8)
    with pytest.raises(InvalidInput, match="one moov"):
        video_facts(FTYP)
