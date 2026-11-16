from datetime import UTC, datetime

from app.research.crafts import CraftRef
from app.research.evidence import EvidenceItem, Quote

AJRAKH = CraftRef(slug="Kutch-Ajrakh", name="Kutch Ajrakh", path="/crafts/Kutch-Ajrakh")
BAGRU = CraftRef(slug="Bagru-Print", name="Bagru Print", path="/crafts/Bagru-Print")
ALUM_QUOTE = Quote(text="alum forms a red lake with alizarin at about 60 °C", locator="p. 12")
RETRIEVED = datetime(2026, 11, 16, 9, 30, tzinfo=UTC)


def evidence_item(**changes: object) -> EvidenceItem:
    fields: dict[str, object] = {
        "id": "openalex:W2019",
        "adapter": "openalex",
        "tier": "T3",
        "sourceType": "PAPER",
        "url": "https://doi.org/10.1000/example.2019.1",
        "title": "Alizarin lakes on cotton",
        "authors": ["A. Author"],
        "published": "2019-07",
        "retrievedAt": RETRIEVED,
        "licence": "CC BY 4.0",
        "doi": "10.1000/Example.2019.1",
        "trust": "B",
        "quotes": [ALUM_QUOTE],
    }
    fields.update(changes)
    return EvidenceItem.model_validate(fields)
