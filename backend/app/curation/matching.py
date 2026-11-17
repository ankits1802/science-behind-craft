from __future__ import annotations

from collections.abc import Iterable

from app.research.quotes import normalise_quote_text, occurs_in_key, quote_key

__all__ = ["match_key", "quote_chars", "quote_found", "stated_in"]


def match_key(text: str) -> str:
    return quote_key(text.casefold())


def quote_found(quote: str, key: str) -> bool:
    return occurs_in_key(quote.casefold(), key)


def stated_in(words: str, texts: Iterable[str]) -> bool:
    return any(quote_found(words, match_key(text)) for text in texts)


def quote_chars(quote: str) -> int:
    return len(normalise_quote_text(quote))
