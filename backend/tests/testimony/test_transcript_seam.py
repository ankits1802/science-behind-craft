import uuid

from cryptography.fernet import Fernet

from app.schemas.artisan import ArtisanTranscript, TranscriptTurn
from app.services import testimony_views
from app.voice.artisan_transcript import open_transcript, sealed_merge
from app.voice.privacy import TranscriptCipher

ASKED = "How long does each step take?"
HEARD = "We keep the indigo vat warm for three days before we dip."


def sealed_conversation(cipher: TranscriptCipher, answer_id: uuid.UUID) -> tuple[str, uuid.UUID]:
    question = TranscriptTurn(
        id=uuid.uuid4(),
        ordinal=0,
        speaker="KALAVIGYAN",
        text=ASKED,
        topic="TIMING",
        answer_id=answer_id,
        start_ms=0,
        end_ms=4_000,
    )
    reply = TranscriptTurn(
        id=uuid.uuid4(), ordinal=1, speaker="ARTISAN", text=HEARD, start_ms=4_500, end_ms=9_000
    )
    return sealed_merge(cipher, question, reply)(None), reply.id


def test_the_review_view_reads_the_transcript_the_conversation_writes() -> None:
    cipher = TranscriptCipher(Fernet.generate_key().decode("ascii"))
    answer_id = uuid.uuid4()
    sealed, quoted = sealed_conversation(cipher, answer_id)
    turns = testimony_views.turns_by_id(cipher.open(sealed))
    turn = turns[str(quoted)]
    assert (turn["text"], turn["speaker"], turn["startMs"], turn["endMs"]) == (HEARD, "ARTISAN", 4_500, 9_000)
    before = testimony_views._turn_before(turns, turn)
    assert before == {"text": ASKED, "english": None, "answerId": str(answer_id)}
    assert isinstance(open_transcript(cipher, sealed), ArtisanTranscript)
