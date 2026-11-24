import pytest

from app.renderer.browser import browser_flags
from app.renderer.guard import ALLOW, BLOCK, PASS, RequestGuard, preview_refusal, resolver_rules

SITE = "https://kalavigyan.example"
TOKEN = f"{'a' * 32}.1795000000.{'b' * 64}"
PREVIEW = f"{SITE}/preview/{TOKEN}"


def guard() -> RequestGuard:
    return RequestGuard(site=SITE, preview_url=PREVIEW)


def test_only_a_preview_s_private_link_on_the_site_is_drawn() -> None:
    assert preview_refusal(PREVIEW, SITE) is None
    assert preview_refusal(f"https://elsewhere.example/preview/{TOKEN}", SITE) == (
        "the renderer draws only previews on https://kalavigyan.example"
    )
    assert preview_refusal(f"http://kalavigyan.example/preview/{TOKEN}", SITE) is not None
    for path in ("/crafts/Kutch-Ajrakh", f"/preview/{TOKEN}?next=/admin", "/preview/token"):
        assert preview_refusal(f"{SITE}{path}", SITE) == (
            "the renderer draws only a page preview's private link, /preview/<token>"
        )


@pytest.mark.parametrize(
    ("url", "kind", "verdict"),
    [
        (PREVIEW, "Document", PASS),
        (f"{PREVIEW}#chem", "Document", PASS),
        (f"{SITE}/_next/static/chunks/app.js", "Script", PASS),
        (f"{SITE}/api/knowledge/pages/pictures/0e000000-0000-4000-8000-000000000001", "Image", PASS),
        (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Ajrakh.jpg/960px-Ajrakh.jpg",
            "Image",
            ALLOW,
        ),
        ("https://upload.wikimedia.org/wikipedia/commons/a/ab/Ajrakh.js", "Script", BLOCK),
        (f"{SITE}/login?next=/preview", "Document", BLOCK),
        ("https://fonts.googleapis.com/css2?family=Newsreader", "Stylesheet", BLOCK),
        ("http://169.254.169.254/latest/meta-data/", "Fetch", BLOCK),
        ("http://127.0.0.1:8091/render", "Fetch", BLOCK),
        ("ws://kalavigyan.example/socket", "WebSocket", BLOCK),
    ],
)
def test_the_browser_reaches_the_site_and_its_pictures_and_nothing_else(
    url: str, kind: str, verdict: str
) -> None:
    assert guard().decide(url, kind) == verdict


def test_what_the_browser_was_kept_from_is_named_without_its_query() -> None:
    kept = guard()
    kept.decide(f"{SITE}/login?next=/preview", "Document")
    kept.decide("https://fonts.googleapis.com/css2?family=Newsreader", "Stylesheet")
    assert kept.blocked == {"the site's /login", "fonts.googleapis.com"}


def test_no_host_resolves_but_the_site_s_and_the_picture_host_s() -> None:
    assert (
        resolver_rules(SITE) == "MAP * ~NOTFOUND , EXCLUDE kalavigyan.example , EXCLUDE upload.wikimedia.org"
    )
    flags = browser_flags("/tmp/kv-render-x", SITE)
    assert f"--host-resolver-rules={resolver_rules(SITE)}" in flags
    assert "--user-data-dir=/tmp/kv-render-x" in flags
    assert {"--headless", "--remote-debugging-address=127.0.0.1", "--disable-background-networking"} <= set(
        flags
    )
