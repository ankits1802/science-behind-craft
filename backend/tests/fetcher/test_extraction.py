import pytest

from app.fetcher.extract import content_type_of, extract
from app.fetcher.pdf import pdf_text
from app.fetcher.robots import rules_for_answer
from app.research.fetcher import FETCH_TEXT_MAX_CHARS, FetchRefused, PageMetadata

from .pdf_fixture import pdf_with_pages
from .site import fixture

URL = "https://crafts.example.org/ajrakh/resist-printing"
PDF_URL = "https://crafts.example.org/notes.pdf"
ARTICLE_PARAGRAPHS = [
    "Ajrakh printers in Kutch soak cotton in a solution of camel dung, soda ash and castor oil before the first printing.",
    "The resist paste of lime and gum arabic keeps the dye away from the printed areas, and alum is printed where red is wanted.",
    "After printing, the cloth is boiled with alizarin, which forms a red lake only where the alum mordant was applied.",
    "Indigo vats are fermented separately with jaggery and lime for about ten days.",
]


def test_the_article_text_is_the_main_content_in_reading_order() -> None:
    extracted = extract(URL, "text/html", fixture("article.html"), None)
    positions = [extracted.text.index(paragraph) for paragraph in ARTICLE_PARAGRAPHS]
    assert positions == sorted(positions)
    assert "Home" not in extracted.text.split("\n")
    assert extracted.truncated is False


def test_the_article_metadata_comes_from_its_head_and_licence_link() -> None:
    extracted = extract(URL, "text/html", fixture("article.html"), None)
    assert extracted.metadata == PageMetadata(
        title="Ajrakh resist printing",
        authors=["Meera Shah"],
        published="2024-03-18",
        licence="CC BY 4.0",
        canonical_url="https://crafts.example.org/ajrakh/resist-printing",
        site_name="Craft Notes",
        language="en",
    )


def test_a_page_with_no_main_text_fails_to_parse() -> None:
    with pytest.raises(FetchRefused) as refused:
        extract(URL, "text/html", b"<html><body><script>alert(1)</script></body></html>", None)
    assert refused.value.reason == "PARSE_FAILED"


def test_plain_text_keeps_indic_joiners_and_drops_invisible_controls() -> None:
    body = "अज्\u200dरख\u202e ছাপা\u200b \U000e0049\U000e0047gone\x07".encode()
    text = extract(URL, "text/plain", body, "utf-8").text
    assert text == "अज्\u200dरख ছাপা gone"


def test_text_past_the_cap_is_cut_and_marked_truncated() -> None:
    extracted = extract(URL, "text/plain", b"a" * (FETCH_TEXT_MAX_CHARS + 1), None)
    assert (len(extracted.text), extracted.truncated) == (FETCH_TEXT_MAX_CHARS, True)


def test_an_unknown_charset_falls_back_to_utf8() -> None:
    assert extract(URL, "text/plain", "kalamkārī".encode(), "x-unknown").text == "kalamkārī"


@pytest.mark.parametrize(
    ("declared", "kept"),
    [
        ("text/html", "text/html"),
        ("application/xhtml+xml", "text/html"),
        ("application/pdf", "application/pdf"),
        ("text/plain", "text/plain"),
    ],
)
def test_accepted_content_types(declared: str, kept: str) -> None:
    assert content_type_of(URL, declared) == kept


@pytest.mark.parametrize("declared", ["image/png", "application/octet-stream", "application/javascript", ""])
def test_other_content_types_are_refused(declared: str) -> None:
    with pytest.raises(FetchRefused) as refused:
        content_type_of(URL, declared)
    assert refused.value.reason == "CONTENT_TYPE"


def test_pdf_pages_are_joined_with_their_metadata() -> None:
    body = pdf_with_pages(
        ["Alum fixes the red dye.", "Indigo needs a reduced (leuco) vat."],
        title="Mordants and vats",
        author="R. Iyer",
        created="D:20190704120000Z",
    )
    text, truncated, metadata = pdf_text(PDF_URL, body)
    assert text == "Alum fixes the red dye.\n\nIndigo needs a reduced (leuco) vat."
    assert truncated is False
    assert metadata == PageMetadata(title="Mordants and vats", authors=["R. Iyer"], published="2019-07-04")


def test_pages_past_the_page_cap_are_left_out_and_marked() -> None:
    body = pdf_with_pages([f"Page {n} text." for n in range(1, 5)])
    text, truncated, _ = pdf_text(PDF_URL, body, max_pages=3)
    assert text == "Page 1 text.\n\nPage 2 text.\n\nPage 3 text."
    assert truncated is True


def test_content_past_the_decompressed_cap_is_refused() -> None:
    body = pdf_with_pages(["Alum fixes the red dye.", "Indigo needs a reduced vat."])
    with pytest.raises(FetchRefused) as refused:
        pdf_text(PDF_URL, body, max_decompressed=60)
    assert refused.value.reason == "PDF_LIMIT"


@pytest.mark.parametrize("body", [b"not a pdf at all", b"%PDF-1.4\n%%EOF\n"])
def test_a_broken_pdf_fails_to_parse(body: bytes) -> None:
    with pytest.raises(FetchRefused) as refused:
        pdf_text(PDF_URL, body)
    assert refused.value.reason == "PARSE_FAILED"


ROBOTS = b"User-agent: *\nDisallow: /private/\n\nUser-agent: KalaVigyan\nDisallow: /drafts/\n"


def test_robots_rules_for_our_agent_apply() -> None:
    rules = rules_for_answer(200, ROBOTS)
    assert rules.allows("https://crafts.example.org/ajrakh") is True
    assert rules.allows("https://crafts.example.org/drafts/x") is False


@pytest.mark.parametrize(
    ("status", "allowed"), [(404, True), (410, True), (401, True), (429, False), (500, False), (503, False)]
)
def test_robots_answers_without_a_file_follow_rfc_9309(status: int, allowed: bool) -> None:
    assert rules_for_answer(status, b"").allows("https://crafts.example.org/") is allowed
