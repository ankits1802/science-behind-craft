import pytest
from pydantic import ValidationError

from app.research.quotes import figures_in, fold_digits, numbers_in, unsupported_figures
from app.research.translation import TranslationRequest, protected_tokens, translation_problems
from app.research.vocabulary import ANSWER_LANGUAGES, CANONICAL_LANGUAGE, text_direction

SCRIPT_ZEROS = {
    "Devanagari": 0x0966,
    "Bengali": 0x09E6,
    "Gurmukhi": 0x0A66,
    "Gujarati": 0x0AE6,
    "Odia": 0x0B66,
    "Tamil": 0x0BE6,
    "Telugu": 0x0C66,
    "Kannada": 0x0CE6,
    "Malayalam": 0x0D66,
    "Arabic-Indic": 0x0660,
    "Extended Arabic-Indic": 0x06F0,
}
ENGLISH = "Mordant baths held 8 g/L alum and were heated to 60 °C."
HINDI = "मॉर्डेंट के घोल में 8 g/L फिटकरी थी और उसे 60 °C तक गरम किया गया।"


@pytest.mark.parametrize("script", sorted(SCRIPT_ZEROS))
def test_the_ten_digits_of_each_script_fold_to_ascii(script: str) -> None:
    digits = "".join(chr(SCRIPT_ZEROS[script] + value) for value in range(10))
    assert fold_digits(digits) == "0123456789"


def test_native_numbers_read_as_their_values() -> None:
    assert numbers_in("तापमान ६० °C") == ["60"]
    assert numbers_in("১,২০০ জন") == ["1200"]
    assert numbers_in("۱٫۵ کلو") == ["1.5"]
    assert numbers_in("௧௨ நாட்கள்") == ["12"]


def test_a_quote_in_native_digits_supports_the_same_figure() -> None:
    assert unsupported_figures("The bath is heated to 60 °C.", ["घोल को ६० °C तक गरम किया जाता है"]) == []
    assert unsupported_figures("The bath is heated to 70 °C.", ["घोल को ६० °C तक गरम किया जाता है"]) == ["70"]


def test_folding_keeps_formulas_whole() -> None:
    assert figures_in("Rust is Fe2O3 and alum adds 12 parts.") == ["Fe2O3", "12"]


def test_a_faithful_translation_passes() -> None:
    assert translation_problems(ENGLISH, HINDI, language="hi") == []


def test_a_translation_in_native_digits_passes() -> None:
    native = HINDI.replace("8", chr(0x096E)).replace("60", chr(0x096C) + chr(0x0966))
    assert native != HINDI
    assert translation_problems(ENGLISH, native, language="hi") == []


def test_indian_digit_grouping_is_the_same_number() -> None:
    assert (
        translation_problems(
            "About 120,000 artisans print Ajrakh.", "लगभग 1,20,000 कारीगर अजरख छापते हैं।", language="hi"
        )
        == []
    )


def test_urdu_in_extended_arabic_indic_digits_passes() -> None:
    urdu = "اسے " + chr(0x06F6) + chr(0x06F0) + " °C تک گرم کیا گیا۔"
    assert translation_problems("It was heated to 60 °C.", urdu, language="ur") == []


def test_a_changed_number_fails_both_ways() -> None:
    wrong = HINDI.replace("60", "65")
    assert translation_problems(ENGLISH, wrong, language="hi") == [
        "number 60 is missing",
        "number 65 is not in the original",
    ]


def test_a_number_added_from_a_word_fails() -> None:
    problems = translation_problems("Three dyes are used.", "3 रंगों का प्रयोग होता है।", language="hi")
    assert problems == ["number 3 is not in the original"]


def test_a_unit_written_in_words_fails() -> None:
    worded = HINDI.replace("60 °C", "60 डिग्री सेल्सियस")
    assert translation_problems(ENGLISH, worded, language="hi") == ["°C must be copied exactly"]


def test_a_changed_formula_fails() -> None:
    english = "Rust on the iron is Fe2O3."
    assert translation_problems(english, "लोहे पर जंग Fe2O3 है।", language="hi") == []
    assert translation_problems(english, "लोहे पर जंग FeO3 है।", language="hi") == [
        "Fe2O3 must be copied exactly",
        "FeO3 is not in the original",
    ]


def test_mhchem_markup_must_be_copied_exactly() -> None:
    english = r"Iron dissolves: \ce{Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2}."
    kept = r"लोहा घुलता है: \ce{Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2}।"
    squeezed = r"लोहा घुलता है: \ce{Fe + 2CH3COOH -> Fe(CH3COO)2 + H2}।"
    assert translation_problems(english, kept, language="hi") == []
    assert r"\ce{Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2} must be copied exactly" in translation_problems(
        english, squeezed, language="hi"
    )


def test_ph_is_a_protected_unit() -> None:
    assert protected_tokens("The bath stays near pH 4.") == {"pH"}
    assert translation_problems(
        "The bath stays near pH 4.", "घोल का पीएच 4 के पास रहता है।", language="hi"
    ) == ["pH must be copied exactly"]


def test_an_untranslated_text_is_refused() -> None:
    assert translation_problems(ENGLISH, ENGLISH, language="hi") == [
        "the translation is not written in the Deva script"
    ]


def test_an_empty_translation_is_refused() -> None:
    assert translation_problems(ENGLISH, "  ", language="ta") == ["the translation is empty"]


def test_requests_carry_unique_keys_in_an_offered_language() -> None:
    with pytest.raises(ValidationError):
        TranslationRequest(language="hi", items=[{"key": "a", "text": "x"}, {"key": "a", "text": "y"}])
    with pytest.raises(ValidationError):
        TranslationRequest(language="fr", items=[{"key": "a", "text": "x"}])


def test_english_and_twelve_indian_languages_are_offered_and_only_urdu_is_right_to_left() -> None:
    assert ANSWER_LANGUAGES == ("en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "or", "pa", "as", "ur")
    assert CANONICAL_LANGUAGE == "en"
    assert [code for code in ANSWER_LANGUAGES if text_direction(code) == "rtl"] == ["ur"]
