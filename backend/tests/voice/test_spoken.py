from typing import Any

from app.research.translation import written_in
from app.research.vocabulary import ANSWER_LANGUAGE_SPECS
from app.schemas.voice import MAX_SPOKEN_WORDS
from app.voice.languages import VOICE_LANGUAGES
from app.voice.phrases import (
    END_CALL_REPLIES,
    FILLERS,
    NO_CRAFT_REPLIES,
    NO_EVIDENCE_REPLIES,
    SOURCE_WORDS,
    UNSAID_REPLIES,
)
from app.voice.spoken import spoken_label, spoken_reply, word_count

from .fakes import CITATION, SOURCE

PHRASE_TABLES = (FILLERS, NO_EVIDENCE_REPLIES, NO_CRAFT_REPLIES, UNSAID_REPLIES, *END_CALL_REPLIES.values())


def sentence(text: str, source_id: str = SOURCE["id"]) -> dict[str, Any]:
    return {
        "id": "s1.1",
        "text": text,
        "level": "PROVISIONAL",
        "citations": [{**CITATION, "sourceId": source_id}],
    }


def test_a_gi_journal_is_spoken_by_its_issue() -> None:
    assert spoken_label(SOURCE) == "GI Journal 188"


def test_a_paper_is_spoken_by_its_first_author_and_year() -> None:
    paper = {
        "kind": "PAPER",
        "title": "Alizarin lakes on cotton",
        "authors": ["Meera Shah", "B. Rao"],
        "year": 2019,
    }
    assert spoken_label(paper) == "Shah 2019"


def test_other_sources_are_spoken_by_the_head_of_their_title() -> None:
    page = {
        "kind": "ENCYCLOPEDIA",
        "title": "Ajrakh (block printing) - Wikipedia",
        "authors": [],
        "year": None,
    }
    assert spoken_label(page) == "Ajrakh"
    long = {"kind": "WEB_PAGE", "title": "One two three four five six seven", "authors": [], "year": None}
    assert spoken_label(long) == "One two three four five"


def test_the_reply_says_each_sentence_then_its_sources() -> None:
    reply = spoken_reply([sentence("Alum fastens the colours.")], {SOURCE["id"]: SOURCE}, language="en")
    assert reply.parts == ("Alum fastens the colours.", " Source: GI Journal 188.")
    assert reply.text == "Alum fastens the colours. Source: GI Journal 188."


def test_two_sources_are_listed_once_each() -> None:
    other = {**SOURCE, "id": "other", "kind": "PAPER", "authors": ["Meera Shah"], "year": 2019}
    sources = {SOURCE["id"]: SOURCE, "other": other}
    reply = spoken_reply(
        [sentence("First."), sentence("Second.", "other"), sentence("Third.")], sources, language="en"
    )
    assert reply.text == "First. Second. Third. Sources: GI Journal 188; Shah 2019."


def test_a_sentence_that_would_pass_sixty_words_is_left_out() -> None:
    forty = " ".join(["word"] * 40) + "."
    reply = spoken_reply(
        [sentence(forty), sentence(forty), sentence("Short one.")], {SOURCE["id"]: SOURCE}, language="en"
    )
    assert [s["text"] for s in reply.sentences] == [forty, "Short one."]
    assert word_count(reply.text) == 40 + 2 + 4
    assert word_count(reply.text) <= MAX_SPOKEN_WORDS


def test_every_spoken_phrase_exists_in_every_voice_language() -> None:
    for table in (*PHRASE_TABLES, SOURCE_WORDS):
        assert set(table) == set(VOICE_LANGUAGES)
    assert all(filler.endswith("... ") for filler in FILLERS.values())
    assert all("{craft}" in reply for reply in NO_EVIDENCE_REPLIES.values())


def test_every_spoken_phrase_is_written_in_its_language_s_script() -> None:
    for language in VOICE_LANGUAGES:
        script = ANSWER_LANGUAGE_SPECS[language].script
        for table in PHRASE_TABLES:
            assert written_in(table[language].replace("{craft}", ""), script), (language, table[language])
        assert all(written_in(word, script) for word in SOURCE_WORDS[language]), language


def test_a_hindi_reply_names_its_sources_in_hindi_and_keeps_the_labels_as_names() -> None:
    reply = spoken_reply([sentence("फिटकरी रंग पक्का करती है।")], {SOURCE["id"]: SOURCE}, language="hi")
    assert reply.text == "फिटकरी रंग पक्का करती है। स्रोत: GI Journal 188."
    other = {**SOURCE, "id": "other", "kind": "PAPER", "authors": ["Meera Shah"], "year": 2019}
    sources = {SOURCE["id"]: SOURCE, "other": other}
    urdu = spoken_reply([sentence("پہلا۔"), sentence("دوسرا۔", "other")], sources, language="ur")
    assert urdu.text == "پہلا۔ دوسرا۔ مآخذ: GI Journal 188; Shah 2019."
