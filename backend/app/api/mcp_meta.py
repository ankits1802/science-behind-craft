from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from .mcp_protocol import (
    INVALID_PARAMS,
    LEGACY_VERSIONS,
    MISSING_CAPABILITY,
    MODERN_VERSION,
    RequestError,
    unsupported_version,
)

__all__ = [
    "CAPABILITIES_KEY",
    "CLIENT_INFO_KEY",
    "FILES_EXTENSION",
    "PROTOCOL_KEY",
    "SERVER_INFO_KEY",
    "SKILLS_EXTENSION",
    "TASKS_EXTENSION",
    "RequestMeta",
    "is_modern",
    "missing_capability",
    "request_meta",
]

PROTOCOL_KEY = "io.modelcontextprotocol/protocolVersion"
CAPABILITIES_KEY = "io.modelcontextprotocol/clientCapabilities"
CLIENT_INFO_KEY = "io.modelcontextprotocol/clientInfo"
SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"
SKILLS_EXTENSION = "io.modelcontextprotocol/skills"
TASKS_EXTENSION = "io.modelcontextprotocol/tasks"
FILES_EXTENSION = "io.modelcontextprotocol/files"
LEGACY_ONLY = frozenset({"initialize"})
UPLOAD_SETTING = "upload"
REVISION_SETTING = "revision"
FORM_MODE = "form"
MISSING_MESSAGE = "Missing required client capability"
NO_CAPABILITIES = f"a request of protocol {MODERN_VERSION} carries {CAPABILITIES_KEY} in its _meta"


@dataclass(frozen=True)
class RequestMeta:
    version: str
    capabilities: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def extension(self, name: str) -> Mapping[str, Any] | None:
        extensions = self.capabilities.get("extensions")
        settings = extensions.get(name) if isinstance(extensions, Mapping) else None
        return settings if isinstance(settings, Mapping) else None

    def runs_tasks(self) -> bool:
        return self.extension(TASKS_EXTENSION) is not None

    def uploads_files(self) -> bool:
        settings = self.extension(FILES_EXTENSION)
        if settings is None or REVISION_SETTING in settings:
            return False
        return isinstance(settings.get(UPLOAD_SETTING), Mapping)

    def elicits_forms(self) -> bool:
        modes = self.capabilities.get("elicitation")
        if not isinstance(modes, Mapping):
            return False
        return not modes or isinstance(modes.get(FORM_MODE), Mapping)


def is_modern(message: Any) -> bool:
    if not isinstance(message, Mapping) or message.get("method") in LEGACY_ONLY:
        return False
    params = message.get("params")
    meta = params.get("_meta") if isinstance(params, Mapping) else None
    version = meta.get(PROTOCOL_KEY) if isinstance(meta, Mapping) else None
    return version is not None and version not in LEGACY_VERSIONS


def request_meta(method: str, params: Mapping[str, Any]) -> RequestMeta | None:
    if not is_modern({"method": method, "params": params}):
        return None
    meta = params["_meta"]
    version = meta[PROTOCOL_KEY]
    if version != MODERN_VERSION:
        raise unsupported_version(version)
    capabilities = meta.get(CAPABILITIES_KEY)
    if not isinstance(capabilities, Mapping):
        raise RequestError(INVALID_PARAMS, NO_CAPABILITIES)
    return RequestMeta(version=version, capabilities=MappingProxyType(dict(capabilities)))


def missing_capability(required: Mapping[str, Any]) -> RequestError:
    return RequestError(MISSING_CAPABILITY, MISSING_MESSAGE, data={"requiredCapabilities": dict(required)})
