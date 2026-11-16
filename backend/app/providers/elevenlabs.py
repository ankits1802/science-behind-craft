from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
from urllib.parse import quote

import httpx

from app.core.errors import RETRYABLE_KINDS, ExternalFailure, InvalidInput, NotConfigured, failure_kind
from app.core.retry_after import parse_headers

__all__ = [
    "ELEVENLABS_API",
    "ELEVENLABS_KEY_NAME",
    "ELEVENLABS_SERVICE",
    "SPEECH_MAX_BYTES",
    "STT_LANGUAGE_CODES",
    "STT_MODEL",
    "TTS_BITS_PER_SECOND",
    "TTS_LANGUAGES",
    "TTS_MODEL",
    "TTS_OUTPUT_FORMAT",
    "ConversationRecord",
    "ConversationToken",
    "ElevenLabs",
    "HeardSpeech",
    "speech_seconds",
]

ELEVENLABS_SERVICE = "elevenlabs"
ELEVENLABS_API = "https://api.elevenlabs.io"
ELEVENLABS_KEY_NAME = "ELEVENLABS_API_KEY"
KEY_HEADER = "xi-api-key"
STT_MODEL = "scribe_v3"
TTS_MODEL = "eleven_v4_turbo"
TTS_OUTPUT_FORMAT = "mp3_44100_128"
TTS_BITS_PER_SECOND = 128_000
SPEECH_MAX_BYTES = 8 * 1024 * 1024
REQUEST_TIMEOUT = httpx.Timeout(20.0, connect=5.0)
PROBE_TIMEOUT = httpx.Timeout(3.0)
PAGE_SIZE = 100
PAGES_MAX = 20
STT_LANGUAGE_CODES: Mapping[str, str] = MappingProxyType(
    {
        "en": "eng",
        "hi": "hin",
        "bn": "ben",
        "ta": "tam",
        "te": "tel",
        "mr": "mar",
        "gu": "guj",
        "kn": "kan",
        "ml": "mal",
        "or": "ori",
        "pa": "pan",
        "as": "asm",
        "ur": "urd",
    }
)
TTS_LANGUAGES = frozenset({"en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "or", "pa", "as", "ur"})


@dataclass(frozen=True)
class ConversationToken:
    token: str
    conversation_id: str


@dataclass(frozen=True)
class ConversationRecord:
    conversation_id: str
    status: str
    call_duration_seconds: int | None


@dataclass(frozen=True)
class HeardSpeech:
    text: str
    language: str | None
    seconds: int


def speech_seconds(byte_count: int) -> int:
    return math.ceil(byte_count * 8 / TTS_BITS_PER_SECOND)


class ElevenLabs:
    def __init__(self, *, api_key: str, client: httpx.AsyncClient, base_url: str = ELEVENLABS_API) -> None:
        if not api_key.strip():
            raise NotConfigured(ELEVENLABS_KEY_NAME, f"{ELEVENLABS_KEY_NAME} is not set")
        self._key = api_key.strip()
        self._client = client
        self._base = base_url.rstrip("/")

    async def account(self) -> None:
        await self._send("GET", "/v1/user", timeout=PROBE_TIMEOUT)

    async def conversation_token(self, agent_id: str) -> ConversationToken:
        body = await self._json("GET", "/v1/convai/conversation/token", params={"agent_id": agent_id})
        token, conversation_id = body.get("token"), body.get("conversation_id")
        if not _text(token) or not _text(conversation_id):
            raise _off_contract("conversation token")
        return ConversationToken(token=token, conversation_id=conversation_id)

    async def conversation(self, conversation_id: str) -> ConversationRecord:
        body = await self._json("GET", f"/v1/convai/conversations/{quote(conversation_id, safe='')}")
        status = body.get("status")
        duration = (body.get("metadata") or {}).get("call_duration_secs")
        if not _text(status) or (duration is not None and not isinstance(duration, int | float)):
            raise _off_contract("conversation")
        seconds = None if duration is None else math.ceil(duration)
        return ConversationRecord(
            conversation_id=conversation_id, status=status, call_duration_seconds=seconds
        )

    async def delete_conversation(self, conversation_id: str) -> None:
        await self._send("DELETE", f"/v1/convai/conversations/{quote(conversation_id, safe='')}")

    async def speech_to_text(
        self, audio: bytes, *, content_type: str, language: str, keyterms: Sequence[str] = ()
    ) -> HeardSpeech:
        if language not in STT_LANGUAGE_CODES:
            raise InvalidInput(f"{STT_MODEL} is not set up to hear language {language!r}")
        data: dict[str, Any] = {
            "model_id": STT_MODEL,
            "language_code": STT_LANGUAGE_CODES[language],
            "tag_audio_events": "false",
        }
        if keyterms:
            data["keyterms"] = list(keyterms)
        files = {"file": ("turn", audio, content_type)}
        body = await self._json("POST", "/v1/speech-to-text", data=data, files=files)
        text, words = body.get("text"), body.get("words") or []
        if not isinstance(text, str) or not isinstance(words, list):
            raise _off_contract("speech to text")
        ends = [w["end"] for w in words if isinstance(w, dict) and isinstance(w.get("end"), int | float)]
        language_code = body.get("language_code")
        return HeardSpeech(
            text=text.strip(),
            language=language_code if isinstance(language_code, str) else None,
            seconds=math.ceil(max(ends)) if ends else 0,
        )

    async def speech(self, text: str, *, voice_id: str, language: str) -> bytes:
        if language not in TTS_LANGUAGES:
            raise InvalidInput(f"{TTS_MODEL} is not set up to speak language {language!r}")
        response = await self._send(
            "POST",
            f"/v1/text-to-speech/{quote(voice_id, safe='')}/stream",
            params={"output_format": TTS_OUTPUT_FORMAT},
            json={"text": text, "model_id": TTS_MODEL, "language_code": language},
        )
        audio = response.content
        if not audio or len(audio) > SPEECH_MAX_BYTES:
            raise _off_contract(f"text to speech ({len(audio)} bytes)")
        return audio

    async def agent_ids(self, name: str) -> list[str]:
        agents = await self._pages("/v1/convai/agents", "agents", {"search": name})
        return [str(a["agent_id"]) for a in agents if a.get("name") == name and _text(a.get("agent_id"))]

    async def create_agent(self, body: Mapping[str, Any]) -> str:
        created = await self._json("POST", "/v1/convai/agents/create", json=dict(body))
        return _id_in(created, "agent_id", "agent")

    async def update_agent(self, agent_id: str, body: Mapping[str, Any]) -> None:
        await self._send("PATCH", f"/v1/convai/agents/{quote(agent_id, safe='')}", json=dict(body))

    async def client_tool_ids(self) -> dict[str, str]:
        tools = await self._pages("/v1/convai/tools", "tools", {"types": "client"})
        return {str(t["tool_config"]["name"]): str(t["id"]) for t in tools if _is_named_tool(t)}

    async def create_tool(self, config: Mapping[str, Any]) -> str:
        created = await self._json("POST", "/v1/convai/tools", json={"tool_config": dict(config)})
        return _id_in(created, "id", "tool")

    async def update_tool(self, tool_id: str, config: Mapping[str, Any]) -> None:
        await self._send(
            "PATCH", f"/v1/convai/tools/{quote(tool_id, safe='')}", json={"tool_config": dict(config)}
        )

    async def secret_ids(self, name: str) -> list[str]:
        found = await self._pages("/v1/convai/secrets", "secrets", {"search": name})
        return [str(s["secret_id"]) for s in found if s.get("name") == name and _text(s.get("secret_id"))]

    async def create_secret(self, name: str, value: str) -> str:
        created = await self._json(
            "POST", "/v1/convai/secrets", json={"type": "new", "name": name, "value": value}
        )
        return _id_in(created, "secret_id", "secret")

    async def update_secret(self, secret_id: str, name: str, value: str) -> None:
        body = {"type": "update", "name": name, "value": value}
        await self._send("PATCH", f"/v1/convai/secrets/{quote(secret_id, safe='')}", json=body)

    async def _pages(self, path: str, field: str, params: Mapping[str, str]) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(PAGES_MAX):
            query = {**params, "page_size": str(PAGE_SIZE), **({"cursor": cursor} if cursor else {})}
            body = await self._json("GET", path, params=query)
            items = body.get(field)
            if not isinstance(items, list):
                raise _off_contract(path)
            found += [item for item in items if isinstance(item, dict)]
            cursor = body.get("next_cursor") if body.get("has_more", True) else None
            if not _text(cursor):
                return found
        raise ExternalFailure(
            f"ElevenLabs {path} has more than {PAGES_MAX} pages", service=ELEVENLABS_SERVICE
        )

    async def _json(self, method: str, path: str, **request: Any) -> dict[str, Any]:
        response = await self._send(method, path, **request)
        try:
            body = response.json()
        except ValueError:
            raise _off_contract(path) from None
        if not isinstance(body, dict):
            raise _off_contract(path)
        return body

    async def _send(
        self, method: str, path: str, *, timeout: httpx.Timeout = REQUEST_TIMEOUT, **request: Any
    ) -> httpx.Response:
        try:
            response = await self._client.request(
                method, f"{self._base}{path}", headers={KEY_HEADER: self._key}, timeout=timeout, **request
            )
        except httpx.HTTPError as error:
            raise ExternalFailure(
                f"ElevenLabs could not be reached ({type(error).__name__})",
                kind="unavailable",
                retryable=True,
                service=ELEVENLABS_SERVICE,
            ) from None
        if response.is_success:
            return response
        kind = failure_kind(response.status_code)
        raise ExternalFailure(
            f"ElevenLabs answered {response.status_code} to {method} {path}",
            kind=kind,
            retryable=kind in RETRYABLE_KINDS,
            status=response.status_code,
            retry_after=parse_headers(response.headers),
            service=ELEVENLABS_SERVICE,
        )


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_named_tool(tool: Mapping[str, Any]) -> bool:
    config = tool.get("tool_config")
    return isinstance(config, dict) and _text(config.get("name")) and _text(tool.get("id"))


def _id_in(body: Mapping[str, Any], field: str, what: str) -> str:
    value = body.get(field)
    if not _text(value):
        raise _off_contract(f"created {what}")
    return str(value)


def _off_contract(what: str) -> ExternalFailure:
    return ExternalFailure(
        f"ElevenLabs {what} answer is off its documented shape", service=ELEVENLABS_SERVICE
    )
