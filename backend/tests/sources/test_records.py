from datetime import date

import pytest

from app.sources.records import (
    UnusableRecord,
    classify,
    doi_of,
    https_or_none,
    markup_text,
    partial_date_of,
    published_since,
    query_terms,
    title_of,
)
from app.sources.scholarly.openalex import abstract_from_index
from app.sources.scholarly.springer_nature import springer_abstract


def test_markup_is_reduced_to_plain_text() -> None:
    jats = "<jats:title>Abstract</jats:title><jats:p>Alum &amp; iron <jats:italic>mordants</jats:italic>.</jats:p>"
    assert markup_text(jats) == "Abstract Alum & iron mordants."
    assert markup_text("a &lt; b &#8211; c") == "a < b – c"
    assert markup_text("   ") is None
    assert markup_text(None) is None


def test_hidden_scripted_and_styled_markup_is_dropped() -> None:
    commons_date = 'circa 1640<div style="display: none;">date QS:P571,+1640-00-00T00:00:00Z/9</div>–50'
    assert markup_text(commons_date) == "circa 1640–50"
    assert markup_text("a<span hidden>b<span>c</span>d</span>e") == "ae"
    assert markup_text("x<script>alert(1)</script><style>p{}</style>y") == "xy"
    assert markup_text('<p style="DISPLAY : NONE">gone</p>kept') == "kept"


def test_dois_are_recognised_in_their_usual_spellings() -> None:
    assert doi_of("https://doi.org/10.1111/cote.12288") == "10.1111/cote.12288"
    assert doi_of("doi:10.1186/s40494-020-00441-9") == "10.1186/s40494-020-00441-9"
    assert doi_of(" 10.1111/COTE.12288 ") == "10.1111/COTE.12288"
    assert doi_of("2045-2322") is None
    assert doi_of(None) is None


def test_partial_dates_from_each_service_shape() -> None:
    assert partial_date_of("2017-06-13") == "2017-06-13"
    assert partial_date_of("2019-03-26T00:00:00+00:00") == "2019-03-26"
    assert partial_date_of(2017) == "2017"
    assert partial_date_of([2025, 4, 27]) == "2025-04-27"
    assert partial_date_of([2025, 4]) == "2025-04"
    assert partial_date_of([]) is None
    assert partial_date_of("2019-13-01") is None
    assert partial_date_of("March 2019") is None


def test_freshness_counts_the_latest_day_a_partial_date_can_mean() -> None:
    cutoff = date(2025, 6, 30)
    assert published_since("2025", cutoff)
    assert published_since("2025-06", cutoff)
    assert not published_since("2025-05", cutoff)
    assert not published_since("2025-06-29", cutoff)
    assert published_since("2025-06-30", cutoff)
    assert not published_since(None, cutoff)


def test_work_kinds_set_source_type_and_trust() -> None:
    assert classify("article") == ("PAPER", "A")
    assert classify("preprint") == ("PAPER", "B")
    assert classify("repository") == ("PAPER", "B")
    assert classify("chapter") == ("BOOK_CHAPTER", "A")
    assert classify("other") == ("OTHER", "C")
    with pytest.raises(ValueError):
        classify("blog")


def test_only_https_urls_are_kept() -> None:
    assert https_or_none("https://core.ac.uk/works/1") == "https://core.ac.uk/works/1"
    assert https_or_none("http://www.sciencedirect.com/science/article/pii/S1") is None
    assert https_or_none("") is None


def test_titles_are_required() -> None:
    assert title_of(["", "Mordant dyes"]) == "Mordant dyes"
    with pytest.raises(UnusableRecord):
        title_of([])


def test_query_terms_keep_words_only() -> None:
    assert query_terms("alizarin: mordant / cotton (Ajrakh)") == ["alizarin", "mordant", "cotton", "Ajrakh"]
    assert query_terms("—") == []
    assert len(query_terms(" ".join(["w"] * 20))) == 8


def test_an_inverted_index_is_read_back_in_word_order() -> None:
    assert abstract_from_index({"dyed": [2], "Cotton": [0], "is": [1], "with": [3], "madder": [4]}) == (
        "Cotton is dyed with madder"
    )
    assert abstract_from_index({}) is None
    assert abstract_from_index(None) is None


def test_springer_abstracts_come_as_text_or_sections() -> None:
    assert springer_abstract("Plain abstract.") == "Plain abstract."
    assert (
        springer_abstract({"h1": "Abstract", "p": ["First part.", "Second part."]})
        == "First part. Second part."
    )
    assert springer_abstract({"h1": "Abstract"}) is None
