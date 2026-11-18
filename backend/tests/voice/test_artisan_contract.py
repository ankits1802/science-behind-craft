import json
import uuid
from datetime import UTC, datetime

import pytest

from app.research.testimony import RECORDING_NOTICE_VERSION
from app.schemas.artisan import (
    ConversationAvailability,
    RelayConversationStarted,
    artisan_speech_path,
    parse_artisan_event,
)
from app.services.naming import artisan_audio_file_name, artisan_audio_key
from app.voice.artisan_availability import HIDDEN_CONVERSATION
from app.voice.artisan_guide import guide_question

from ..contracts.golden import golden_json, golden_text

TURN_ORDER = ["status", "heard", "status", "status", "source", "reply", "done"]


def frames() -> list[tuple[str, object]]:
    found = []
    for block in golden_text("conversation.turn.golden.sse").split("\n\n")[:-1]:
        name, data = block.split("\n")
        found.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return found


def test_the_availability_golden_is_a_configured_offer_of_the_artisan_s_crafts() -> None:
    offer = ConversationAvailability.model_validate(golden_json("conversation.availability.golden.json"))
    assert offer.configured and offer.notice_version == RECORDING_NOTICE_VERSION
    assert [craft.slug for craft in offer.crafts] == ["kutch-ajrakh", "kutch-bandhani"]
    assert {language.direction for language in offer.languages} == {"ltr", "rtl"}


def test_the_hidden_offer_names_nothing() -> None:
    assert ConversationAvailability.model_validate(HIDDEN_CONVERSATION).crafts == []
    with pytest.raises(ValueError):
        ConversationAvailability.model_validate(
            HIDDEN_CONVERSATION | {"crafts": [{"slug": "a", "name": "A", "path": "/crafts/a"}]}
        )


def test_the_relay_start_golden_opens_in_the_artisan_s_language_with_the_first_guide_question() -> None:
    started = RelayConversationStarted.model_validate(golden_json("conversation.started-relay.golden.json"))
    assert started.language == "hi" and started.max_turns == 40
    assert started.opening.text.endswith(guide_question("PROCESS", "hi"))
    assert started.opening.speech_path == artisan_speech_path(
        started.conversation_id, started.opening.turn_id
    )


def test_the_turn_golden_is_one_heard_turn_answered_then_asked() -> None:
    parsed = [(name, parse_artisan_event(name, data)) for name, data in frames()]
    assert [name for name, _ in parsed] == TURN_ORDER
    heard, reply, done = parsed[1][1], parsed[5][1], parsed[6][1]
    assert done.turn_id == heard.turn_id != reply.turn_id
    assert reply.text.endswith(reply.question) and reply.sentences[0].text in reply.text
    assert parsed[4][1].id == reply.sentences[0].citations[0].source_id
    started = golden_json("conversation.started-relay.golden.json")
    assert str(reply.speech_path) == artisan_speech_path(uuid.UUID(started["conversationId"]), reply.turn_id)


def test_a_reply_that_does_not_end_with_its_question_breaks_the_contract() -> None:
    name, data = frames()[5]
    with pytest.raises(ValueError):
        parse_artisan_event(name, {**data, "text": "Something else."})


@pytest.mark.parametrize(
    "row", golden_json("naming-golden.json")["artisanAudioFiles"], ids=lambda row: row["fileName"]
)
def test_artisan_recordings_are_named_by_the_one_convention(row: dict[str, str]) -> None:
    recorded = datetime.fromisoformat(row["recordedAt"]).astimezone(UTC)
    leaf = artisan_audio_file_name(
        recorded_at=recorded,
        district=row["district"],
        craft=row["craft"],
        ordinal=int(row["ordinal"]),
        mime_type=row["mimeType"],
    )
    assert leaf == row["fileName"]
    key = artisan_audio_key(uuid.UUID(row["ownerId"]), leaf, token=uuid.UUID(row["token"]))
    assert key == row["key"]
