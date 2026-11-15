from __future__ import annotations

from common import REPO

IMMERSIVE_ROOT = REPO.parent / "immersive-episteme" / "content"
INFERENTIAL_ROOT = REPO.parent / "inferential-system" / "data" / "seed"

IMMERSIVE_TO_MASTER: dict[str, str] = {
    "ajrakh": "Kutch-Ajrakh",
    "bagh": "Bagh-Prints-Of-Madhya-Pradesh",
    "bagru": "Bagru-Hand-Block-Print",
    "dabu": "Block-Printing-Of-Akola",
    "machilipatnam-kalamkari": "Machilipatnam-Kalamkari",
    "sanganeri": "Sanganeri-Hand-Block-Printing",
}

SHARED_SCIENCE_SUB_CATEGORY = "Hand-Block-Printing"

INFERENTIAL_TO_SUB_CATEGORY: dict[str, str] = {
    "block-printing": "Hand-Block-Printing",
    "terracotta": "Terracotta-Pottery-Works",
    "wood-carving": "Wood-Carving",
}
