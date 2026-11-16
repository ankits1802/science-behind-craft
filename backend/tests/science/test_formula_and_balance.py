import pytest

from app.core.errors import InvalidInput
from app.science.balance import CHECKER_VERSION, ProposedSpecies, balance, composition_matrix
from app.science.formula import hill_formula, parse_formula
from app.science.reactions import CheckedReaction, SpeciesProposal, check_reaction

R, P = "REACTANT", "PRODUCT"


def species(*pairs: tuple[str, str]) -> list[ProposedSpecies]:
    return [ProposedSpecies(role, formula) for role, formula in pairs]


@pytest.mark.parametrize(
    ("text", "counts", "charge"),
    [
        ("Fe(CH3COO)2", {"C": 4, "Fe": 1, "H": 6, "O": 4}, 0),
        ("Al2Si2O5(OH)4", {"Al": 2, "H": 4, "O": 9, "Si": 2}, 0),
        ("KAl(SO4)2·12H2O", {"Al": 1, "H": 24, "K": 1, "O": 20, "S": 2}, 0),
        ("CuSO4.5H2O", {"Cu": 1, "H": 10, "O": 9, "S": 1}, 0),
        ("[Fe(CN)6]^4-", {"C": 6, "Fe": 1, "N": 6}, -4),
        ("Al^3+", {"Al": 1}, 3),
        ("H^+", {"H": 1}, 1),
        ("SO4^2-", {"O": 4, "S": 1}, -2),
        ("e^-", {}, -1),
    ],
)
def test_formulas_are_counted_by_hand(text: str, counts: dict[str, int], charge: int) -> None:
    formula = parse_formula(text)
    assert (dict(formula.counts), formula.charge) == (counts, charge)


@pytest.mark.parametrize("text", ["", "Xx2", "Fe(CH3COO", "Fe)2", "H0", "fe", "C6H12O6^0+", "()", "e"])
def test_a_malformed_formula_is_refused(text: str) -> None:
    with pytest.raises(InvalidInput):
        parse_formula(text)


def test_hill_order_puts_carbon_and_hydrogen_first() -> None:
    assert hill_formula(parse_formula("Fe(CH3COO)2")) == "C4H6FeO4"
    assert hill_formula(parse_formula("KAl(SO4)2·12H2O")) == "AlH24KO20S2"
    assert hill_formula(parse_formula("C14H8O4")) == "C14H8O4"


@pytest.mark.parametrize(
    ("pairs", "coefficients"),
    [
        (((R, "Fe"), (R, "CH3COOH"), (P, "Fe(CH3COO)2"), (P, "H2")), (1, 2, 1, 1)),
        (((R, "Al2Si2O5(OH)4"), (P, "Al2Si2O7"), (P, "H2O")), (1, 1, 2)),
        (((R, "C16H12N2O2"), (R, "O2"), (P, "C16H10N2O2"), (P, "H2O")), (2, 1, 2, 2)),
        (((R, "C16H10N2O2"), (R, "H^+"), (R, "e^-"), (P, "C16H12N2O2")), (1, 2, 2, 1)),
        (((R, "KAl(SO4)2·12H2O"), (P, "K^+"), (P, "Al^3+"), (P, "SO4^2-"), (P, "H2O")), (1, 1, 1, 2, 12)),
        (((R, "CH4"), (R, "O2"), (P, "CO2"), (P, "H2O")), (1, 2, 1, 2)),
    ],
)
def test_coefficients_match_the_hand_balanced_equation(
    pairs: tuple[tuple[str, str], ...], coefficients: tuple[int, ...]
) -> None:
    result = balance(species(*pairs))
    assert (result.outcome, result.coefficients, result.balanced) == ("BALANCED", coefficients, True)


def test_peroxide_from_water_alone_has_no_balance() -> None:
    assert balance(species((R, "H2O"), (P, "H2O2"))).outcome == "NO_SOLUTION"


def test_a_charge_left_unbalanced_has_no_balance() -> None:
    assert balance(species((R, "Fe"), (P, "Fe^2+"))).outcome == "NO_SOLUTION"


def test_carbon_burning_to_both_oxides_has_no_unique_balance() -> None:
    result = balance(species((R, "C"), (R, "O2"), (P, "CO"), (P, "CO2")))
    assert (result.outcome, result.coefficients, result.balanced) == ("NOT_UNIQUE", None, False)


def test_a_species_needed_on_the_other_side_is_not_balanced() -> None:
    assert balance(species((R, "H2"), (R, "H2O"), (P, "O2"))).outcome == "NOT_POSITIVE"


def test_a_species_that_takes_no_part_is_not_balanced() -> None:
    assert balance(species((R, "H2"), (R, "O2"), (P, "H2O"), (P, "He"))).outcome == "NOT_POSITIVE"


def test_a_reaction_needs_both_sides() -> None:
    with pytest.raises(InvalidInput, match="REACTANT and one PRODUCT"):
        balance(species((R, "H2"), (R, "O2")))


def test_the_element_matrix_signs_products_negative_and_adds_a_charge_row() -> None:
    formulas = [parse_formula(text) for text in ("H^+", "e^-", "H2")]
    assert composition_matrix([R, R, P], formulas) == [[1, 0, -2], [1, -1, 0]]


def test_model_coefficients_are_never_read() -> None:
    proposals = [
        SpeciesProposal(R, "Fe", "Iron"),
        SpeciesProposal(R, "CH3COOH", "Acetic acid"),
        SpeciesProposal(P, "Fe(CH3COO)2", "Iron(II) acetate"),
        SpeciesProposal(P, "H2", "Hydrogen"),
    ]
    checked = check_reaction(proposals)
    assert checked.coefficients == (1, 2, 1, 1)
    assert checked.checker_version == CHECKER_VERSION
    assert checked.equation_input == "Fe + CH3COOH -> Fe(CH3COO)2 + H2"
    assert checked.equation_balanced == "Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2"


def test_an_unbalanced_proposal_keeps_its_equation_and_no_checker() -> None:
    checked = check_reaction([SpeciesProposal(R, "H2O", None), SpeciesProposal(P, "H2O2", None)])
    assert (checked.balanced, checked.coefficients, checked.checker_version) == (False, None, None)
    assert (checked.equation_input, checked.equation_balanced) == ("H2O -> H2O2", None)


def test_a_species_without_a_formula_is_not_balanced_at_all() -> None:
    lake = [
        SpeciesProposal(R, "Al^3+", None),
        SpeciesProposal(R, "C14H8O4", "Alizarin"),
        SpeciesProposal(P, None, "Lake"),
    ]
    assert check_reaction(lake) == CheckedReaction(False, None, None, None, None)
