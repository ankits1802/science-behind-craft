import json
from typing import Any

from app.providers.router import RouterError
from app.services.answer_events import cited_claims
from app.services.answer_translation import translated_sentences
from app.services.answering import AnswerAsk

from ..composer.fixtures import QUESTION
from ..planner.fakes import FakeModel
from .fakes import (
    ALUM_CLAIM_ID,
    GUESS_CLAIM_ID,
    SOURCES,
    VIEWS,
    WRITTEN_LAKE_ID,
    WRITTEN_WASH_ID,
    FakeResearch,
    FakeStore,
    MemoryCache,
    pipeline,
    streamed,
    translation,
)
from .test_answer_flow import REPLY, events

ALUM_HI = "फिटकरी वह मॉर्डेंट है जो अजरख में एलिज़रिन को कपास से बाँधती है।"
LIME_HI = "धोने के पानी में चूना लाल रंग को चमका सकता है।"
ALUM_SHORT_HI = "फिटकरी वह मॉर्डेंट है जो एलिज़रिन को कपास से बाँधती है।"
LAKE_HI = "मॉर्डेंट के घोल में 8 g/L फिटकरी थी और उसे 60 °C तक गरम किया गया।"
WASH_HI = "लाल लेक 20 धुलाइयों तक टिकी रही।"
WASH_WITHOUT_NUMBER_HI = "लाल लेक कई धुलाइयों तक टिकी रही।"
MORDANT_HI = "मॉर्डेंट"
FASTNESS_HI = "पक्कापन"
FOLLOW_UP_HI = "कच्छ अजरख के लिए फिटकरी का घोल कैसे तैयार किया जाता है?"
TRANSLATING = {"step": "TRANSLATING", "message": "Translating the answer into Hindi"}


def reply(**texts: str) -> str:
    return json.dumps(
        {"items": [{"key": key, "text": text} for key, text in texts.items()]}, ensure_ascii=False
    )


def verified(question: str = QUESTION) -> AnswerAsk:
    return AnswerAsk(question=question, mode="VERIFIED", language="hi")


def stored() -> FakeStore:
    return FakeStore(stored=cited_claims([VIEWS[0], VIEWS[3]], SOURCES))


def payloads(found: list[tuple[str, dict]], name: str) -> list[dict[str, Any]]:
    return [payload for event, payload in found if event == name]


def schema_keys(call: dict[str, Any]) -> list[str]:
    return call["schema"]["properties"]["items"]["items"]["properties"]["key"]["enum"]


async def test_a_verified_answer_in_hindi_translates_each_claim_and_keeps_its_citations() -> None:
    model = FakeModel([reply(**{"s1.1": ALUM_HI, "open.1": LIME_HI})])
    found = events(await streamed(verified(), pipeline(store=stored(), translated=translation(model))))
    assert TRANSLATING in payloads(found, "status")
    (sentence,) = payloads(found, "sentence")
    assert sentence["sentence"]["text"] == ALUM_HI
    assert sentence["sentence"]["translated"] is True
    assert sentence["sentence"]["original"] == "Alum is the mordant that binds alizarin to cotton in Ajrakh."
    assert sentence["sentence"]["citations"][0]["claimId"] == str(ALUM_CLAIM_ID)
    assert sentence["sentence"]["citations"][0]["quote"] == "Alum is the mordant"
    (guess,) = payloads(found, "open_question")
    assert (guess["sentence"]["text"], guess["sentence"]["original"]) == (
        LIME_HI,
        "Lime in the wash water may brighten the red.",
    )
    assert payloads(found, "section") == [{"id": "s1", "heading": "Materials and tools"}]
    assert len(model.calls) == 1
    assert schema_keys(model.calls[0]) == ["s1.1", "open.1"]


async def test_cached_claim_translations_make_no_second_model_call() -> None:
    model = FakeModel([reply(**{"s1.1": ALUM_HI, "open.1": LIME_HI})])
    cache = MemoryCache()
    first = events(await streamed(verified(), pipeline(store=stored(), translated=translation(model, cache))))
    second = events(
        await streamed(verified(), pipeline(store=stored(), translated=translation(model, cache)))
    )
    assert len(model.calls) == 1
    assert sorted(cache.rows) == sorted([(ALUM_CLAIM_ID, "hi"), (GUESS_CLAIM_ID, "hi")])
    texts = [payload["sentence"]["text"] for payload in payloads(second, "sentence")]
    assert texts == [ALUM_HI]
    assert payloads(first, "sentence") == payloads(second, "sentence")


async def test_a_question_in_devanagari_searches_stored_claims_in_english() -> None:
    model = FakeModel(
        [
            reply(question="Why does alum keep Ajrakh red?"),
            reply(**{"s1.1": ALUM_HI, "open.1": LIME_HI}),
        ]
    )
    store = stored()
    await streamed(
        verified("अजरख को फिटकरी लाल क्यों रखती है?"), pipeline(store=store, translated=translation(model))
    )
    assert store.questions == ["Why does alum keep Ajrakh red?"]
    assert schema_keys(model.calls[0]) == ["question"]
    assert model.calls[0]["user"].startswith("Target language: English (en")


async def test_an_english_question_in_verified_mode_makes_no_model_call() -> None:
    model = FakeModel([])
    store = stored()
    ask = AnswerAsk(question=QUESTION, mode="VERIFIED")
    found = events(await streamed(ask, pipeline(store=store, translated=translation(model))))
    assert model.calls == []
    assert store.questions == [QUESTION]
    assert "translated" not in payloads(found, "sentence")[0]["sentence"]


async def test_a_researched_answer_in_hindi_translates_sentences_headings_and_follow_ups_in_one_call() -> (
    None
):
    translated = {
        "s1.1": ALUM_SHORT_HI,
        "s1.2": LAKE_HI,
        "s2.1": WASH_HI,
        "open.1": LIME_HI,
        "heading:s1": MORDANT_HI,
        "heading:s2": FASTNESS_HI,
        "follow-up:0": FOLLOW_UP_HI,
    }
    model = FakeModel([reply(**translated)])
    cache = MemoryCache()
    research = FakeResearch()
    ask = AnswerAsk(question=QUESTION, mode="HYBRID", language="hi")
    found = events(
        await streamed(
            ask, pipeline(research=research, replies=[REPLY], translated=translation(model, cache))
        )
    )
    assert len(model.calls) == 1
    assert schema_keys(model.calls[0]) == list(translated)
    assert payloads(found, "section") == [
        {"id": "s1", "heading": MORDANT_HI, "original": "Mordant"},
        {"id": "s2", "heading": FASTNESS_HI, "original": "Fastness"},
    ]
    texts = [payload["sentence"]["text"] for payload in payloads(found, "sentence")]
    assert texts == [ALUM_SHORT_HI, LAKE_HI, WASH_HI]
    assert payloads(found, "follow_ups") == [{"items": [FOLLOW_UP_HI]}]
    assert sorted(cache.rows) == sorted(
        [(WRITTEN_LAKE_ID, "hi"), (WRITTEN_WASH_ID, "hi"), (GUESS_CLAIM_ID, "hi")]
    )
    (request,) = research.requests
    assert (request.language, request.english_question) == ("hi", QUESTION)


async def test_a_sentence_failing_its_check_twice_is_shown_in_english() -> None:
    first = {
        "s1.1": ALUM_SHORT_HI,
        "s1.2": LAKE_HI,
        "s2.1": WASH_WITHOUT_NUMBER_HI,
        "open.1": LIME_HI,
        "heading:s1": MORDANT_HI,
        "heading:s2": FASTNESS_HI,
        "follow-up:0": FOLLOW_UP_HI,
    }
    model = FakeModel([reply(**first), reply(**{"s2.1": WASH_WITHOUT_NUMBER_HI})])
    ask = AnswerAsk(question=QUESTION, mode="HYBRID", language="hi")
    found = events(await streamed(ask, pipeline(replies=[REPLY], translated=translation(model))))
    assert len(model.calls) == 2
    assert schema_keys(model.calls[1]) == ["s2.1"]
    wash = payloads(found, "sentence")[2]["sentence"]
    assert wash["text"] == "The red lake withstood 20 washes."
    assert "translated" not in wash and "original" not in wash


async def test_a_question_in_tamil_script_plans_without_an_english_rendering() -> None:
    research = FakeResearch()
    ask = AnswerAsk(question="அஜ்ரக் ஏன் சிவப்பாக இருக்கிறது?", mode="HYBRID", language="ta")
    model = FakeModel([reply(), reply()])
    await streamed(ask, pipeline(research=research, replies=[REPLY], translated=translation(model)))
    (request,) = research.requests
    assert (request.language, request.english_question) == ("ta", None)


async def test_a_failed_translation_route_shows_the_answer_in_english() -> None:
    class NoRoute:
        async def __call__(self, **_: object) -> object:
            raise RouterError("no_route", "No enabled route can run TRANSLATE")

    found = events(await streamed(verified(), pipeline(store=stored(), translated=translation(NoRoute()))))
    assert [name for name, _ in found if name == "error"] == []
    (sentence,) = payloads(found, "sentence")
    assert sentence["sentence"]["text"] == "Alum is the mordant that binds alizarin to cotton in Ajrakh."


async def test_voice_sentences_translate_through_the_same_cache() -> None:
    cache = MemoryCache()
    model = FakeModel([reply(**{str(ALUM_CLAIM_ID): ALUM_HI})])
    sentence = {**VIEWS[0].payload(), "id": str(ALUM_CLAIM_ID)}
    texts = {view.id: view.text for view in VIEWS}
    spoken = await translated_sentences(
        [sentence], language="hi", translation=translation(model, cache), claim_texts=texts
    )
    assert spoken == [{**sentence, "text": ALUM_HI, "translated": True, "original": VIEWS[0].text}]
    again = await translated_sentences(
        [sentence], language="hi", translation=translation(model, cache), claim_texts=texts
    )
    assert again == spoken
    assert len(model.calls) == 1
