from typing import Any

import pytest
from pydantic import ValidationError

from app.research.knowledge_writes import FACT_TASK_KINDS, FactProposal

from .fakes import PAGE_URL, QUOTE, STATEMENT


def proposal(task_key: str | None, **changes: Any) -> FactProposal:
    body: dict[str, Any] = {
        "subject": {"kind": "craft", "slug": "Kutch-Ajrakh"},
        "field": "PROCESS",
        "fields": ["CHEMISTRY"],
        "statement": STATEMENT,
        "sources": [{"url": PAGE_URL, "title": "Indigo in Ajrakh", "quotes": [{"text": QUOTE}]}],
        "taskKey": task_key,
    }
    return FactProposal.model_validate(body | changes)


def test_a_fact_completes_only_field_and_corroboration_tasks() -> None:
    assert FACT_TASK_KINDS == ("MISSING_FIELD", "THIN_FIELD", "SECOND_SOURCE", "SOURCES_DIFFER")


@pytest.mark.parametrize(
    "key",
    [
        "MISSING_FIELD:craft:Kutch-Ajrakh:PROCESS",
        "THIN_FIELD:craft:Kutch-Ajrakh:CHEMISTRY",
        "THIN_FIELD:family:Kutch-Ajrakh:PROCESS",
        "SECOND_SOURCE:craft:Kutch-Ajrakh:PROCESS",
        "SECOND_SOURCE:craft:Kutch-Ajrakh",
        "SOURCES_DIFFER:craft:Kutch-Ajrakh",
    ],
)
def test_a_task_of_the_same_page_and_one_of_the_fact_s_fields_is_taken(key: str) -> None:
    assert proposal(key).task_key == key


def test_without_a_task_key_nothing_is_completed() -> None:
    assert proposal(None).task_key is None


@pytest.mark.parametrize(
    ("key", "said"),
    [
        ("MISSING_COMPONENT:craft:Kutch-Ajrakh:map", "is not a task a fact completes"),
        ("SECTION:craft:Kutch-Ajrakh:PROCESS", "is not a task a fact completes"),
        ("DEAD_SOURCE:craft:Kutch-Ajrakh", "is not a task a fact completes"),
        ("THIN_FIELD:craft:Bagh-Print:PROCESS", "is a task of another page"),
        ("THIN_FIELD:category:Kutch-Ajrakh:PROCESS", "is a task of another page"),
        ("THIN_FIELD:craft:Kutch-Ajrakh:HISTORY", "asks for HISTORY"),
        ("MISSING_FIELD:craft:Kutch-Ajrakh", "names no field"),
        ("REVIEW:FACTS", "is not a task a fact completes"),
        ("NO_SUCH_KIND:craft:Kutch-Ajrakh", "is not a task key"),
    ],
)
def test_a_task_the_fact_cannot_complete_is_refused_before_any_gate(key: str, said: str) -> None:
    with pytest.raises(ValidationError, match=said):
        proposal(key)


def test_a_category_fact_takes_only_a_category_task() -> None:
    category = {"subject": {"kind": "category", "slug": "textiles"}}
    assert proposal("THIN_FIELD:category:textiles:PROCESS", **category).task_key is not None
    with pytest.raises(ValidationError, match="another page"):
        proposal("THIN_FIELD:craft:textiles:PROCESS", **category)
