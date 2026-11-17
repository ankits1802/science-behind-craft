import dataclasses
import uuid

import pytest

from app.composer.what_if import WhatIfChoice
from app.research.blocks_play import WhatIfBlock
from app.science.records import ProcessRecords
from app.science.what_if_check import what_if_problems
from app.services.craft_matter import section_sentences
from app.services.piece_store import process_problems
from app.services.what_if_block import what_if_block
from app.services.what_if_offers import named_groups, what_if_inputs

from .fixtures import (
    ALIZARIN_ID,
    FIXTURE_REPLY,
    MADDER_ID,
    evidence,
    golden_what_if,
    red_ask,
    red_matter,
    red_records,
)

ELSEWHERE = uuid.uuid5(uuid.NAMESPACE_URL, "test-what-if/stage/elsewhere")


def built() -> WhatIfBlock:
    matter = red_matter()
    ask = red_ask()
    inputs = what_if_inputs(
        named_groups(matter, section_sentences(ask.blocks)), matter, evidence(), ask.cited
    )
    block = what_if_block(WhatIfChoice.model_validate(FIXTURE_REPLY), inputs, block_id="s2.b3")
    assert block is not None
    return block


def with_uses(records: ProcessRecords, chosen: uuid.UUID, **changes: object) -> ProcessRecords:
    uses = tuple(
        dataclasses.replace(use, **changes) if use.material_id == chosen else use for use in records.materials
    )
    return dataclasses.replace(records, materials=uses)


def test_a_what_if_built_from_the_rows_matches_them_through_the_piece_store() -> None:
    assert what_if_problems(built(), red_records()) == []
    assert process_problems(built(), red_records()) == []


def test_the_fixture_s_what_if_matches_the_seeded_rows_and_its_unstored_unknown_is_not_re_checked() -> None:
    golden = WhatIfBlock.model_validate(golden_what_if())
    assert what_if_problems(golden, red_records(al_root=False)) == []


@pytest.mark.parametrize(
    ("records", "message"),
    [
        (lambda r: with_uses(r, MADDER_ID, name="Rubia tinctorum"), "does not match its stored material"),
        (lambda r: with_uses(r, MADDER_ID, material_id=uuid.UUID(int=7)), "is not a stored material"),
        (lambda r: with_uses(r, MADDER_ID, stage_id=ELSEWHERE), "is not used at the stage"),
        (lambda r: dataclasses.replace(r, reactions=()), "which is not stored"),
        (
            lambda r: dataclasses.replace(r, reactions=(dataclasses.replace(r.reactions[0], citations=()),)),
            "cites no passage linked to reaction",
        ),
        (lambda r: with_uses(r, ALIZARIN_ID, compound=None), "holds no compound of option"),
        (lambda r: dataclasses.replace(r, stages=()), "not a stage of Kutch-Ajrakh"),
    ],
)
def test_a_stored_what_if_is_refused_once_its_rows_change(records: object, message: str) -> None:
    changed = records(red_records())
    assert any(message in problem for problem in what_if_problems(built(), changed))
    assert any(message in problem for problem in process_problems(built(), changed))


def test_a_glossary_option_cannot_be_re_checked_against_the_rows_and_is_refused() -> None:
    block = built()
    options = [block.options[0].model_copy(update={"material_id": None, "term_key": "indian-madder"})]
    termed = block.model_copy(update={"options": [*options, *block.options[1:]]})
    (problem,) = what_if_problems(termed, red_records())
    assert "glossary term" in problem
