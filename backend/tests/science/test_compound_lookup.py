import pytest

from app.core.errors import InvalidInput
from app.services.compound_lookup import find_compound
from app.sources.reference.pubchem import PubChemAdapter, PubChemCompound

from ..sources.recorded import Recorder, Reply, fixed_clock, source_http

PUG = "pubchem.ncbi.nlm.nih.gov/rest/pug"
PROPERTIES = "property/Title,MolecularFormula,MolecularWeight,IUPACName,InChIKey,SMILES/JSON"


def compound(cid: int, title: str, formula: str) -> PubChemCompound:
    return PubChemCompound(cid, title, formula, None, None, None, None)


class FakeFinder:
    def __init__(
        self, answers: dict[str, list[PubChemCompound]], records: dict[int, PubChemCompound] | None = None
    ) -> None:
        self.answers = answers
        self.records = records or {}
        self.asked: list[str] = []

    async def compounds(self, text: str, k: int) -> list[PubChemCompound]:
        self.asked.append(text)
        return self.answers.get(text, [])[:k]

    async def compound(self, cid: int) -> PubChemCompound | None:
        self.asked.append(f"cid:{cid}")
        return self.records.get(cid)


def pubchem(routes: dict) -> PubChemAdapter:
    return PubChemAdapter(source_http(Recorder(routes), "pubchem"), clock=fixed_clock())


async def test_a_name_match_with_another_composition_falls_back_to_the_formula() -> None:
    finder = FakeFinder(
        {
            "Potassium alum": [compound(24856, "Aluminum potassium sulfate", "AlKO8S2")],
            "AlH24KO20S2": [compound(62667, "Potassium alum dodecahydrate", "AlH24KO20S2")],
        }
    )
    found = await find_compound(finder, name="Potassium alum", formula="KAl(SO4)2·12H2O")
    assert (found.cid, finder.asked) == (62667, ["Potassium alum", "AlH24KO20S2"])


async def test_no_candidate_of_the_same_composition_is_not_found() -> None:
    finder = FakeFinder({"Iron(II) acetate": [compound(10, "Iron(III) acetate", "C6H9FeO6")]})
    assert await find_compound(finder, name="Iron(II) acetate", formula="Fe(CH3COO)2") is None


async def test_an_ion_is_not_looked_up() -> None:
    with pytest.raises(InvalidInput, match="ion"):
        await find_compound(FakeFinder({}), name="Aluminium", formula="Al^3+")


async def test_alizarin_is_found_by_name_through_the_pubchem_adapter() -> None:
    adapter = pubchem(
        {
            f"{PUG}/compound/name/alizarin/cids/JSON": [
                Reply("pubchem_name_cids.json"),
                Reply("pubchem_word_cids.json"),
            ],
            f"{PUG}/compound/cid/6293,3955344,20431/{PROPERTIES}": Reply("pubchem_properties.json"),
        }
    )
    found = await find_compound(adapter, name="alizarin", formula="C14H8O4")
    assert (found.cid, found.title, found.inchikey) == (6293, "Alizarin", "RGCKGOZRHPZPFP-UHFFFAOYSA-N")
    assert found.url == "https://pubchem.ncbi.nlm.nih.gov/compound/6293"


async def test_an_unknown_name_is_found_by_its_hill_formula_through_the_pubchem_adapter() -> None:
    adapter = pubchem(
        {
            f"{PUG}/compound/name/madder%20red/cids/JSON": [
                Reply("pubchem_not_found.json", status=404),
                Reply("pubchem_not_found.json", status=404),
            ],
            f"{PUG}/compound/fastformula/C14H8O4/cids/JSON": Reply("pubchem_formula_cids.json"),
            f"{PUG}/compound/cid/6293,2950/{PROPERTIES}": Reply("pubchem_formula_properties.json"),
        }
    )
    found = await find_compound(adapter, name="madder red", formula="C14H8O4")
    assert (found.cid, found.formula) == (6293, "C14H8O4")


async def test_a_known_record_is_read_by_its_cid_through_the_pubchem_adapter() -> None:
    adapter = pubchem({f"{PUG}/compound/cid/6293/{PROPERTIES}": Reply("pubchem_properties.json")})
    found = await adapter.compound(6293)
    assert (found.cid, found.title, found.formula) == (6293, "Alizarin", "C14H8O4")


async def test_a_record_pubchem_does_not_hold_is_none() -> None:
    adapter = pubchem({f"{PUG}/compound/cid/9/{PROPERTIES}": Reply("pubchem_not_found.json", status=404)})
    assert await adapter.compound(9) is None
