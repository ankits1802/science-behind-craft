import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from app.api.routes import crafts, learning_views, map_districts, map_layers, molecules, public, rivers, terms
from app.data.craft_master_loader import build_catalogue
from app.research.craft_compare import CraftComparison
from app.research.craft_page import CraftPage
from app.research.shared_science import SharedConcept, SharedScience
from app.services import craft_catalogue, knowledge_view
from app.services.river_store import BasinFile
from app.services.term_summaries import StoredTermLookup, TermLookup

from ..answering.fakes import translation
from ..contracts.golden import golden_json
from ..contracts.learning_golden import SHARED_SCIENCE, learning
from ..geo.golden_region import golden_layer_values, golden_listing, golden_region_records
from ..geo.test_district_view import records as district_records
from ..geo.test_river_routes import KEY, OUTLET, SHA, TOPOLOGY, FakeBucket
from ..science.golden_process import golden_records as process_records
from ..sources.recorded import recorded
from ..terms.fakes import CHECKED_AT, FakeResearch, FakeTermStore, golden_claims, kut_term
from ..voice.listen_fakes import MemoryObjects
from .summary_fixture import summary_fixture_records

__all__ = ["AJRAKH", "BAGRU", "OUTLET", "Asked", "stored_reads"]

AJRAKH = "Kutch-Ajrakh"
BAGRU = "Bagru-Hand-Block-Print"
POINTS = [
    {
        "key": "state-24",
        "name": "Gujarat",
        "latitude": 22.7,
        "longitude": 71.6,
        "total": 1,
        "crafts": [{"slug": AJRAKH, "name": "Kutch Ajrakh", "path": f"/crafts/{AJRAKH}"}],
    }
]
CRAFTS = {
    AJRAKH: SimpleNamespace(id=uuid.UUID(int=11), slug=AJRAKH, name="Kutch Ajrakh"),
    BAGRU: SimpleNamespace(id=uuid.UUID(int=12), slug=BAGRU, name="Bagru Hand Block Print"),
}


@dataclass
class Asked:
    acls: dict[str, set[tuple[str, ...]]] = field(default_factory=dict)

    def heard(self, name: str, acls: Sequence[str]) -> None:
        self.acls.setdefault(name, set()).add(tuple(acls))

    def loader(self, name: str, value: Any) -> Any:
        async def answer(*_args: Any, acls: Sequence[str], **_kwargs: Any) -> Any:
            self.heard(name, acls)
            return value

        return answer


@dataclass
class Conformers:
    sdf: str

    async def conformer(self, cid: int) -> str | None:
        return self.sdf if cid == 6293 else None


async def nothing(*_args: Any, **_kwargs: Any) -> None:
    return None


def returning(value: Any) -> Any:
    async def answer(*_args: Any, **_kwargs: Any) -> Any:
        return value

    return answer


def stored_reads(asked: Asked) -> dict[Any, dict[str, Any]]:
    return {
        **_craft_reads(asked),
        **_learning_reads(asked),
        **_map_reads(asked),
        **_media_reads(),
        **_term_reads(asked),
        public: {"summary_records": returning(summary_fixture_records())},
    }


def _craft_reads(asked: Asked) -> dict[Any, dict[str, Any]]:
    page = CraftPage.model_validate(golden_json("craft.page.golden.json"))

    async def resolve(_session: Any, slug: str) -> Any:
        return CRAFTS.get(slug)

    return {
        knowledge_view: {"resolve_craft": resolve, "map_points": returning(POINTS)},
        craft_catalogue: {"load_catalogue": returning(build_catalogue())},
        crafts: {
            "craft_page_records": asked.loader("craft_page_records", None),
            "craft_page": lambda _records: page,
            "region_records": returning(golden_region_records()),
            "process_records": asked.loader("process_records", process_records()),
        },
    }


def _learning_reads(asked: Asked) -> dict[Any, dict[str, Any]]:
    shared = learning(SHARED_SCIENCE)

    async def concept(
        _session: Any, term_key: str, _focus: Any, *, acls: Sequence[str]
    ) -> SharedConcept | None:
        asked.heard("shared_concept_of", acls)
        return SharedConcept.model_validate(shared["concept"]) if term_key == "alum" else None

    compared = CraftComparison.model_validate(golden_json("learning.compare.golden.json"))
    return {
        learning_views: {
            "craft_shared_science": asked.loader(
                "craft_shared_science", SharedScience.model_validate(shared["craft"])
            ),
            "shared_concept_of": concept,
            "craft_comparison": asked.loader("craft_comparison", compared),
        }
    }


def _map_reads(asked: Asked) -> dict[Any, dict[str, Any]]:
    return {
        map_layers: {
            "listed_layers": returning(golden_listing()),
            "layer_values": returning(golden_layer_values()),
        },
        map_districts: {"district_records": asked.loader("district_records", district_records())},
        rivers: {
            "basin_file": returning(BasinFile(main_riv=OUTLET, edition="v10", sha256=SHA)),
            "release_connection": nothing,
            "media_bucket": lambda: FakeBucket({KEY: TOPOLOGY}),
        },
    }


def _media_reads() -> dict[Any, dict[str, Any]]:
    sdf = recorded("pubchem_conformer.sdf").decode("ascii").strip()
    return {
        molecules: {
            "stored_compound_cid": returning(True),
            "release_connection": nothing,
            "media_bucket": MemoryObjects,
            "live_pubchem": returning(Conformers(sdf)),
            "sessionmaker": lambda: None,
        }
    }


def _term_reads(asked: Asked) -> dict[Any, dict[str, Any]]:
    store = FakeTermStore({"kut": kut_term()}, stored=golden_claims())

    def stored_terms(_sessions: Any, *, acls: Sequence[str]) -> StoredTermLookup:
        asked.heard("term_lookup", acls)
        return StoredTermLookup(store)

    async def signed_in_terms(*, acls: Sequence[str], **_kwargs: Any) -> TermLookup:
        asked.heard("term_lookup", acls)
        return TermLookup(
            store=store, research=FakeResearch(None), translation=translation(), clock=lambda: CHECKED_AT
        )

    return {
        terms: {
            "sessionmaker": lambda: None,
            "stored_term_lookup": stored_terms,
            "build_term_lookup": signed_in_terms,
        }
    }
