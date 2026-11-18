import pytest

from app.research.testimony import held_back_terms, quote_span, screens_for

TURNS = {
    "hi": ("हम कपड़े को पानी में भिगोते हैं और फिर धूप में सुखाते हैं", "कपड़े को पानी में भिगोते हैं"),
    "bn": ("সকালে আমরা কাপড় ধুই নদীর জলে।", "আমরা কাপড় ধুই নদীর জলে"),
    "ta": ("முதலில் துணியை தண்ணீரில் ஊற வைப்போம்.", "துணியை தண்ணீரில் ஊற வைப்போம்"),
    "ur": ("پہلے ہم کپڑا پانی میں بھگوتے ہیں۔", "ہم کپڑا پانی میں بھگوتے ہیں"),
}


@pytest.mark.parametrize("language", sorted(TURNS))
def test_a_whole_word_quote_in_an_indian_script_is_found(language: str) -> None:
    turn, quote = TURNS[language]
    span = quote_span(quote, turn)
    assert span is not None
    assert turn[span[0] : span[1]] == quote


@pytest.mark.parametrize("language", sorted(TURNS))
def test_a_quote_that_cuts_a_syllable_is_refused(language: str) -> None:
    turn, quote = TURNS[language]
    assert quote_span(quote[:-1], turn) is None
    assert quote_span(quote[1:], turn) is None


def test_a_quote_ending_on_a_consonant_before_its_vowel_sign_is_refused() -> None:
    turn, _ = TURNS["hi"]
    cut = turn[: turn.index("हैं") + 1]
    assert quote_span(cut, turn) is None


@pytest.mark.parametrize(
    ("name", "said", "unsaid"),
    [
        ("रमेश कुमार", "मेरा नाम रमेश है", "रमेशों के घर"),
        ("সুমিত্রা দাস", "আমি সুমিত্রা, এই কাজ করি", "সুমিত্রারা"),
        ("செல்வி முருகன்", "நான் செல்வி இந்த வேலை செய்கிறேன்", "செல்வியின்"),
        ("فاطمہ بی", "میرا نام فاطمہ ہے", "فاطمہوں"),
    ],
)
def test_a_name_in_an_indian_script_is_held_back_as_a_whole_word(name: str, said: str, unsaid: str) -> None:
    terms = held_back_terms(account_name=name, mode="CRAFT_AND_DISTRICT", credit_name=None, short_name=None)
    assert name.split()[0] in terms
    assert screens_for([said], terms) == ["NAME_HELD_BACK"]
    assert screens_for([unsaid], frozenset({name.split()[0]})) == []


def test_a_first_name_credit_keeps_only_the_rest_of_the_name_back() -> None:
    terms = held_back_terms(account_name="रमेश कुमार", mode="FIRST_NAME", credit_name=None, short_name="रमेश")
    assert terms == frozenset({"कुमार"})
