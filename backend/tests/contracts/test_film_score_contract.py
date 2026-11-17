import copy
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.film import SCORE_CUES_MAX, SCORE_LABEL, FilmOffer, FilmScore

from .explainer_golden import DOCUMENT, golden_json
from .golden import reproduces

SCORE = "film.score.golden.json"


def score() -> dict[str, Any]:
    return copy.deepcopy(golden_json(SCORE))


def reading_order() -> list[str]:
    document = golden_json(DOCUMENT)
    return [block["id"] for section in document["sections"] for block in section["blocks"]]


def test_the_score_fixture_is_reproduced_byte_for_byte() -> None:
    assert reproduces(FilmScore, SCORE)


def test_the_score_belongs_to_the_explainer_it_plays_under() -> None:
    body = FilmScore.model_validate(score())
    assert str(body.answer_id) == golden_json(DOCUMENT)["answerId"]
    order = reading_order()
    cued = [cue.block_id for cue in body.cues]
    assert set(cued) <= set(order) and cued == sorted(cued, key=order.index)
    assert body.label.text == SCORE_LABEL == "AI music and sound"
    assert body.label.models == ["music_v2_5", "eleven_text_to_sound_v3"]


def test_every_score_audio_is_a_private_bucket_link() -> None:
    body = FilmScore.model_validate(score())
    links = [body.music.audio_url, *(cue.audio_url for cue in body.cues)]
    assert all(
        link.startswith("https://kalavigyan-media-example.s3.ap-south-1.amazonaws.com/media/score/")
        for link in links
    )
    assert all("KalaVigyan_Explainer_2026-11-18_1030_" in link for link in links)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda s: s | {"music": None, "cues": []}, "music or a cue"),
        (lambda s: s | {"cues": [s["cues"][0], s["cues"][0]]}, "one cue at most"),
        (lambda s: s | {"label": s["label"] | {"models": ["music_v2_5"]}}, "each model"),
        (lambda s: s | {"label": s["label"] | {"text": "Music"}}, "AI music and sound"),
        (lambda s: s | {"music": s["music"] | {"audioUrl": "http://example.org/a.mp3"}}, "https"),
        (lambda s: s | {"music": s["music"] | {"durationSeconds": 301.0}}, "less than or equal"),
        (lambda s: s | {"cues": [s["cues"][0] | {"durationSeconds": 31.0}]}, "less than or equal"),
        (lambda s: s | {"cues": [s["cues"][0] | {"offsetSeconds": -1.0}]}, "greater than or equal"),
        (lambda s: s | {"cues": [s["cues"][0] | {"blockId": "S1 B1"}]}, "pattern"),
        (lambda s: s | {"language": "xx"}, "Input should be"),
    ],
)
def test_a_score_off_the_contract_is_refused(change: Any, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        FilmScore.model_validate(change(score()))


def test_a_film_holds_at_most_twelve_cues_and_the_offer_is_a_flag() -> None:
    body = score()
    cue = body["cues"][0]
    many = [cue | {"blockId": f"s{n}.b1"} for n in range(1, SCORE_CUES_MAX + 2)]
    with pytest.raises(ValidationError, match="at most 12"):
        FilmScore.model_validate(body | {"cues": many})
    assert FilmOffer.model_validate({"score": True}).score is True
    with pytest.raises(ValidationError):
        FilmOffer.model_validate({"score": True, "languages": []})
