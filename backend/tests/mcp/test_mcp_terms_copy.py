from pathlib import Path

from app.services.oauth_consent import TERMS_PATH

DRAFT = Path(__file__).resolve().parents[3] / "docs" / "legal" / "mcp-terms-of-use.md"
FIRST_HEADING = "## "


def test_the_served_mcp_terms_are_the_legal_draft_below_its_preface() -> None:
    draft = DRAFT.read_text(encoding="utf-8")
    body = draft[draft.index(FIRST_HEADING) :]
    assert TERMS_PATH.read_text(encoding="utf-8") == body
