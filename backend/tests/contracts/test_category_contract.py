from __future__ import annotations

import copy
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from app.research.category_page import CategoryList, CategoryPage, contract_text
from app.services.category_preview import category_list_preview, category_page_preview

from ..curation.category_support import (
    LEATHER,
    LEATHER_DOSSIER,
    LIST_GOLDEN,
    PAGE_GOLDEN,
    PAPER,
    UNCURATED_GOLDEN,
)
from .golden import golden_json, golden_text, reproduces

OUTSIDE = str(uuid.UUID(int=99))


def test_the_category_goldens_parse_and_match_the_response_models() -> None:
    assert reproduces(CategoryPage, PAGE_GOLDEN)
    assert reproduces(CategoryPage, UNCURATED_GOLDEN)
    assert reproduces(CategoryList, LIST_GOLDEN)


def test_the_curated_golden_is_the_leather_fixture_as_served() -> None:
    page = category_page_preview(LEATHER, dossier=LEATHER_DOSSIER)
    assert contract_text(page) == golden_text(PAGE_GOLDEN)


def test_the_uncurated_golden_is_the_paper_category_from_the_register() -> None:
    assert contract_text(category_page_preview(PAPER)) == golden_text(UNCURATED_GOLDEN)


def test_the_list_golden_is_the_register_with_the_leather_fixture() -> None:
    assert contract_text(category_list_preview([LEATHER_DOSSIER])) == golden_text(LIST_GOLDEN)


def refused(edit: Callable[[dict[str, Any]], None]) -> None:
    plain = copy.deepcopy(golden_json(PAGE_GOLDEN))
    edit(plain)
    with pytest.raises(ValidationError):
        CategoryPage.model_validate(plain)


def test_a_page_never_names_a_claim_or_source_it_does_not_list() -> None:
    refused(lambda page: page["overview"]["keyFacts"][0].update(claimIds=[OUTSIDE]))
    refused(lambda page: page["claims"][0]["citations"][0].update(sourceId=OUTSIDE))
    refused(lambda page: page["claims"].append(dict(page["claims"][0], id=OUTSIDE)))
    refused(lambda page: page["sources"].pop())


def test_sources_are_numbered_one_to_n_and_crafts_are_members() -> None:
    refused(lambda page: page["sources"][0].update(number=2))
    refused(lambda page: page["overview"]["lede"][1]["crafts"].append("Kutch-Ajrakh"))
    refused(lambda page: page["subCategories"][0].update(craftCount=4))
    refused(lambda page: page["subCategories"][1].update(openQuestion="O09"))
    refused(lambda page: page["hero"]["media"].update(title="Not one of the pictures"))


def test_a_sentence_rests_on_facts_and_the_header_matches_curation() -> None:
    refused(lambda page: page["overview"]["lede"][0].update(level="HYPOTHESIS"))
    refused(lambda page: page.update(curation=None))
    uncurated = copy.deepcopy(golden_json(UNCURATED_GOLDEN))
    uncurated["curated"] = True
    with pytest.raises(ValidationError):
        CategoryPage.model_validate(uncurated)


def test_a_list_carries_exactly_the_sources_its_ledes_cite() -> None:
    plain = copy.deepcopy(golden_json(LIST_GOLDEN))
    plain["sources"].append(dict(plain["sources"][0], id=OUTSIDE))
    with pytest.raises(ValidationError, match="exactly the sources"):
        CategoryList.model_validate(plain)
    plain = copy.deepcopy(golden_json(LIST_GOLDEN))
    paper = next(category for category in plain["categories"] if category["slug"] == PAPER)
    leather = next(category for category in plain["categories"] if category["slug"] == LEATHER)
    paper["lede"] = leather["lede"]
    with pytest.raises(ValidationError, match="not curated"):
        CategoryList.model_validate(plain)
