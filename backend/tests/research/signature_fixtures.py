from typing import Any

__all__ = ["SIGNATURE_DECLARED", "cited"]

CLAIM = "826c1d72-9373-59f0-85c3-6bb38aa89320"
SOURCE = "d0f53ee9-4b97-5df7-a367-686957bdb7c8"


def cited(sentence_id: str, text: str, *, level: str = "PROVISIONAL") -> dict[str, Any]:
    return {
        "id": sentence_id,
        "text": text,
        "level": level,
        "citations": [
            {
                "id": "bf7fda76-2629-5609-ac54-d4c011fbb573",
                "claimId": CLAIM,
                "sourceId": SOURCE,
                "quote": text,
                "locator": None,
                "context": None,
                "evidence": "QUOTED",
                "level": level,
            }
        ],
        "translated": False,
        "terms": [],
    }


SIGNATURE_DECLARED: dict[str, dict[str, Any]] = {
    "indigo_vat": {
        "vat": "FERMENTED",
        "lift": cited(
            "v.1", "At first bright green, the cloth rapidly becomes blue as oxygen meets the dye."
        ),
        "forms": [
            {
                "form": "KETO",
                "name": "indigo",
                "colour": "blue",
                "soluble": False,
                "compound": None,
                "sentence": cited("v.2", "The blue indigo does not dissolve in water."),
            },
            {
                "form": "LEUCO",
                "name": "leucoindigo",
                "colour": "yellow",
                "soluble": True,
                "compound": None,
                "sentence": cited("v.3", "Its reduced form, leucoindigo, is yellow and dissolves in water."),
            },
        ],
        "dips": [
            {
                "dips": 3,
                "stated": "three or four",
                "shade": "darkest",
                "sentence": cited("v.4", "The darkest blue needs three or four dips in the vat."),
            }
        ],
        "contents": [
            {
                "name": "dates",
                "sentence": cited("v.5", "Natural indigo is fermented with lime, dates and soda."),
            }
        ],
    },
    "mordant_bath": {
        "dye": "madder",
        "fibre": "cotton",
        "swatches": [
            {
                "mordant": None,
                "colour": "pink",
                "sentence": cited("m.1", "Cotton dyed in madder with no mordant turns pink and washes out."),
            },
            {
                "mordant": "alum",
                "colour": "red",
                "sentence": cited("m.2", "With alum, madder dyes cotton red."),
            },
            {
                "mordant": "iron",
                "colour": "black",
                "sentence": cited("m.3", "With iron, the madder bath turns the cloth black."),
            },
        ],
    },
    "lost_wax": {
        "metal": "brass",
        "steps": [
            {"step": "MODEL", "sentence": cited("w.1", "A wax model is shaped over a clay core.")},
            {"step": "POUR", "sentence": cited("w.2", "Molten brass is poured into the mould.")},
        ],
    },
    "firing": {
        "body": "clay",
        "atmospheres": [
            {
                "atmosphere": "OXIDISING",
                "colour": "red",
                "sentence": cited("f.1", "Fired with plenty of air, the clay turns red."),
            },
            {
                "atmosphere": "REDUCING",
                "colour": "black",
                "sentence": cited("f.2", "Starved of air in the kiln, the clay turns black."),
            },
        ],
        "temperature": {"stated": "800 degrees", "sentence": cited("f.3", "The kiln reaches 800 degrees.")},
    },
}
