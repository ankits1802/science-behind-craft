from __future__ import annotations

import copy
import types
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError
from pydantic.alias_generators import to_camel

from app.core.errors import InvalidInput

from .component_specs import checked_spec
from .component_specs_science import SPEC_MODELS_SCIENCE
from .component_specs_science_parts import Styled
from .component_specs_science_players import StageEntry
from .shown_text import ShownText

__all__ = [
    "SPEC_KEY_SEPARATOR",
    "SPEC_TEXT_TAG",
    "SpecText",
    "spec_texts",
    "with_spec_texts",
]

SPEC_KEY_SEPARATOR = "#"
SPEC_TEXT_TAG = "label"
MARK = "m"
CHILDREN = "c"
NATIVE_NAMES: Mapping[type[BaseModel], tuple[str, str]] = MappingProxyType({StageEntry: ("name", "local")})

Path = tuple[str | int, ...]


@dataclass(frozen=True)
class SpecText:
    key: str
    path: Path
    nodes: list[Any]
    rich: bool


def spec_texts(label: str, kind: str, spec: Mapping[str, Any]) -> list[SpecText]:
    if kind not in SPEC_MODELS_SCIENCE:
        return []
    try:
        model = checked_spec(kind, spec)
    except InvalidInput, ValidationError:
        return []
    return [
        SpecText(key=_key(label, path), path=path, nodes=_nodes(value), rich=isinstance(value, list))
        for path, value in _shown(model, (), None, ())
    ]


def with_spec_texts(spec: Mapping[str, Any], given: Sequence[tuple[SpecText, list[Any]]]) -> dict[str, Any]:
    shown = copy.deepcopy(dict(spec))
    for text, nodes in given:
        _place(shown, text.path, _rich(nodes) if text.rich else "".join(str(node) for node in nodes))
    return shown


def _shown(value: Any, path: Path, annotation: Any, metadata: Sequence[Any]) -> Iterator[tuple[Path, Any]]:
    if value is None:
        return
    if _marked(annotation, metadata) and isinstance(value, str | list):
        yield path, value
    elif isinstance(value, BaseModel):
        skipped = _native_name(value)
        for name, info in type(value).model_fields.items():
            if name == skipped:
                continue
            alias = info.alias or to_camel(name)
            yield from _shown(getattr(value, name), (*path, alias), info.annotation, info.metadata)
    elif isinstance(value, list):
        inner = _item(annotation)
        for at, item in enumerate(value):
            yield from _shown(item, (*path, at), inner, ())


def _native_name(model: BaseModel) -> str | None:
    named = NATIVE_NAMES.get(type(model))
    if named is None:
        return None
    field, flag = named
    return field if getattr(model, flag, False) else None


def _marked(annotation: Any, metadata: Sequence[Any]) -> bool:
    if any(isinstance(item, ShownText) for item in metadata):
        return True
    origin = get_origin(annotation)
    if origin is Annotated:
        base, *extra = get_args(annotation)
        return any(isinstance(item, ShownText) for item in extra) or _marked(base, ())
    if origin is Union or origin is types.UnionType:
        return any(_marked(arg, ()) for arg in get_args(annotation))
    return False


def _item(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is Annotated:
        return _item(get_args(annotation)[0])
    if origin is Union or origin is types.UnionType:
        return next((found for arg in get_args(annotation) if (found := _item(arg)) is not None), None)
    if origin is list:
        return get_args(annotation)[0]
    return None


def _nodes(value: str | list[Any]) -> list[Any]:
    if isinstance(value, str):
        return [value]
    return [part if isinstance(part, str) else {MARK: part.style, CHILDREN: [part.text]} for part in value]


def _rich(nodes: Sequence[Any]) -> list[Any]:
    out: list[Any] = []
    for node in nodes:
        if isinstance(node, str):
            out.append(node)
        else:
            out.append(Styled(text="".join(node.get(CHILDREN, [])), style=node[MARK]).model_dump(mode="json"))
    return out


def _place(spec: Any, path: Path, value: Any) -> None:
    holder = spec
    for step in path[:-1]:
        holder = _step(holder, step)
        if holder is None:
            return
    last = path[-1]
    if (isinstance(holder, dict) and isinstance(last, str) and last in holder) or (
        isinstance(holder, list) and isinstance(last, int) and last < len(holder)
    ):
        holder[last] = value


def _step(holder: Any, step: str | int) -> Any:
    if isinstance(holder, dict) and isinstance(step, str):
        return holder.get(step)
    if isinstance(holder, list) and isinstance(step, int) and step < len(holder):
        return holder[step]
    return None


def _key(label: str, path: Path) -> str:
    return f"{label}{SPEC_KEY_SEPARATOR}{'.'.join(str(step) for step in path)}"
