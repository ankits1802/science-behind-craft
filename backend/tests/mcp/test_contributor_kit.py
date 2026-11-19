import re
from pathlib import Path

from app.data.contributor_kit import (
    CONTRIBUTOR_SKILL_PATH,
    DESIGN_TOKENS_PATH,
    SITE_SKILL_PATH,
    skill_section,
)
from app.models.enums import DISCIPLINES
from app.research.sections import DISCIPLINE_FIELDS, DISCIPLINE_TITLES

REPOSITORY = Path(__file__).resolve().parents[3]
SITE_COPY = REPOSITORY / "frontend" / "public" / SITE_SKILL_PATH.lstrip("/")
SKILL_TOKENS = REPOSITORY / ".claude" / "skills" / "kalavigyan-design" / "references" / "tokens.json"
ROW = re.compile(r"^\| (?P<field>[A-Z]+) \| (?P<title>[^|]+) \| (?P<covers>[^|]+) \|$", re.MULTILINE)


def test_the_site_serves_the_same_contributor_skill_as_the_mcp_resource() -> None:
    assert SITE_COPY.read_bytes() == CONTRIBUTOR_SKILL_PATH.read_bytes()


def test_the_design_tokens_resource_is_the_design_skill_s_tokens() -> None:
    assert DESIGN_TOKENS_PATH.read_bytes() == SKILL_TOKENS.read_bytes()


def test_the_skill_names_itself_for_agents_that_load_skills() -> None:
    head = CONTRIBUTOR_SKILL_PATH.read_bytes().decode("utf-8").split("---")[1]
    assert "name: kalavigyan-contributor" in head
    assert "description:" in head


def test_the_skill_lists_every_field_with_its_title_and_what_it_covers() -> None:
    rows = [match.groupdict() for match in ROW.finditer(skill_section("The fields"))]
    assert [row["field"] for row in rows] == list(DISCIPLINES)
    assert {row["field"]: row["title"] for row in rows} == dict(DISCIPLINE_TITLES)
    assert {row["field"]: row["covers"] for row in rows} == dict(DISCIPLINE_FIELDS)
