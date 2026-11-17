from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from app.research.evidence import personal_data_in

from .dossier import Dossier
from .problems import Problem

__all__ = ["LINK_KEYS", "TRACKING_PARAMETERS", "link_problem", "personal_data_problems", "source_problems"]

LINK_KEYS = frozenset({"url", "archivedUrl", "pageUrl", "licenceUrl", "doi"})
TRACKING_PARAMETERS = re.compile(
    r"^(?:utm_\w+|fbclid|gclid|dclid|msclkid|mc_cid|mc_eid|igshid|_ga)$", re.IGNORECASE
)
SEARCH_PAGES = (
    re.compile(r"(?:^|\.)google\.[a-z.]+$"),
    re.compile(r"(?:^|\.)bing\.com$"),
    re.compile(r"(?:^|\.)duckduckgo\.com$"),
    re.compile(r"(?:^|\.)search\.yahoo\.com$"),
    re.compile(r"(?:^|\.)yandex\.[a-z.]+$"),
)
SEARCH_PATHS = ("/search", "/scholar", "/url", "/html")


def source_problems(dossier: Dossier) -> list[Problem]:
    cited = {quote.source_id for claim in dossier.claims for quote in claim.quotes}
    found = [
        Problem(source.id, "no claim quotes it; drop it and keep the search under searched")
        for source in dossier.sources
        if source.id not in cited
    ]
    for source in dossier.sources:
        problem = link_problem(source.url)
        if problem is not None:
            found.append(Problem(source.id, problem))
    return found


def link_problem(url: str) -> str | None:
    parts = urlsplit(url)
    tracking = [
        name for name, _ in parse_qsl(parts.query, keep_blank_values=True) if TRACKING_PARAMETERS.match(name)
    ]
    if tracking:
        return f"the URL carries tracking parameters ({', '.join(tracking)}); cite the canonical page"
    host = (parts.hostname or "").casefold()
    if any(pattern.search(host) for pattern in SEARCH_PAGES) and parts.path.startswith(SEARCH_PATHS):
        return "the URL is a search result or redirect; cite the page itself"
    return None


def personal_data_problems(dossier: Dossier) -> list[Problem]:
    plain = dossier.model_dump(mode="json", by_alias=True)
    return [
        Problem(where, f"carries personal data ({', '.join(labels)})")
        for where, text in _texts(plain, "")
        if (labels := personal_data_in(text))
    ]


def _texts(value: Any, where: str) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield where or "dossier", value
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in LINK_KEYS:
                yield from _texts(item, f"{where}.{key}" if where else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _texts(item, f"{where}.{index}")
