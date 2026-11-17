from app.research.term_marking import GlossaryEntry, TermMarker
from app.research.terms import span_problems, spans_still_shown

KUT = GlossaryEntry("kut", ("Kut",))
KHARIYANU = GlossaryEntry("khariyanu", ("Khariyanu", "kiriyana"))
DATLA = GlossaryEntry("datla", ("datla",))
RESIST_PASTE = GlossaryEntry("resist-paste", ("resist paste",))
PASTE = GlossaryEntry("paste", ("paste",))
MADDER = GlossaryEntry("indian-madder", ("Indian madder", "majith", "majeeta"))


def marked(text: str, *glossary: GlossaryEntry) -> list[tuple[str, str]]:
    spans = TermMarker(list(glossary)).spans(text)
    assert span_problems(text, spans) == []
    return [(span.text, span.term_key) for span in spans]


def test_terms_are_marked_where_they_first_appear_in_reading_order() -> None:
    text = "Areas where black is required are printed with kut paste, usually an infill (datla) between khariyanu outlines."
    assert marked(text, KHARIYANU, DATLA, KUT) == [
        ("kut", "kut"),
        ("datla", "datla"),
        ("khariyanu", "khariyanu"),
    ]


def test_the_longest_name_wins_and_spans_never_overlap() -> None:
    text = "Outlines are printed with a lime and tree-gum resist paste."
    assert marked(text, PASTE, RESIST_PASTE) == [("resist paste", "resist-paste")]


def test_a_local_name_marks_its_term_once() -> None:
    text = "Majith roots, Indian madder, give the red."
    assert marked(text, MADDER) == [("Majith", "indian-madder")]


def test_a_name_inside_a_longer_word_is_not_marked() -> None:
    assert marked("The kutch printers use kut.", KUT) == []
    assert marked("Kut is fermented iron.", KUT) == [("Kut", "kut")]


def test_a_name_two_terms_share_is_never_guessed() -> None:
    other = GlossaryEntry("datla-block", ("datla",))
    assert marked("An infill (datla) is printed.", DATLA, other) == []


def test_an_empty_glossary_marks_nothing() -> None:
    assert marked("Kut is fermented iron.") == []


def test_a_translated_sentence_keeps_only_the_spans_its_text_still_shows() -> None:
    spans = [
        {"text": "Kut", "termKey": "kut"},
        {"text": "datla", "termKey": "datla"},
        {"text": "khariyanu", "termKey": "khariyanu"},
    ]
    text = "काले हिस्सों पर kut छापा जाता है, khariyanu रेखाओं के बीच।"
    assert spans_still_shown(text, spans) == [spans[2]]
    assert spans_still_shown("datla (khariyanu) datla", spans) == spans[1:]


def test_a_span_whose_first_place_overlaps_a_kept_one_is_dropped() -> None:
    spans = [{"text": "resist paste", "termKey": "resist-paste"}, {"text": "paste", "termKey": "paste"}]
    assert spans_still_shown("lime resist paste, then paste again", spans) == spans[:1]
