import pytest

from app.research.knowledge_pieces import KnowledgePiece, reuse_refusal

from ..contracts.test_knowledge_piece_contract import ask, piece_body


def styled_piece(style: str | None) -> KnowledgePiece:
    return KnowledgePiece.model_validate(piece_body() | {"readingStyle": style})


@pytest.mark.parametrize(
    ("stored", "asked", "reason"),
    [
        ("TEEN", "TEEN", None),
        ("TEEN", None, "STYLE"),
        ("TEEN", "CHILD", "STYLE"),
        (None, "CHILD", "STYLE"),
        (None, None, None),
    ],
)
def test_a_composed_section_is_reused_only_by_a_reader_of_its_style(
    stored: str | None, asked: str | None, reason: str | None
) -> None:
    piece = styled_piece(stored)
    assert piece.kind == "prose"
    assert reuse_refusal(piece, ask(readingStyle=asked), set(piece.claim_ids)) == reason
