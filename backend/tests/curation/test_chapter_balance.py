import uuid

from app.research.blocks_matter import ReactionStep
from app.research.citations import Citation
from app.science.records import CompoundRecord
from app.services.chapter_balance import inferred_step, named_compounds

SOURCE = uuid.UUID(int=900)
INDIGO = CompoundRecord(uuid.UUID(int=1), "Indigo", "C16H10N2O2", 10215, SOURCE)
HYDROGEN = CompoundRecord(uuid.UUID(int=2), "Hydrogen", "H2", 783, SOURCE)
LEUCO = CompoundRecord(uuid.UUID(int=3), "Leucoindigo", "C16H12N2O2", 5462, uuid.UUID(int=901))
CITATION = Citation(
    id="c1",
    claim_id=str(uuid.UUID(int=50)),
    source_id="s1",
    quote="indigo is reduced to leucoindigo",
    locator=None,
    context=None,
    evidence="QUOTED",
    level="PROVISIONAL",
)


def word_step(*names: tuple[str, str]) -> ReactionStep:
    species = [
        {"role": role, "formula": None, "name": name, "coefficient": None, "compoundId": None}
        for role, name in names
    ]
    return ReactionStep.model_validate(
        {
            "reactionId": str(uuid.UUID(int=77)),
            "stageId": None,
            "kind": "REDOX",
            "label": "indigo to leucoindigo",
            "species": species,
            "equation": None,
            "balanced": False,
            "level": "PROVISIONAL",
            "citations": [CITATION.model_dump(by_alias=True)],
        }
    )


def test_a_word_reaction_whose_every_species_has_a_record_is_balanced_and_marked() -> None:
    named = named_compounds([INDIGO, HYDROGEN, LEUCO], {})
    step = inferred_step(
        word_step(("REACTANT", "indigo"), ("REACTANT", "hydrogen"), ("PRODUCT", "leucoindigo")), named
    )
    assert step.balanced and step.formula_basis == "COMPOUND_RECORD"
    assert [s.coefficient for s in step.species] == [1, 1, 1]
    assert step.formula_sources == [str(SOURCE), str(LEUCO.source_id)]
    assert step.equation is not None and "C16H12N2O2" in step.equation


def test_a_species_without_a_record_leaves_the_stored_reaction_as_it_is() -> None:
    stored = word_step(("REACTANT", "indigo"), ("REACTANT", "air"), ("PRODUCT", "leucoindigo"))
    assert inferred_step(stored, named_compounds([INDIGO, LEUCO], {})) == stored


def test_a_reaction_that_does_not_balance_is_left_as_stated() -> None:
    stored = word_step(("REACTANT", "indigo"), ("PRODUCT", "leucoindigo"))
    assert inferred_step(stored, named_compounds([INDIGO, LEUCO], {})) == stored
