from pathlib import Path

from app.research.oauth_rules import MCP_TERMS_VERSION
from app.services.oauth_consent import TERMS_PATH

REPO = Path(__file__).resolve().parents[3]
POINTER = REPO / "docs" / "legal" / "mcp-terms-of-use.md"
SERVED = "backend/app/data/mcp_terms_of_use.md"
SECTION = "\n## "


def test_the_legal_page_points_at_the_one_served_copy_of_the_mcp_terms() -> None:
    pointer = POINTER.read_text(encoding="utf-8")
    assert SERVED in pointer
    assert TERMS_PATH == REPO / SERVED
    assert pointer.startswith(f"# MCP terms of use (version {MCP_TERMS_VERSION})\n")


def test_the_terms_text_lives_only_in_the_served_file() -> None:
    assert SECTION not in POINTER.read_text(encoding="utf-8")
    assert TERMS_PATH.read_text(encoding="utf-8").startswith("## What you may do\n")
