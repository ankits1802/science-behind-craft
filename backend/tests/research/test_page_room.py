import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.api.mcp_page_arguments import DraftAdd, PageWork
from app.research.page_drafts import DRAFT_BYTES_MAX, DraftAddition, DraftParts, draft_bundle, with_added
from app.research.page_proposals import (
    COMPONENTS_MAX,
    COMPONENTS_PER_CALL_MAX,
    FACTS_MAX,
    FACTS_PER_CALL_MAX,
    PageBundle,
    PageSubject,
    fact_index,
    one_call_problem,
)

from .test_page_proposals import COMPONENT, FACT, SUBJECT

AJRAKH_SPECS = Path(__file__).resolve().parents[2] / "app" / "data" / "monographs" / "Kutch-Ajrakh" / "specs"
AJRAKH_COMPONENTS = 80
AJRAKH_CITED_FACTS = 183


def fact(n: int) -> dict[str, Any]:
    return {**FACT, "statement": f"Alum fixes the madder red on the cotton in bath {n}."}


def component(n: int, ref: str = "fact:0") -> dict[str, Any]:
    proposal = {**COMPONENT, "label": f"kutch-ajrakh/chemistry/alum-table-{n}"}
    return {"proposal": proposal, "cites": {"u0006": [ref]}}


def grown(facts: int, components: int) -> DraftParts:
    held = DraftParts()
    for start in range(0, facts, FACTS_PER_CALL_MAX):
        batch = [fact(n) for n in range(start, min(start + FACTS_PER_CALL_MAX, facts))]
        held = with_added(held, DraftAddition.model_validate({"facts": batch}))
    for start in range(0, components, COMPONENTS_PER_CALL_MAX):
        batch = [component(n) for n in range(start, min(start + COMPONENTS_PER_CALL_MAX, components))]
        held = with_added(held, DraftAddition.model_validate({"components": batch}))
    return held


def test_a_draft_grows_over_calls_to_hold_a_page_as_rich_as_kutch_ajrakh() -> None:
    held = grown(AJRAKH_CITED_FACTS, AJRAKH_COMPONENTS)
    assert (len(held.facts), len(held.components)) == (AJRAKH_CITED_FACTS, AJRAKH_COMPONENTS)
    bundle = draft_bundle(PageSubject.model_validate(SUBJECT), held)
    assert len(bundle.components) == AJRAKH_COMPONENTS and len(bundle.facts) == AJRAKH_CITED_FACTS


def test_a_draft_still_stops_at_its_total_bound() -> None:
    full = grown(FACTS_MAX, COMPONENTS_MAX)
    with pytest.raises(ValidationError, match=f"at most {COMPONENTS_MAX} items"):
        with_added(full, DraftAddition.model_validate({"components": [component(COMPONENTS_MAX)]}))
    with pytest.raises(ValidationError, match=f"at most {FACTS_MAX} items"):
        with_added(full, DraftAddition.model_validate({"facts": [fact(FACTS_MAX)]}))


def test_a_fact_is_named_by_its_place_up_to_the_draft_s_last_fact() -> None:
    held = grown(FACTS_MAX, 0)
    last = f"fact:{FACTS_MAX - 1}"
    cited = with_added(held, DraftAddition.model_validate({"components": [component(0, last)]}))
    assert cited.components[0].cites == {"u0006": [last]} and fact_index(last) == FACTS_MAX - 1
    assert fact_index("fact:1000") is None
    with pytest.raises(ValidationError, match="should match pattern"):
        DraftAddition.model_validate({"components": [component(0, "fact:1000")]})


def test_one_call_adds_at_most_its_own_bound() -> None:
    assert len(DraftAdd.model_validate({"components": [component(n) for n in range(10)]}).components) == 10
    with pytest.raises(ValidationError, match=f"at most {COMPONENTS_PER_CALL_MAX} items"):
        DraftAdd.model_validate({"components": [component(n) for n in range(COMPONENTS_PER_CALL_MAX + 1)]})
    with pytest.raises(ValidationError, match=f"at most {FACTS_PER_CALL_MAX} items"):
        DraftAdd.model_validate({"facts": [fact(n) for n in range(FACTS_PER_CALL_MAX + 1)]})


def test_a_bundle_sent_whole_holds_what_one_call_adds_and_a_draft_s_bundle_holds_the_page() -> None:
    small = {"subject": SUBJECT, "facts": [fact(0)], "components": [component(n) for n in range(10)]}
    assert PageWork.model_validate({"bundle": small}).bundle is not None
    large = {**small, "components": [component(n) for n in range(COMPONENTS_PER_CALL_MAX + 1)]}
    assert len(PageBundle.model_validate(large).components) == COMPONENTS_PER_CALL_MAX + 1
    with pytest.raises(ValidationError, match="a larger page is built in a draft"):
        PageWork.model_validate({"bundle": large})


def test_the_one_call_bound_names_each_part_past_it() -> None:
    assert one_call_problem({"components": COMPONENTS_PER_CALL_MAX, "facts": FACTS_PER_CALL_MAX}) is None
    said = one_call_problem({"components": COMPONENTS_PER_CALL_MAX + 1, "facts": FACTS_PER_CALL_MAX + 1})
    assert said is not None
    assert (
        f"at most {COMPONENTS_PER_CALL_MAX} components" in said
        and f"at most {FACTS_PER_CALL_MAX} facts" in said
    )


def test_every_kutch_ajrakh_spec_fits_in_one_draft_with_room_to_spare() -> None:
    compact = [
        len(json.dumps(json.loads(path.read_text(encoding="utf-8")), separators=(",", ":")).encode("utf-8"))
        for path in AJRAKH_SPECS.glob("*.json")
    ]
    assert len(compact) == AJRAKH_COMPONENTS and max(compact) > 200_000
    assert 2 * sum(compact) < DRAFT_BYTES_MAX
