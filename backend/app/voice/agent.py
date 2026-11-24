from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.core.errors import InvalidInput
from app.providers.elevenlabs import TTS_MODEL, ElevenLabs
from app.research.vocabulary import CANONICAL_LANGUAGE
from app.schemas.voice import CLIENT_TOOL_NAMES, MAX_SESSION_SECONDS
from app.schemas.voice_llm import CONVERSATION_HEADER, SYSTEM_TOOL_NAMES, VOICE_LLM_MODEL, VOICE_LLM_PATH

from .artisan_guide import agent_opening
from .languages import VOICE_LANGUAGES

__all__ = [
    "AGENT_NAME",
    "ARTISAN_AGENT_NAME",
    "ARTISAN_LLM_PATH",
    "CLIENT_TOOLS",
    "LLM_SECRET_NAME",
    "AgentPlan",
    "ProvisionedAgent",
    "agent_body",
    "artisan_agent_body",
    "artisan_language_presets",
    "language_presets",
    "llm_base_url",
    "provision_agent",
    "provision_artisan_agent",
]

AGENT_NAME = "KalaVigyan voice"
ARTISAN_AGENT_NAME = "KalaVigyan artisan conversations"
ARTISAN_LLM_PATH = "/api/artisan/llm/v1/chat/completions"
ARTISAN_TURN_EAGERNESS = "patient"
ARTISAN_SOFT_TIMEOUT_SECONDS = 5.0
ARTISAN_PROMPT = (
    "You are KalaVigyan, listening to an artisan. Every reply comes from the custom language model."
)
LLM_SECRET_NAME = "KALAVIGYAN_VOICE_LLM_BEARER"
CHAT_COMPLETIONS_SUFFIX = "/chat/completions"
AGENT_PROMPT = "You are KalaVigyan. Every reply comes from the custom language model."
TURN_TIMEOUT_SECONDS = 10
CONVERSATION_ID_VARIABLE = {"variable_name": "system__conversation_id"}
CASCADE_TIMEOUT_SECONDS = 15.0
NO_BACKUP_LLM = {"preference": "disabled"}
SOFT_TIMEOUT_SECONDS = 3.0
TURN_EAGERNESS = "normal"
TRANSCRIPT_RETENTION_DAYS_AT_ELEVENLABS = 2
CLIENT_EVENTS = (
    "audio",
    "interruption",
    "user_transcript",
    "agent_response",
    "agent_response_correction",
    "client_tool_call",
)

CLIENT_TOOLS: Mapping[str, dict[str, Any]] = {
    "show_on_map": {
        "description": "Show the session's craft on the India map.",
        "parameters": {"craftSlug": "The craft's slug, exactly as given by the server."},
    },
    "open_stage": {
        "description": "Open a process stage of the craft on the page.",
        "parameters": {"stageId": "The stage id, exactly as given by the server."},
    },
    "show_sources": {
        "description": "Show the sources of a spoken answer.",
        "parameters": {"answerId": "The answer id, exactly as given by the server."},
    },
    "offer_image": {
        "description": "Offer the image button for a process stage.",
        "parameters": {"stageId": "The stage id, exactly as given by the server."},
    },
}


@dataclass(frozen=True)
class AgentPlan:
    api_base_url: str
    llm_bearer: str
    voice_id: str
    max_live_sessions: int
    agent_id: str | None = None


@dataclass(frozen=True)
class ProvisionedAgent:
    agent_id: str
    created: bool
    secret_id: str
    tool_ids: dict[str, str]


def llm_base_url(api_base_url: str) -> str:
    origin = api_base_url.rstrip("/")
    if not origin.startswith("https://"):
        raise InvalidInput("The custom language model must be reached over https")
    return origin + VOICE_LLM_PATH.removesuffix(CHAT_COMPLETIONS_SUFFIX)


def client_tool_config(name: str) -> dict[str, Any]:
    spec = CLIENT_TOOLS[name]
    properties = {key: {"type": "string", "description": text} for key, text in spec["parameters"].items()}
    return {
        "type": "client",
        "name": name,
        "description": spec["description"],
        "parameters": {"type": "object", "properties": properties, "required": list(properties)},
        "expects_response": False,
    }


def agent_body(plan: AgentPlan, *, secret_id: str, tool_ids: Sequence[str]) -> dict[str, Any]:
    return {
        "name": AGENT_NAME,
        "conversation_config": {
            "agent": {
                "first_message": "",
                "language": CANONICAL_LANGUAGE,
                "prompt": _prompt(plan, secret_id, tool_ids),
            },
            "language_presets": language_presets(),
            "turn": {
                "turn_timeout": TURN_TIMEOUT_SECONDS,
                "turn_eagerness": TURN_EAGERNESS,
                "soft_timeout_config": {"timeout_seconds": SOFT_TIMEOUT_SECONDS},
            },
            "conversation": {
                "max_duration_seconds": MAX_SESSION_SECONDS,
                "client_events": list(CLIENT_EVENTS),
            },
            "tts": {"model_id": TTS_MODEL, "voice_id": plan.voice_id},
        },
        "platform_settings": {
            "auth": {"enable_auth": True},
            "overrides": {"custom_llm_extra_body": False, "conversation_config_override": _no_overrides()},
            "privacy": {
                "record_voice": False,
                "retention_days": TRANSCRIPT_RETENTION_DAYS_AT_ELEVENLABS,
                "delete_audio": True,
            },
            "call_limits": {"agent_concurrency_limit": plan.max_live_sessions},
        },
    }


async def provision_agent(elevenlabs: ElevenLabs, plan: AgentPlan) -> ProvisionedAgent:
    secret_id = await _llm_secret(elevenlabs, plan.llm_bearer)
    tool_ids = await _client_tools(elevenlabs)
    body = agent_body(plan, secret_id=secret_id, tool_ids=[tool_ids[name] for name in CLIENT_TOOL_NAMES])
    agent_id = plan.agent_id or await _existing_agent(elevenlabs)
    if agent_id is None:
        created = await elevenlabs.create_agent(body)
        return ProvisionedAgent(agent_id=created, created=True, secret_id=secret_id, tool_ids=tool_ids)
    await elevenlabs.update_agent(agent_id, body)
    return ProvisionedAgent(agent_id=agent_id, created=False, secret_id=secret_id, tool_ids=tool_ids)


def language_presets() -> dict[str, Any]:
    return {
        code: {"overrides": {"tts": {"model_id": TTS_MODEL}}}
        for code in VOICE_LANGUAGES
        if code != CANONICAL_LANGUAGE
    }


def _prompt(plan: AgentPlan, secret_id: str, tool_ids: Sequence[str]) -> dict[str, Any]:
    return {
        "prompt": AGENT_PROMPT,
        "llm": "custom-llm",
        "custom_llm": {
            "url": llm_base_url(plan.api_base_url),
            "model_id": VOICE_LLM_MODEL,
            "api_key": {"secret_id": secret_id},
            "request_headers": {CONVERSATION_HEADER: dict(CONVERSATION_ID_VARIABLE)},
            "api_type": "chat_completions",
        },
        "cascade_timeout_seconds": CASCADE_TIMEOUT_SECONDS,
        "backup_llm_config": dict(NO_BACKUP_LLM),
        "tool_ids": list(tool_ids),
        "built_in_tools": {
            name: {"name": name, "description": "", "params": {"system_tool_type": name}}
            for name in SYSTEM_TOOL_NAMES
        },
    }


def _no_overrides() -> dict[str, Any]:
    return {
        "agent": {"first_message": False, "language": False, "prompt": {"prompt": False}},
        "tts": {"voice_id": False, "model_id": False},
        "conversation": {"text_only": False, "max_duration_seconds": False},
    }


async def _llm_secret(elevenlabs: ElevenLabs, bearer: str) -> str:
    found = await elevenlabs.secret_ids(LLM_SECRET_NAME)
    if len(found) > 1:
        raise InvalidInput(f"ElevenLabs holds {len(found)} secrets named {LLM_SECRET_NAME}; keep one")
    if found:
        await elevenlabs.update_secret(found[0], LLM_SECRET_NAME, bearer)
        return found[0]
    return await elevenlabs.create_secret(LLM_SECRET_NAME, bearer)


async def _client_tools(elevenlabs: ElevenLabs) -> dict[str, str]:
    existing = await elevenlabs.client_tool_ids()
    ids: dict[str, str] = {}
    for name in CLIENT_TOOL_NAMES:
        config = client_tool_config(name)
        if name in existing:
            await elevenlabs.update_tool(existing[name], config)
            ids[name] = existing[name]
        else:
            ids[name] = await elevenlabs.create_tool(config)
    return ids


async def _existing_agent(elevenlabs: ElevenLabs) -> str | None:
    found = await elevenlabs.agent_ids(AGENT_NAME)
    if len(found) > 1:
        raise InvalidInput(
            f"ElevenLabs holds {len(found)} agents named {AGENT_NAME}; set ELEVENLABS_AGENT_ID"
        )
    return found[0] if found else None


def artisan_language_presets() -> dict[str, Any]:
    return {
        code: {"overrides": {"tts": {"model_id": TTS_MODEL}, "agent": {"first_message": agent_opening(code)}}}
        for code in VOICE_LANGUAGES
        if code != CANONICAL_LANGUAGE
    }


def artisan_agent_body(plan: AgentPlan, *, secret_id: str) -> dict[str, Any]:
    body = agent_body(plan, secret_id=secret_id, tool_ids=())
    config = body["conversation_config"]
    prompt = config["agent"]["prompt"]
    prompt["prompt"] = ARTISAN_PROMPT
    prompt["custom_llm"]["url"] = _origin(plan.api_base_url) + ARTISAN_LLM_PATH.removesuffix(
        CHAT_COMPLETIONS_SUFFIX
    )
    config["agent"]["first_message"] = agent_opening(CANONICAL_LANGUAGE)
    config["language_presets"] = artisan_language_presets()
    config["turn"] |= {
        "turn_eagerness": ARTISAN_TURN_EAGERNESS,
        "soft_timeout_config": {"timeout_seconds": ARTISAN_SOFT_TIMEOUT_SECONDS},
    }
    return {**body, "name": ARTISAN_AGENT_NAME}


async def provision_artisan_agent(elevenlabs: ElevenLabs, plan: AgentPlan) -> ProvisionedAgent:
    secret_id = await _llm_secret(elevenlabs, plan.llm_bearer)
    body = artisan_agent_body(plan, secret_id=secret_id)
    agent_id = plan.agent_id or await _existing_named(elevenlabs, ARTISAN_AGENT_NAME)
    if agent_id is None:
        created = await elevenlabs.create_agent(body)
        return ProvisionedAgent(agent_id=created, created=True, secret_id=secret_id, tool_ids={})
    await elevenlabs.update_agent(agent_id, body)
    return ProvisionedAgent(agent_id=agent_id, created=False, secret_id=secret_id, tool_ids={})


def _origin(api_base_url: str) -> str:
    origin = api_base_url.rstrip("/")
    if not origin.startswith("https://"):
        raise InvalidInput("The custom language model must be reached over https")
    return origin


async def _existing_named(elevenlabs: ElevenLabs, name: str) -> str | None:
    found = await elevenlabs.agent_ids(name)
    if len(found) > 1:
        raise InvalidInput(f"ElevenLabs holds {len(found)} agents named {name}; set its agent id")
    return found[0] if found else None
