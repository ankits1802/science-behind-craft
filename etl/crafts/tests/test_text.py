import pytest

from app.data.craft_master_loader import codes_normalise, normalise
from app.data.craft_text import (
    ascii_key,
    core_key,
    fold,
    indic_inherent_vowels,
    schwa_deleted,
    script_of,
    to_latin,
    to_latin_spoken,
    unaccent,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Bāgh Prints & Co", "bagh prints and co"),
        ("  Kutch   Ajrakh (GI) ", "kutch ajrakh gi"),
        ('Nachiarkoil Kuthuvilakku ("Nachiarkoil Lamp")', "nachiarkoil kuthuvilakku nachiarkoil lamp"),
        ("Café-Crème", "cafe creme"),
        ("", ""),
        (None, ""),
    ],
)
def test_ascii_key_folds_latin(text, expected):
    assert ascii_key(text) == expected


def test_ascii_key_agrees_with_designer_portal_normalisers_on_latin():
    for text in ["Bagru Hand Block Print", "Bell Metal Ware of Datia and Tikamgarh", "Thewa Art Work"]:
        assert ascii_key(text) == normalise(text) == codes_normalise(text)


def test_core_key_drops_stop_tokens_but_keeps_place():
    assert core_key("Bagh Prints of Madhya Pradesh") == "bagh madhya pradesh"
    assert core_key("The Art of Kalamkari") == "kalamkari"


@pytest.mark.parametrize(
    ("text", "script"),
    [
        ("बगरू", "Deva"),
        ("বাঁকুড়া", "Beng"),
        ("மண்பாண்டம்", "Taml"),
        ("ಕಸೂತಿ", "Knda"),
        ("Bagru", "Latn"),
        ("اجرک", "Arab"),
        ("123", "Zyyy"),
    ],
)
def test_script_of(text, script):
    assert script_of(text) == script


def test_inherent_vowel_pass_matches_naming_rule():
    assert to_latin("बगरू") == "bagaru"
    assert indic_inherent_vowels("कलम") == "कaलaम"


@pytest.mark.parametrize(
    ("text", "spoken"),
    [("बगरू", "bagru"), ("अजरख", "ajrakh"), ("कलमकारी", "kalamkari"), ("बांधणी", "bamdhni"), ("छपाई", "chapai")],
)
def test_schwa_deletion_gives_spoken_latin(text, spoken):
    assert to_latin_spoken(text) == spoken


def test_schwa_deletion_leaves_dravidian_scripts_alone():
    assert schwa_deleted("ಕಸೂತಿ") == indic_inherent_vowels("ಕಸೂತಿ")
    assert to_latin_spoken("ಕಸೂತಿ") == "kasuti"


def test_fold_keeps_indic_marks_and_strips_latin_accents():
    assert fold("कलमकारी") == "कलमकारी"
    assert fold("Bāgh, Print!") == "bagh print"
    assert unaccent("é") == "e"
    assert unaccent("कि") == "कि"
