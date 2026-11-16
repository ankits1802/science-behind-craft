from app.providers import elevenlabs
from app.voice import agent, languages
from app.voice.languages import VOICE_LANGUAGES, heard_and_spoken, voice_language_options

SCRIBE_V3_DOCS = {
    "English": "eng",
    "Hindi": "hin",
    "Bengali": "ben",
    "Tamil": "tam",
    "Telugu": "tel",
    "Marathi": "mar",
    "Gujarati": "guj",
    "Kannada": "kan",
    "Malayalam": "mal",
    "Odia": "ori",
    "Punjabi": "pan",
    "Assamese": "asm",
    "Urdu": "urd",
}
ELEVEN_V4_TURBO_DOCS = {
    "English": "en",
    "Hindi": "hi",
    "Bengali": "bn",
    "Tamil": "ta",
    "Telugu": "te",
    "Marathi": "mr",
    "Gujarati": "gu",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Odia": "or",
    "Punjabi": "pa",
    "Assamese": "as",
    "Urdu": "ur",
}
ANSWER_ORDER = ("en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "or", "pa", "as", "ur")


def test_the_adapter_sends_scribe_the_codes_its_language_list_gives() -> None:
    by_iso = {ELEVEN_V4_TURBO_DOCS[name]: code for name, code in SCRIBE_V3_DOCS.items()}
    assert dict(elevenlabs.STT_LANGUAGE_CODES) == by_iso
    assert elevenlabs.STT_MODEL == "scribe_v3"


def test_the_speech_model_speaks_every_answer_language_by_its_two_letter_code() -> None:
    assert frozenset(ELEVEN_V4_TURBO_DOCS.values()) == elevenlabs.TTS_LANGUAGES
    assert elevenlabs.TTS_MODEL == "eleven_v4_turbo"


def test_voice_offers_every_answer_language_both_directions_support_in_answer_order() -> None:
    assert VOICE_LANGUAGES == ANSWER_ORDER


def test_a_language_one_direction_lacks_is_not_offered() -> None:
    heard = {"en": "eng", "hi": "hin", "ur": "urd"}
    spoken = {"en", "hi", "ta"}
    assert heard_and_spoken(ANSWER_ORDER, heard=heard, spoken=spoken) == ("en", "hi")
    assert heard_and_spoken(("ur", "en"), heard=heard, spoken={"ur", "en"}) == ("ur", "en")


def test_the_offered_options_carry_what_the_client_draws_them_with() -> None:
    options = voice_language_options()
    assert [option["code"] for option in options] == list(ANSWER_ORDER)
    assert options[1] == {
        "code": "hi",
        "label": "Hindi",
        "autonym": "हिन्दी",
        "script": "Deva",
        "direction": "ltr",
    }
    assert options[-1] == {
        "code": "ur",
        "label": "Urdu",
        "autonym": "اردو",
        "script": "Arab",
        "direction": "rtl",
    }
    assert [option["code"] for option in options if option["direction"] == "rtl"] == ["ur"]


def test_the_agent_lists_every_other_offered_language_on_the_speech_model() -> None:
    presets = agent.language_presets()
    assert sorted(presets) == sorted(ANSWER_ORDER[1:])
    assert all(
        preset == {"overrides": {"tts": {"model_id": "eleven_v4_turbo"}}} for preset in presets.values()
    )
    assert languages.VOICE_LANGUAGES[0] == "en"
