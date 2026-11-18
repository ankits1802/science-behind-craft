from app.research.translation import written_in
from app.research.vocabulary import ANSWER_LANGUAGE_SPECS
from app.voice.artisan_guide import (
    AGENT_OPENINGS,
    CLOSINGS,
    GUIDE_QUESTIONS,
    INTERVIEW_TOPICS,
    OPENINGS,
    SCREENED_WORDS,
    agent_opening,
    guide_question,
    next_topic,
    opening,
)
from app.voice.languages import VOICE_LANGUAGES

TABLES = (GUIDE_QUESTIONS, OPENINGS, AGENT_OPENINGS, CLOSINGS, SCREENED_WORDS)


def test_the_guide_asks_the_six_topics_in_the_contract_s_order() -> None:
    assert INTERVIEW_TOPICS == ("PROCESS", "MATERIALS", "TIMING", "TOOLS", "HISTORY", "CHANGE")
    assert guide_question("PROCESS", "en") == (
        "Please walk me through how you make your work, from the raw material to the finished piece."
    )
    assert (
        guide_question("CHANGE", "en") == "What has changed in your craft in the years you have practised it?"
    )


def test_every_table_speaks_every_voice_language() -> None:
    for table in TABLES:
        assert set(table) == set(VOICE_LANGUAGES)
    for language in VOICE_LANGUAGES:
        assert set(GUIDE_QUESTIONS[language]) == set(INTERVIEW_TOPICS), language


def test_every_phrase_is_written_in_its_language_s_script() -> None:
    for language in VOICE_LANGUAGES:
        script = ANSWER_LANGUAGE_SPECS[language].script
        phrases = [
            *GUIDE_QUESTIONS[language].values(),
            OPENINGS[language].replace("{craft}", ""),
            AGENT_OPENINGS[language],
            CLOSINGS[language],
            *SCREENED_WORDS[language],
        ]
        for text in phrases:
            assert written_in(text, script), (language, text)


def test_the_relay_opening_names_the_craft_and_the_agent_s_cannot() -> None:
    for language in VOICE_LANGUAGES:
        assert "{craft}" in OPENINGS[language]
        assert "{craft}" not in AGENT_OPENINGS[language]
    assert "about Ajrakh so a reviewer" in opening("en", "Ajrakh")
    assert agent_opening("en").endswith(guide_question("PROCESS", "en"))


def test_the_next_topic_is_the_first_one_not_asked() -> None:
    assert next_topic([]) == "PROCESS"
    assert next_topic(["PROCESS", "MATERIALS"]) == "TIMING"
    assert next_topic(["TIMING", "PROCESS"]) == "MATERIALS"
    assert next_topic(INTERVIEW_TOPICS) is None
