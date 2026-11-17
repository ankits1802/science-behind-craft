import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MAGIC = b"CDF\x01"
DIMENSION, VARIABLE, ATTRIBUTE = 0x0A, 0x0B, 0x0C
CHAR = 2
TYPES = {np.dtype(">f4"): 5, np.dtype(">f8"): 6}


@dataclass
class Variable:
    name: str
    dimensions: tuple[str, ...]
    data: np.ndarray
    attributes: dict[str, str] = field(default_factory=dict)


def padded(data: bytes) -> bytes:
    return data + b"\0" * (-len(data) % 4)


def name_bytes(text: str) -> bytes:
    encoded = text.encode("utf-8")
    return struct.pack(">i", len(encoded)) + padded(encoded)


def attribute_list(attributes: dict[str, str]) -> bytes:
    if not attributes:
        return struct.pack(">ii", 0, 0)
    body = b"".join(
        name_bytes(key) + struct.pack(">ii", CHAR, len(value.encode("utf-8"))) + padded(value.encode("utf-8"))
        for key, value in attributes.items()
    )
    return struct.pack(">ii", ATTRIBUTE, len(attributes)) + body


def header(dimensions: dict[str, int], variables: list[Variable], begins: list[int]) -> bytes:
    dims = b"".join(name_bytes(name) + struct.pack(">i", size) for name, size in dimensions.items())
    order = list(dimensions)
    parts = [MAGIC, struct.pack(">i", 0), struct.pack(">ii", DIMENSION, len(dimensions)), dims]
    parts += [struct.pack(">ii", 0, 0), struct.pack(">ii", VARIABLE, len(variables))]
    for variable, begin in zip(variables, begins, strict=True):
        dimension_ids = [order.index(name) for name in variable.dimensions]
        ids = struct.pack(f">i{len(dimension_ids)}i", len(dimension_ids), *dimension_ids)
        size = len(padded(variable.data.tobytes()))
        parts += [name_bytes(variable.name), ids, attribute_list(variable.attributes)]
        parts += [struct.pack(">iii", TYPES[variable.data.dtype], size, begin)]
    return b"".join(parts)


def write_classic(path: Path, dimensions: dict[str, int], variables: list[Variable]) -> Path:
    blobs = [padded(variable.data.tobytes()) for variable in variables]
    start = len(header(dimensions, variables, [0] * len(variables)))
    begins = [start + sum(len(blob) for blob in blobs[:index]) for index in range(len(blobs))]
    path.write_bytes(header(dimensions, variables, begins) + b"".join(blobs))
    return path
