import pytest

from app.research.knowledge_pieces import KnowledgePiece, PieceSlot, knowledge_piece

from .owner_fixtures import curated_ajrakh
from .owner_runs import Owner, answered, kinds, owner, seeded_matter
from .piece_fakes import MemoryPieces

PLAYER = "reaction_player"


@pytest.fixture
def seed_matter(monkeypatch: pytest.MonkeyPatch) -> None:
    seeded_matter(monkeypatch, curated_ajrakh().process)


def current_players(pieces: MemoryPieces) -> list[KnowledgePiece]:
    return [piece for piece in pieces.current() if piece.kind == PLAYER]


def kept_again(run: Owner) -> set[str]:
    (_, _, sections) = run.pieces.kept[-1]
    return {section.facet for section in sections}


def researched(run: Owner) -> set[str]:
    return {request.focus or "" for request in run.pipeline.research.requests}


def played_only_first(pieces: MemoryPieces) -> None:
    (stored,) = current_players(pieces)
    player = stored.payload.model_copy(update={"steps": stored.payload.steps[:1], "notes": []})
    slot = PieceSlot(stored.craft_id, stored.facet, stored.topic_key, stored.depth)
    older = knowledge_piece(
        player,
        slot,
        piece_id=stored.id,
        answer_id=stored.created_from_answer_id,
        created_at=stored.created_at,
    )
    pieces.pieces = [older if piece.id == stored.id else piece for piece in pieces.pieces]


async def test_asking_again_reuses_the_first_answer_with_one_reaction_player(seed_matter: None) -> None:
    first = owner(golden=False)
    await answered(first)
    assert len(current_players(first.pieces)) == 1
    for depth in ("EXPERT", "EXPERT", "DETAILED"):
        again = owner(first.pieces, golden=False)
        explainer = await answered(again, depth)
        (chemistry,) = [section for section in explainer.sections if section.discipline == "CHEMISTRY"]
        assert any(block.reuse for block in chemistry.blocks) and "CHEMISTRY" not in researched(again)
        assert kinds(explainer)[PLAYER] == 1
        assert len(current_players(first.pieces)) == 1
        assert "CHEMISTRY" not in kept_again(again)


async def test_a_stored_player_that_plays_less_than_the_rows_is_replaced_and_kept_once(
    seed_matter: None,
) -> None:
    first = owner(golden=False)
    await answered(first)
    played_only_first(first.pieces)
    again = owner(first.pieces, golden=False)
    explainer = await answered(again)
    (player,) = [b for s in explainer.sections for b in s.blocks if b.kind == PLAYER]
    assert player.reuse is None and len(player.steps) > 1
    assert "CHEMISTRY" in kept_again(again)
    (kept,) = current_players(first.pieces)
    assert len(kept.payload.steps) == len(player.steps)
    third = owner(first.pieces, golden=False)
    assert kinds(await answered(third))[PLAYER] == 1
    assert "CHEMISTRY" not in kept_again(third)
