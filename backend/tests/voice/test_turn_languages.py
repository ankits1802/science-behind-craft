import asyncio
import uuid
from dataclasses import dataclass, field, replace
from datetime import timedelta
from typing import Any

from app.composer.translation import TRANSLATE_SYSTEM_PROMPT
from app.research.structured import StructuredReply
from app.schemas.voice import VoiceTurnView
from app.voice.compose import VOICE_TURN_SYSTEM_PROMPT
from app.voice.spoken import word_count
from app.voice.turns import TurnAsk, spoken_turn

from .fakes import (
    ALUM,
    ANSWER_ID,
    CLAIM_ID,
    START,
    TURN_ID,
    FakeModel,
    MemoryTranslationCache,
    alum_pack,
    alum_view,
    compose_reply,
    session,
    tools,
    translation,
    translation_reply,
)

HINDI_QUESTION = "अजरख छापने वाले फिटकरी का उपयोग क्यों करते हैं?"
ENGLISH_QUESTION = "Why do Ajrakh printers use alum?"
HINDI_ALUM = "फिटकरी का उपयोग रंगों को पक्का करने के लिए मॉर्डेंट के रूप में किया जाता है।"
TAMIL_QUESTION = "படிகாரம் எவ்வளவு கரைக்கப்படுகிறது?"
TAMIL_ENGLISH_QUESTION = "How much alum is dissolved?"
FIVE_GRAMS = "Alum is dissolved at 5 g/L before the cloth is dipped."
TAMIL_IN_WORDS = "துணியை நனைப்பதற்கு முன் படிகாரம் ஐந்து கிராம் அளவில் கரைக்கப்படுகிறது."
TAMIL_FIVE_GRAMS = "துணியை நனைப்பதற்கு முன் படிகாரம் 5 g/L அளவில் கரைக்கப்படுகிறது."
FIRST = "Alum is dissolved in warm water and the cloth is soaked so that the madder dye binds to the cotton fibres."
SECOND = (
    "Boiled alum water is brushed 2 times onto the printed areas before the cloth goes into the madder bath."
)
SECOND_ID = uuid.UUID("0d1e2f3a-4b5c-4d6e-8f7a-9b0c1d2e3f4a")


def asked(question: str, language: str, *, mode: str = "HYBRID", seconds_left: float = 600.0) -> TurnAsk:
    return TurnAsk(session(language=language, mode=mode), question, 1, TURN_ID, ANSWER_ID, seconds_left)


def two_claims() -> Any:
    first = replace(alum_view(), text=FIRST)
    second = replace(alum_view(), id=SECOND_ID, text=SECOND)
    return alum_pack(first, second, mode="VERIFIED")


async def test_a_hindi_turn_ranks_composes_and_checks_in_english_then_speaks_hindi() -> None:
    translator = FakeModel(
        [translation_reply(question=ENGLISH_QUESTION), translation_reply(**{"s1.1": HINDI_ALUM})]
    )
    cache = MemoryTranslationCache()
    composer = FakeModel([compose_reply(ALUM, ALUM)])
    turn = await spoken_turn(
        asked(HINDI_QUESTION, "hi"), tools(model=composer, translated=translation(translator, cache))
    )
    assert turn.heard == HINDI_QUESTION
    assert turn.spoken == f"{HINDI_ALUM} स्रोत: GI Journal 188."
    [sentence] = turn.sentences
    assert (sentence["id"], sentence["text"], sentence["translated"], sentence["original"]) == (
        "t1.1",
        HINDI_ALUM,
        True,
        ALUM,
    )
    assert sentence["citations"] == alum_view().citations
    assert turn.claim_ids == (CLAIM_ID,) and turn.answer_id == ANSWER_ID
    [compose_call] = composer.calls
    assert compose_call["system"] == VOICE_TURN_SYSTEM_PROMPT
    assert HINDI_QUESTION in compose_call["user"] and "Answer language: en" in compose_call["user"]
    assert [call["system"] for call in translator.calls] == [TRANSLATE_SYSTEM_PROMPT] * 2
    assert "Target language: English" in translator.calls[0]["user"]
    assert "Target language: Hindi" in translator.calls[1]["user"]
    assert cache.rows == {(CLAIM_ID, "hi"): (ALUM, HINDI_ALUM)}
    assert VoiceTurnView.model_validate(turn.view()).spoken == turn.spoken


async def test_the_sixty_word_cap_counts_the_hindi_that_is_spoken() -> None:
    thirty = " ".join(["शब्द"] * 30)
    assert word_count(f"{FIRST} {SECOND} Source: GI Journal 188.") == 21 + 19 + 4
    translator = FakeModel(
        [
            translation_reply(question="Why is alum used?"),
            translation_reply(**{str(CLAIM_ID): thirty, str(SECOND_ID): f"{thirty} 2"}),
        ]
    )
    turn = await spoken_turn(
        asked(HINDI_QUESTION, "hi", mode="VERIFIED"), tools(two_claims(), translated=translation(translator))
    )
    assert [s["original"] for s in turn.sentences] == [FIRST]
    assert turn.spoken == f"{thirty} स्रोत: GI Journal 188."
    assert word_count(turn.spoken) == 30 + 4


async def test_a_sentence_whose_translation_fails_twice_is_left_out_of_the_spoken_reply() -> None:
    first_hindi = "फिटकरी को गुनगुने पानी में घोलकर कपड़ा भिगोया जाता है।"
    second_without_number = "उबला फिटकरी का पानी छपे हिस्सों पर लगाया जाता है।"
    translator = FakeModel(
        [
            translation_reply(question="Why is alum used?"),
            translation_reply(**{str(CLAIM_ID): first_hindi, str(SECOND_ID): second_without_number}),
            translation_reply(**{str(SECOND_ID): second_without_number}),
        ]
    )
    turn = await spoken_turn(
        asked(HINDI_QUESTION, "hi", mode="VERIFIED"), tools(two_claims(), translated=translation(translator))
    )
    assert "number 2 is missing" in translator.calls[2]["user"]
    assert [s["text"] for s in turn.sentences] == [first_hindi]
    assert turn.spoken == f"{first_hindi} स्रोत: GI Journal 188."
    assert SECOND not in turn.spoken and "Boiled" not in turn.spoken


async def test_a_reply_that_cannot_be_translated_at_all_asks_again_in_hindi() -> None:
    translator = FakeModel([translation_reply(question=ENGLISH_QUESTION), "not json", "not json"])
    turn = await spoken_turn(asked(HINDI_QUESTION, "hi"), tools(translated=translation(translator)))
    assert turn.spoken == "अभी यह उत्तर तैयार नहीं हो सका। कृपया फिर से पूछिए।"
    assert turn.sentences == () and turn.answer_id is None and turn.actions == ()


async def test_a_tamil_turn_keeps_the_figure_and_unit_and_reuses_the_cached_translation() -> None:
    pack = alum_pack(replace(alum_view(), text=FIVE_GRAMS), mode="VERIFIED")
    translator = FakeModel(
        [
            translation_reply(question=TAMIL_ENGLISH_QUESTION),
            translation_reply(**{str(CLAIM_ID): TAMIL_IN_WORDS}),
            translation_reply(**{str(CLAIM_ID): TAMIL_FIVE_GRAMS}),
            translation_reply(question=TAMIL_ENGLISH_QUESTION),
        ]
    )
    cache = MemoryTranslationCache()
    turn = await spoken_turn(
        asked(TAMIL_QUESTION, "ta", mode="VERIFIED"), tools(pack, translated=translation(translator, cache))
    )
    refused = translator.calls[2]["user"]
    assert "number 5 is missing" in refused and "g/L must be copied exactly" in refused
    assert turn.spoken == f"{TAMIL_FIVE_GRAMS} ஆதாரம்: GI Journal 188."
    assert turn.sentences[0]["original"] == FIVE_GRAMS
    again = await spoken_turn(
        asked(TAMIL_QUESTION, "ta", mode="VERIFIED"), tools(pack, translated=translation(translator, cache))
    )
    assert again.spoken == turn.spoken and len(translator.calls) == 4


async def test_an_english_turn_makes_no_translation_call() -> None:
    turn = await spoken_turn(asked(ENGLISH_QUESTION, "en"), tools(translated=translation(FakeModel([]))))
    assert turn.spoken == f"{ALUM} Source: GI Journal 188."
    assert "translated" not in turn.sentences[0]


@dataclass
class HeldModel:
    replies: list[str]
    hold_from: int
    release: asyncio.Event = field(default_factory=asyncio.Event)
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def __call__(self, *, system: str, user: str, schema: Any) -> StructuredReply:
        self.calls.append({"system": system, "user": user})
        if len(self.calls) >= self.hold_from:
            await self.release.wait()
        return StructuredReply(text=self.replies[len(self.calls) - 1], degraded=False)


async def test_translation_that_would_outlast_the_call_is_cut_off_and_asks_again() -> None:
    translator = HeldModel([translation_reply(question=ENGLISH_QUESTION)], hold_from=2)
    turn = await spoken_turn(
        asked(HINDI_QUESTION, "hi", seconds_left=0.05),
        tools(translated=translation(translator)),
    )
    assert len(translator.calls) == 2
    assert turn.spoken == "अभी यह उत्तर तैयार नहीं हो सका। कृपया फिर से पूछिए।"


def test_a_turn_may_last_until_the_call_s_hard_end() -> None:
    record = session(turn_count=3)
    ask = TurnAsk.begun(record, "x", turn_id=TURN_ID, answer_id=ANSWER_ID, now=START + timedelta(seconds=60))
    assert (ask.ordinal, ask.seconds_left) == (3, 120 + 540 - 60)
    late = TurnAsk.begun(record, "x", turn_id=TURN_ID, answer_id=ANSWER_ID, now=START + timedelta(hours=1))
    assert late.seconds_left == 0.0
