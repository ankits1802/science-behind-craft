from __future__ import annotations

from typing import Final

__all__ = ["SHOWN_TEXT", "ShownText"]


class ShownText:
    __slots__ = ()

    def __repr__(self) -> str:
        return "ShownText()"


SHOWN_TEXT: Final = ShownText()
