import importlib.util
from pathlib import Path
from types import ModuleType

__all__ = ["migration"]

VERSIONS = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def migration(name: str) -> ModuleType:
    path = VERSIONS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"migration_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
