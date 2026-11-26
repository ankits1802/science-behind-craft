from __future__ import annotations

import types
from collections.abc import Mapping
from functools import cache
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel, RootModel, ValidationError
from pydantic.fields import FieldInfo

from .component_specs import spec_model
from .component_specs_plates_parts import held_text

__all__ = ["text_units_resolved"]

UNIONS = (Union, types.UnionType)
SEQUENCES = (list, tuple)
MARK_CHILDREN = "c"
ROOT = "root"


def text_units_resolved(kind: str, spec: Mapping[str, Any], texts: Mapping[str, str]) -> dict[str, Any]:
    model = spec_model(kind, spec)
    if model is None:
        return dict(spec)
    return _model(spec, model, texts)


def _resolved(value: Any, annotation: Any, texts: Mapping[str, str], marks: tuple[Any, ...] = ()) -> Any:
    origin = get_origin(annotation)
    if origin is Annotated:
        base, *more = get_args(annotation)
        return _resolved(value, base, texts, (*marks, *more))
    if _held(marks):
        return _held_nodes(value, texts)
    if origin in UNIONS:
        fitting = [arm for arm in get_args(annotation) if _fits(value, arm)]
        return _resolved(value, fitting[0], texts, marks) if len(fitting) == 1 else value
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _model(value, annotation, texts)
    if origin in SEQUENCES and isinstance(value, list):
        (item, *_) = get_args(annotation) or (Any,)
        return [_resolved(found, item, texts) for found in value]
    if annotation is str and isinstance(value, str) and not any(_patterned(mark) for mark in marks):
        return texts.get(value, value)
    return value


def _model(value: Any, model: type[BaseModel], texts: Mapping[str, str]) -> Any:
    if issubclass(model, RootModel):
        root = model.model_fields[ROOT]
        return _resolved(value, root.annotation, texts, tuple(root.metadata))
    if not isinstance(value, Mapping):
        return value
    fields = _fields(model)
    return {
        key: _resolved(item, fields[key].annotation, texts, tuple(fields[key].metadata))
        if key in fields
        else item
        for key, item in value.items()
    }


@cache
def _fields(model: type[BaseModel]) -> Mapping[str, FieldInfo]:
    named = dict(model.model_fields)
    return {**named, **{info.alias: info for info in named.values() if info.alias}}


def _held(marks: tuple[Any, ...]) -> bool:
    return any(getattr(mark, "func", None) is held_text for mark in marks)


def _held_nodes(nodes: Any, texts: Mapping[str, str]) -> Any:
    if not isinstance(nodes, list):
        return nodes
    return [_held_node(node, texts) for node in nodes]


def _held_node(node: Any, texts: Mapping[str, str]) -> Any:
    if isinstance(node, str):
        return texts.get(node, node)
    if isinstance(node, Mapping) and isinstance(node.get(MARK_CHILDREN), list):
        return {**node, MARK_CHILDREN: _held_nodes(node[MARK_CHILDREN], texts)}
    return node


def _patterned(mark: Any) -> bool:
    if isinstance(getattr(mark, "pattern", None), str):
        return True
    inner = getattr(mark, "metadata", None)
    return isinstance(inner, list) and any(_patterned(found) for found in inner)


def _fits(value: Any, arm: Any) -> bool:
    base = get_args(arm)[0] if get_origin(arm) is Annotated else arm
    if value is None:
        return base is type(None)
    if isinstance(value, str):
        return base is str
    if isinstance(value, list):
        return get_origin(base) in SEQUENCES
    return isinstance(value, Mapping) and _validates(value, base)


def _validates(value: Mapping[str, Any], base: Any) -> bool:
    if not (isinstance(base, type) and issubclass(base, BaseModel)):
        return False
    try:
        base.model_validate(value)
    except ValidationError:
        return False
    return True
