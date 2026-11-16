import math
import uuid

from app.models.crafts import EMBEDDING_DIMENSIONS
from app.services.craft_index import AliasRecord, CraftIndex, CraftRecord, SpellingRecord, build_index

HALF = 1 / math.sqrt(2)


def unit(*weights: float) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for i, weight in enumerate(weights):
        vector[i] = weight
    return vector


class FixedEmbedder:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = vector if vector is not None else unit(1.0)
        self.calls: list[list[str]] = []

    async def __call__(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [self.vector for _ in texts]


def craft_id(slug: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"test-craft/{slug}")


KUTCH = craft_id("Kutch-Ajrakh")
BARMER = craft_id("Barmer-Ajrakh-Print")
BAGRU = craft_id("Bagru-Hand-Block-Print")
OLD_KUTCH = craft_id("Ajrakh-Printing-Of-Kutch")
NAMDA = craft_id("Namda-Felt")
OTHERS = craft_id("Others-Textile")
LUCKNOW = craft_id("Lucknow-Zardozi")
ZARI = craft_id("Zari-Zardozi")
PHULKARI = craft_id("Phulkari")

CRAFTS = (
    CraftRecord(KUTCH, "Kutch-Ajrakh", "Kutch Ajrakh", "ACTIVE", places=("Gujarat",)),
    CraftRecord(BARMER, "Barmer-Ajrakh-Print", "Barmer Ajrakh Print", "ACTIVE", places=("Rajasthan",)),
    CraftRecord(BAGRU, "Bagru-Hand-Block-Print", "Bagru Hand Block Print", "ACTIVE", places=("Rajasthan",)),
    CraftRecord(
        OLD_KUTCH, "Ajrakh-Printing-Of-Kutch", "Ajrakh Printing of Kutch", "MERGED", merged_into=KUTCH
    ),
    CraftRecord(NAMDA, "Namda-Felt", "Namda Felt", "LEGACY"),
    CraftRecord(OTHERS, "Others-Textile", "Others", "ACTIVE", is_catch_all=True),
    CraftRecord(LUCKNOW, "Lucknow-Zardozi", "Lucknow Zardozi", "ACTIVE", places=("Uttar Pradesh",)),
    CraftRecord(ZARI, "Zari-Zardozi", "Zari Zardozi", "ACTIVE", craft_code="zardozi"),
    CraftRecord(PHULKARI, "Phulkari", "Phulkari", "ACTIVE", places=("Punjab", "All India")),
)
ALIASES = (
    AliasRecord(KUTCH, "Ajrakh"),
    AliasRecord(BARMER, "Ajrakh"),
    AliasRecord(BAGRU, "Bagru"),
    AliasRecord(LUCKNOW, "Zardozi"),
)
SPELLINGS = (SpellingRecord("zardozi", "Zardozi"), SpellingRecord("zardozi", "Zardosi"))


def sample_index(*, embedded: int = 0) -> CraftIndex:
    return build_index(CRAFTS, ALIASES, SPELLINGS, embedded=embedded)
