from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.providers.catalogue import model_for
from app.providers.catalogue_types import AiProvider

__all__ = [
    "CACHE_READ_FACTOR",
    "CACHE_WRITE_FACTOR",
    "CAP_CEILING_USD",
    "CAP_DEFAULT_USD",
    "Budget",
    "Prices",
    "UnknownPrice",
    "dollars",
    "prices_for",
    "turn_cost",
]

MILLION = Decimal(1_000_000)
CACHE_WRITE_FACTOR = Decimal("1.25")
CACHE_READ_FACTOR = Decimal("0.1")
CAP_CEILING_USD = Decimal(40)
CAP_DEFAULT_USD = Decimal(25)
CATALOGUE = "backend/app/providers/catalogue_specs.py"


class UnknownPrice(ValueError):
    pass


@dataclass(frozen=True)
class Prices:
    model: str
    input_per_mtok: Decimal
    output_per_mtok: Decimal


@dataclass
class Budget:
    cap: Decimal
    spent: Decimal = Decimal(0)
    last: Decimal = Decimal(0)

    def charge(self, cost: Decimal) -> None:
        self.spent += cost
        self.last = cost

    def affords_next(self) -> bool:
        return self.spent + self.last < self.cap


def prices_for(model: str, day: date) -> Prices:
    found = model_for(AiProvider.ANTHROPIC, model)
    price = found.token_price_on(day) if found is not None else None
    if price is None:
        raise UnknownPrice(
            f"the provider catalogue holds no token price for {model}; add the model to {CATALOGUE}"
        )
    return Prices(model, Decimal(str(price[0])), Decimal(str(price[1])))


def turn_cost(usage: Mapping[str, Any], prices: Prices) -> Decimal:
    plain = _tokens(usage, "input_tokens")
    written = _tokens(usage, "cache_creation_input_tokens")
    read = _tokens(usage, "cache_read_input_tokens")
    output = _tokens(usage, "output_tokens")
    paid_input = plain + written * CACHE_WRITE_FACTOR + read * CACHE_READ_FACTOR
    return (paid_input * prices.input_per_mtok + output * prices.output_per_mtok) / MILLION


def dollars(amount: Decimal) -> str:
    return f"${amount.quantize(Decimal('0.01'))}"


def _tokens(usage: Mapping[str, Any], name: str) -> Decimal:
    value = usage.get(name)
    if value is None:
        return Decimal(0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"the API reported {name} as {value!r}, not a count of tokens")
    return Decimal(value)
