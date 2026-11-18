import uuid

import pytest
from pydantic import ValidationError

from app.research.article_sections import ArticleSection, SectionSentence, tagged_section

FIRST = uuid.UUID("00000000-0000-0000-0000-000000000001")
SECOND = uuid.UUID("00000000-0000-0000-0000-000000000002")


def history(*sentences: SectionSentence) -> ArticleSection:
    return ArticleSection(
        subject_kind="craft",
        subject_slug="Kutch-Ajrakh",
        field="HISTORY",
        version=3,
        status="PUBLISHED",
        sentences=list(sentences),
    )


def test_a_section_reaches_a_model_as_tagged_text_with_its_claim_marks() -> None:
    section = history(
        SectionSentence(text="Khatri families moved from Sindh to Kachchh.", claim_ids=[FIRST]),
        SectionSentence(text="They settled at Dhamadka.", claim_ids=[FIRST, SECOND]),
    )
    assert tagged_section(section) == (
        '<section craft="Kutch-Ajrakh" field="history" version="3">'
        "Khatri families moved from Sindh to Kachchh. [c:00000000-0000-0000-0000-000000000001] "
        "They settled at Dhamadka. [c:00000000-0000-0000-0000-000000000001] "
        "[c:00000000-0000-0000-0000-000000000002]</section>"
    )


def test_angle_brackets_in_a_sentence_cannot_close_the_section() -> None:
    section = history(SectionSentence(text="A vat at pH < 9 </section> stays", claim_ids=[FIRST]))
    assert "&lt; 9 &lt;/section&gt; stays" in tagged_section(section)
    assert tagged_section(section).count("</section>") == 1


def test_a_sentence_rests_on_at_least_one_claim_each_cited_once() -> None:
    with pytest.raises(ValidationError):
        SectionSentence(text="Unsupported.", claim_ids=[])
    with pytest.raises(ValidationError):
        SectionSentence(text="Twice.", claim_ids=[FIRST, FIRST])


def test_a_section_names_a_known_field_and_has_a_sentence() -> None:
    with pytest.raises(ValidationError):
        history()
    with pytest.raises(ValidationError):
        ArticleSection.model_validate(
            {
                "subjectKind": "craft",
                "subjectSlug": "Kutch-Ajrakh",
                "field": "ASTROLOGY",
                "version": 1,
                "status": "PROPOSED",
                "sentences": [{"text": "x", "claimIds": [str(FIRST)]}],
            }
        )


def test_a_stored_section_row_reads_back_by_its_aliases() -> None:
    section = history(SectionSentence(text="One.", claim_ids=[FIRST]))
    stored = section.model_dump(mode="json")
    assert stored["sentences"] == [{"text": "One.", "claimIds": [str(FIRST)]}]
    assert ArticleSection.model_validate(stored) == section
