from typing import Any

from app.research.citations import SourceRef
from app.research.explainer import Explainer
from app.services.field_voices_readback import (
    WITHDRAWN_SEARCHED,
    Withdrawn,
    portal_field_source,
    without_withdrawn,
)
from tests.contracts.golden import golden_json

GI = "d0f53ee9-4b97-5df7-a367-686957bdb7c8"
MUSEUM = "f0dde764-b68a-5ea6-8d1c-05ca4a7db2b7"
SECOND_MUSEUM = "84cc8e03-ef75-55a3-9fb6-ca8b8e872a93"
INTERVIEW = "907e2c52-14e7-5e41-9b27-9c10f70906a9"
GALLERY = "4ce205e3-653f-51db-9e49-14fb3b3f2e14"


def explainer(*interviews: str) -> Explainer:
    document = golden_json("explainer.document.golden.json")
    for source in document["sources"]:
        if source["id"] in interviews:
            source.update(kind="FIELD_TESTIMONY", publisher="Field Repository", authors=["Asha Demo"])
    return Explainer.model_validate(document)


def sentence_ids(shown: Explainer, section: str) -> list[str]:
    blocks = next(s for s in shown.sections if s.id == section).blocks
    return [sentence.id for block in blocks for sentence in getattr(block, "sentences", [])]


def first_citation(shown: Explainer, sentence: str) -> tuple[str, str]:
    for section in shown.sections:
        for block in section.blocks:
            for each in getattr(block, "sentences", []):
                if each.id == sentence:
                    return each.citations[0].claim_id, each.citations[0].source_id
    raise AssertionError(sentence)


def source_ids(shown: Explainer) -> list[str]:
    return [source.id for source in shown.sources]


def test_nothing_withdrawn_leaves_the_explainer_as_stored() -> None:
    stored = explainer(INTERVIEW)
    assert without_withdrawn(stored, Withdrawn()) is stored


def test_only_portal_interviews_are_checked_against_the_portals() -> None:
    stored = explainer(INTERVIEW)
    kinds: dict[str, Any] = {source.id: portal_field_source(source) for source in stored.sources}
    assert kinds == {GI: False, MUSEUM: False, SECOND_MUSEUM: False, INTERVIEW: True, GALLERY: False}
    testimony = SourceRef.model_validate(
        stored.sources[3].model_dump(mode="json", by_alias=True) | {"publisher": "KalaVigyan"}
    )
    assert not portal_field_source(testimony)


def test_a_withdrawn_interview_takes_its_sentences_and_its_source_out() -> None:
    shown = without_withdrawn(explainer(INTERVIEW), Withdrawn(sources=frozenset({INTERVIEW})))
    assert shown is not None
    assert sentence_ids(shown, "s2") == ["s2.b1.1", "s2.b1.2"]
    assert source_ids(shown) == [GI, MUSEUM, SECOND_MUSEUM, GALLERY]
    assert "Asha Demo" not in shown.model_dump_json()


def test_a_withdrawn_quote_takes_out_only_the_sentence_that_cited_it() -> None:
    stored = explainer(GI)
    cited = first_citation(stored, "s2.b1.1")
    shown = without_withdrawn(stored, Withdrawn(citations=frozenset({cited})))
    assert shown is not None
    assert sentence_ids(shown, "s2") == ["s2.b1.2", "s2.b1.3"]
    assert sentence_ids(shown, "s3") == ["s3.b1.1", "s3.b1.2", "s3.b1.3"]


def test_a_section_left_with_nothing_says_an_interview_is_no_longer_shown() -> None:
    shown = without_withdrawn(explainer(MUSEUM), Withdrawn(sources=frozenset({MUSEUM})))
    assert shown is not None
    first = shown.sections[0]
    assert (first.state, first.blocks, first.searched) == ("EMPTY", [], WITHDRAWN_SEARCHED)
    assert source_ids(shown) == [GI, INTERVIEW, GALLERY]


def test_an_explainer_resting_only_on_withdrawn_interviews_is_not_shown() -> None:
    withdrawn = Withdrawn(sources=frozenset({GI, INTERVIEW, GALLERY}))
    assert without_withdrawn(explainer(GI, INTERVIEW, GALLERY), withdrawn) is None
