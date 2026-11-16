import pytest
from pydantic import ValidationError

from app.schemas.science import CraftProcess, cited_source_ids, process_claims
from app.schemas.voice import VoiceTranscript

from .golden import golden_json


def test_claims_and_spoken_sentences_list_their_sources_by_first_citation() -> None:
    transcript = VoiceTranscript.model_validate(golden_json("voice.transcript.golden.json"))
    sentences = [sentence for turn in transcript.turns for sentence in turn.sentences]
    assert cited_source_ids(sentences) == [source.id for source in transcript.sources]
    process = CraftProcess.model_validate(golden_json("science.process.golden.json"))
    assert cited_source_ids(process_claims(process)) == [source.id for source in process.sources]


def test_a_transcript_listing_a_source_twice_is_refused() -> None:
    body = golden_json("voice.transcript.golden.json")
    body["sources"] = [*body["sources"], body["sources"][0]]
    with pytest.raises(ValidationError, match="every cited source once"):
        VoiceTranscript.model_validate(body)
