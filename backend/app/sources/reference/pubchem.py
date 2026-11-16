from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any
from urllib.parse import quote

from app.core.errors import ExternalFailure, InvalidInput
from app.research.evidence import EvidenceItem, SearchQuery, SourceDocument

from ..adapter import HttpSourceAdapter, build_document
from ..http import RatePolicy
from ..records import UnusableRecord, clean_text, title_of
from .pubchem_hazards import HazardReport, hazard_report

__all__ = ["PUBCHEM_LICENCE", "PUBCHEM_RATE", "PubChemAdapter", "is_formula"]

PUG_REST = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUG_VIEW = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound"
PUBCHEM_RATE = RatePolicy(min_interval=0.25)
PUBCHEM_LICENCE = "https://www.ncbi.nlm.nih.gov/home/about/policies/"
PUBCHEM_PUBLISHER = "National Library of Medicine"
PROPERTIES = ("Title", "MolecularFormula", "MolecularWeight", "IUPACName", "InChIKey", "SMILES")
PROPERTY_LINES = (
    ("MolecularFormula", "Molecular formula", ""),
    ("MolecularWeight", "Molecular weight", " g/mol"),
    ("IUPACName", "IUPAC name", ""),
    ("InChIKey", "InChIKey", ""),
    ("SMILES", "SMILES", ""),
)
FORMULA = re.compile(r"(?:[A-Z][a-z]?\d*){2,}|[A-Z][a-z]?\d+")
FORMULA_PART = re.compile(r"([A-Z][a-z]?)\d*")
ELEMENT_SYMBOLS = (
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
    "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm "
    "Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No "
    "Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og"
)
ELEMENTS = frozenset(ELEMENT_SYMBOLS.split())
NATIVE_ID = re.compile(r"^([1-9]\d{0,11})(:ghs)?$")
GHS_HEADING = "GHS Classification"


class PubChemAdapter(HttpSourceAdapter):
    name = "pubchem"

    async def _search_records(self, query: SearchQuery, k: int) -> list[Any]:
        cids = await self._matching_cids(query.text, k)
        if not cids:
            return []
        table = await self._properties(cids)
        return [table[cid] for cid in cids if cid in table]

    def _item(self, record: Any, retrieved_at: datetime) -> EvidenceItem:
        cid = str(record.get("CID") or "")
        if not cid.isdigit():
            raise UnusableRecord("no PubChem CID")
        external_ids = {"pubchem_cid": cid}
        inchikey = clean_text(record.get("InChIKey"))
        if inchikey:
            external_ids["inchikey"] = inchikey
        return EvidenceItem(
            id=f"{self.name}:{cid}",
            adapter=self.name,
            tier=self.tier,
            source_type="COMPOUND_RECORD",
            url=_compound_url(cid),
            title=title_of(record.get("Title") or record.get("IUPACName")),
            retrieved_at=retrieved_at,
            licence=PUBCHEM_LICENCE,
            attribution=f"PubChem, {PUBCHEM_PUBLISHER}, CID {cid}",
            publisher=PUBCHEM_PUBLISHER,
            trust="A",
            external_ids=external_ids,
        )

    async def _fetch_document(self, native: str, retrieved_at: datetime) -> SourceDocument:
        match = NATIVE_ID.match(native)
        if match is None:
            raise InvalidInput(f"{native!r} is not '<CID>' or '<CID>:ghs'")
        cid, hazards = match.groups()
        if hazards:
            return await self._hazard_document(cid, retrieved_at)
        table = await self._properties([cid])
        if cid not in table:
            raise self._not_found(native, "no compound")
        record = table[cid]
        return build_document(self._item(record, retrieved_at), _compound_text(record), "EXCERPT")

    async def _hazard_document(self, cid: str, retrieved_at: datetime) -> SourceDocument:
        response = await self._get_or_none(f"{PUG_VIEW}/{cid}/JSON", params={"heading": GHS_HEADING})
        report = hazard_report((response or {}).get("Record") or {})
        if report is None:
            raise self._not_found(f"{cid}:ghs", "no attributed GHS classification")
        return build_document(self._hazard_item(cid, report, retrieved_at), report.text(cid), "EXCERPT")

    def _hazard_item(self, cid: str, report: HazardReport, retrieved_at: datetime) -> EvidenceItem:
        first = report.sources[0]
        return EvidenceItem(
            id=f"{self.name}:{cid}:ghs",
            adapter=self.name,
            tier=self.tier,
            source_type="COMPOUND_RECORD",
            url=first.url or f"{PUG_VIEW}/{cid}/JSON?heading=GHS+Classification",
            title=f"{report.title}: GHS classification",
            retrieved_at=retrieved_at,
            licence=report.licence,
            attribution=f"{report.attribution}; via PubChem CID {cid}",
            publisher=first.name,
            trust="A",
            external_ids={"pubchem_cid": cid},
        )

    async def _matching_cids(self, text: str, k: int) -> list[str]:
        name = unicodedata.normalize("NFKC", text).strip()
        if is_formula(name):
            return (await self._cids(f"compound/fastformula/{name}/cids/JSON", {"MaxRecords": str(k)}))[:k]
        path = f"compound/name/{quote(name, safe='')}/cids/JSON"
        exact = await self._cids(path, {})
        words = await self._cids(path, {"name_type": "word"})
        return list(dict.fromkeys([*exact, *words]))[:k]

    async def _cids(self, path: str, params: dict[str, str]) -> list[str]:
        payload = await self._get_or_none(f"{PUG_REST}/{path}", params=params)
        listed = ((payload or {}).get("IdentifierList") or {}).get("CID") or []
        return [str(cid) for cid in listed if isinstance(cid, int) and cid > 0]

    async def _properties(self, cids: list[str]) -> dict[str, dict[str, Any]]:
        path = f"{PUG_REST}/compound/cid/{','.join(cids)}/property/{','.join(PROPERTIES)}/JSON"
        payload = await self._get_or_none(path, params={})
        rows = ((payload or {}).get("PropertyTable") or {}).get("Properties") or []
        return {str(row.get("CID")): row for row in rows}

    async def _get_or_none(self, url: str, *, params: dict[str, str]) -> dict[str, Any] | None:
        try:
            response = await self.http.get(url, params=params)
        except ExternalFailure as failure:
            if failure.status == 404:
                return None
            raise
        return response.json(self.name)


def is_formula(text: str) -> bool:
    candidate = unicodedata.normalize("NFKC", text).strip()
    if FORMULA.fullmatch(candidate) is None:
        return False
    return all(symbol in ELEMENTS for symbol in FORMULA_PART.findall(candidate))


def _compound_url(cid: str) -> str:
    return f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"


def _compound_text(record: dict[str, Any]) -> str:
    lines = [f"{title_of(record.get('Title') or record.get('IUPACName'))} (PubChem CID {record['CID']})"]
    for key, label, unit in PROPERTY_LINES:
        value = clean_text(str(record[key])) if record.get(key) is not None else None
        if value:
            lines.append(f"{label}: {value}{unit}")
    return "\n".join(lines)
