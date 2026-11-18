import uuid
from collections.abc import Mapping

from app.research.translation import TranslationRequest
from app.services.answer_translation import (
    TERM_SEGMENT_PREFIX,
    AnswerTranslation,
    translated_block,
    translated_sentences,
)

HINDI = {
    "p.1": "साज के पेड़ की छाल से कुट बनता है।",
    "p.2": "गच को चूने से बनाया जाता है।",
    f"{TERM_SEGMENT_PREFIX}1": "कुट",
    f"{TERM_SEGMENT_PREFIX}2": "साज",
    f"{TERM_SEGMENT_PREFIX}3": "गच",
}


class Translator:
    def __init__(self) -> None:
        self.asked: list[list[tuple[str, str]]] = []

    async def translate(self, request: TranslationRequest) -> dict[str, str]:
        self.asked.append([(item.key, item.text) for item in request.items])
        return {item.key: HINDI[item.key] for item in request.items if item.key in HINDI}


class NoCache:
    async def known(self, language: str, texts: Mapping[uuid.UUID, str]) -> dict[uuid.UUID, str]:
        return {}

    async def remember(self, language: str, entries: Mapping[uuid.UUID, tuple[str, str]]) -> None:
        return None


def sentence(sentence_id: str, text: str, *terms: str) -> dict:
    return {
        "id": sentence_id,
        "text": text,
        "level": "PROVISIONAL",
        "citations": [],
        "terms": [{"text": term, "termKey": term} for term in terms],
    }


SENTENCES = [
    sentence("p.1", "Kut is made from the bark of the saaj tree.", "kut", "saaj"),
    sentence("p.2", "Gach is made with lime.", "Gach"),
]


async def test_term_names_are_translated_in_the_same_call_and_mark_the_translation() -> None:
    translator = Translator()
    translation = AnswerTranslation(translator=translator, cache=NoCache())
    shown = await translated_sentences(SENTENCES, language="hi", translation=translation, claim_texts={})
    assert len(translator.asked) == 1
    assert translator.asked[0][2:] == [
        (f"{TERM_SEGMENT_PREFIX}1", "kut"),
        (f"{TERM_SEGMENT_PREFIX}2", "saaj"),
        (f"{TERM_SEGMENT_PREFIX}3", "Gach"),
    ]
    assert [s["terms"] for s in shown] == [
        [{"text": "कुट", "termKey": "kut"}, {"text": "साज", "termKey": "saaj"}],
        [{"text": "गच", "termKey": "Gach"}],
    ]


async def test_a_block_keeps_only_the_terms_whose_hindi_name_still_shows() -> None:
    class Partial(Translator):
        async def translate(self, request: TranslationRequest) -> dict[str, str]:
            found = await super().translate(request)
            return {**found, f"{TERM_SEGMENT_PREFIX}2": "सज्जा"}

    translation = AnswerTranslation(translator=Partial(), cache=NoCache())
    block = {"id": "s1.b1", "kind": "prose", "version": 1, "reuse": None, "sentences": SENTENCES[:1]}
    shown = await translated_block(block, language="hi", translation=translation, claim_texts={})
    (first,) = shown["sentences"]
    assert first["text"] == HINDI["p.1"] and first["original"] == SENTENCES[0]["text"]
    assert first["terms"] == [{"text": "कुट", "termKey": "kut"}]
