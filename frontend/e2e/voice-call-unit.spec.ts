import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { ApiError } from "@/lib/api";
import { splitSseBuffer } from "@/lib/answerStream";
import type { AgentEvents } from "@/lib/elevenLabsAgent";
import { parseShape } from "@/lib/shape";
import { AgentTransport } from "@/lib/voiceAgent";
import { VoiceCall, type TransportFactory, type VoiceApi, type VoiceCallDeps, type VoiceCallOptions } from "@/lib/voiceCall";
import {
  parseVoiceTurnBlock,
  voiceSessionStartedShape,
  voiceTranscriptShape,
  type ClientToolCall,
  type VoiceSessionStarted,
  type VoiceTranscript,
  type VoiceTurnEvent
} from "@/lib/voiceContract";
import { fullAt, type RecordingLimits } from "@/lib/voiceDevice";
import { RelayTransport } from "@/lib/voiceRelay";
import { consentVersionOf, VoiceConsentRequired } from "@/lib/voiceSession";

const SHARED = join(__dirname, "..", "..", "shared");
const golden = (name: string): unknown => JSON.parse(readFileSync(join(SHARED, name), "utf8"));
const RELAY = parseShape(voiceSessionStartedShape, golden("voice.session-relay.golden.json"));
const AGENT = parseShape(voiceSessionStartedShape, golden("voice.session-agent.golden.json"));
const TRANSCRIPT = parseShape(voiceTranscriptShape, golden("voice.transcript.golden.json"));
const TURN_EVENTS = splitSseBuffer(readFileSync(join(SHARED, "voice.turn.golden.sse"), "utf8")).blocks.map((block) => parseVoiceTurnBlock(block) as VoiceTurnEvent);
const SESSION_ID = "d4281969-05ea-5cf5-a5c0-5bb292452af6";
const ANSWER_ID = "b51bc0fe-dddf-57fc-84ad-138e6851a223";
const STAGE_ID = "575d3427-7a90-568d-87d5-bb0f1c602591";
const NOW = Date.UTC(2026, 10, 16, 10, 34, 12);
const TRANSPORTS: Record<VoiceSessionStarted["transport"], TransportFactory> = {
  AGENT: (host) => new AgentTransport(host),
  RELAY: (host) => new RelayTransport(host)
};

type Timer = { ms: number; run: () => void; live: boolean };

type Change = { api?: Partial<VoiceApi>; deps?: Partial<Omit<VoiceCallDeps, "api">>; consentVersion?: string };

function harness(session: VoiceSessionStarted, change: Change = {}) {
  const log: string[] = [];
  const timers: Timer[] = [];
  const actions: ClientToolCall[] = [];
  let agent: AgentEvents | null = null;
  let transcript: VoiceTranscript = { ...TRANSCRIPT, turns: [], sources: [] };
  const deps: VoiceCallDeps = {
    api: {
      notice: async () => ({ version: "2026-11-16", title: "Voice notice", body: "We keep the transcript for 30 days.", publishedAt: null }),
      accept: async (version) => void log.push(`accept ${version}`),
      start: async (request) => {
        log.push(`start ${JSON.stringify(request)}`);
        return session;
      },
      end: async (id, keepalive) => {
        log.push(`end ${id}${keepalive ? " keepalive" : ""}`);
        return { voiceSessionId: id, endedAt: "2026-11-16T10:40:00Z", turnCount: 1, reservedSeconds: 60, billedSeconds: null };
      },
      transcript: async () => transcript,
      turn: async (_id, file, onEvent) => {
        log.push(`turn ${file.name} ${file.type}`);
        TURN_EVENTS.forEach(onEvent);
      },
      ...change.api
    },
    connectAgent: async (token, events) => {
      log.push(`connect ${token}`);
      agent = events;
      return { end: async () => void log.push("hang up"), level: () => 0.4 };
    },
    record: async (type, name) => {
      log.push(`record ${type} ${name}`);
      return { stop: async () => new File([new Uint8Array(2048)], name, { type }), cancel: () => void log.push("cancel"), level: () => 0.3 };
    },
    play: async (path) => void log.push(`play ${path}`),
    imageStages: async () => new Set([STAGE_ID]),
    recordingTypes: ["audio/webm", "audio/ogg"],
    now: () => NOW,
    schedule: (ms, run) => {
      const timer = { ms, run, live: true };
      timers.push(timer);
      return () => void (timer.live = false);
    },
    ...change.deps
  };
  const options: VoiceCallOptions = {
    request: () => ({ craftSlug: "Kutch-Ajrakh", mode: "HYBRID", language: "en" }),
    consentVersion: () => change.consentVersion ?? null,
    stageIds: () => new Set([STAGE_ID]),
    onAction: (call) => void actions.push(call),
    onHeard: (text) => void log.push(`heard ${text}`)
  };
  const call = new VoiceCall(deps, TRANSPORTS);
  call.configure(options);
  const fire = (ms: number) => {
    for (const timer of timers.filter((candidate) => candidate.live && candidate.ms === ms)) {
      timer.live = false;
      timer.run();
    }
  };
  return {
    call,
    log,
    actions,
    fire,
    agent: () => agent as AgentEvents,
    setTranscript: (next: VoiceTranscript) => void (transcript = next)
  };
}

async function settled(): Promise<void> {
  for (let round = 0; round < 20; round += 1) await new Promise((resolve) => setTimeout(resolve, 0));
}

test("the notice is shown and accepted before the first session starts", async () => {
  const { call, log } = harness(RELAY, { consentVersion: "2026-11-16" });
  call.begin();
  await settled();
  expect(call.getState()).toMatchObject({ phase: "consent", busy: false, notice: { version: "2026-11-16", title: "Voice notice" } });
  expect(log).toEqual([]);
  await call.accept();
  await settled();
  expect(log.slice(0, 2)).toEqual(["accept 2026-11-16", 'start {"craftSlug":"Kutch-Ajrakh","mode":"HYBRID","language":"en"}']);
  expect(call.getState().phase).toBe("live");
  await call.end();
  call.begin();
  await settled();
  expect(log.filter((line) => line.startsWith("accept "))).toHaveLength(1);
  expect(log.filter((line) => line.startsWith("start "))).toHaveLength(2);
});

test("a session refused for a missing consent asks for it, reading the version from the header", async () => {
  const refusal = new ApiError(403, "Accept the voice notice first.", null, new Headers({ "X-Voice-Consent-Required": "2026-11-16" }));
  expect(consentVersionOf(refusal)).toBe("2026-11-16");
  expect(consentVersionOf(new ApiError(403, "Verify your email first.", null, new Headers()))).toBeNull();
  let starts = 0;
  const { call, log } = harness(RELAY, {
    api: {
      start: async () => {
        starts += 1;
        if (starts === 1) throw new VoiceConsentRequired("2026-11-16");
        return RELAY;
      }
    }
  });
  call.begin();
  await settled();
  expect(call.getState().phase).toBe("consent");
  await call.accept();
  await settled();
  expect(log[0]).toBe("accept 2026-11-16");
  expect(call.getState().phase).toBe("live");
});

test("a relay turn records, streams, cites, applies held tools and speaks", async () => {
  const { call, log, actions } = harness(RELAY);
  call.begin();
  await settled();
  expect(log).toContain("record audio/webm KalaVigyan_Voice-Session_2026-11-16_1604_Kutch-Ajrakh_Recording.webm");
  expect(call.getState()).toMatchObject({ phase: "live", activity: "recording", startedAt: NOW });
  expect(call.level()).toBe(0.3);
  call.talk();
  await settled();
  expect(log).toContain("turn KalaVigyan_Voice-Session_2026-11-16_1604_Kutch-Ajrakh_Recording.webm audio/webm");
  expect(log).toContain("heard Why do Ajrakh printers use alum?");
  expect(log).toContain(`play /api/voice/session/${SESSION_ID}/turns/bd260d55-39e8-5cbf-9e4d-8dbe58ea75df/speech`);
  const state = call.getState();
  expect(state.conversation.turns.map((turn) => [turn.ordinal, turn.answerId, turn.sentences.length])).toEqual([[1, ANSWER_ID, 1]]);
  expect(actions).toEqual([{ name: "show_sources", parameters: { answerId: ANSWER_ID } }]);
  expect(state.reveal?.answerId).toBe(ANSWER_ID);
  expect(state.activity).toBe("ready");
});

test("the dock records at the session's bit rate and sends the turn once the recording nears its byte limit", async () => {
  const seen: RecordingLimits[] = [];
  const record = async (type: string, name: string, limits: RecordingLimits) => {
    seen.push(limits);
    return { stop: async () => new File([new Uint8Array(2048)], name, { type }), cancel: () => undefined, level: () => 0.3 };
  };
  const { call, log } = harness(RELAY, { deps: { record } });
  call.begin();
  await settled();
  const relay = RELAY.transport === "RELAY" ? RELAY : null;
  expect(seen.map(({ bitsPerSecond, maxBytes }) => [bitsPerSecond, maxBytes])).toEqual([[relay?.audioBitsPerSecond, relay?.maxAudioBytes]]);
  expect([relay?.audioBitsPerSecond, relay?.maxAudioBytes, fullAt(300_000)]).toEqual([32_000, 300_000, 270_000]);
  seen[0].onFull();
  await settled();
  expect(log.filter((line) => line.startsWith("turn "))).toHaveLength(1);
});

test("ending a call closes the session once and keeps the transcript", async () => {
  const { call, log } = harness(RELAY);
  call.begin();
  await settled();
  call.talk();
  await settled();
  await call.end();
  expect(log.filter((line) => line.startsWith("end "))).toEqual([`end ${SESSION_ID}`]);
  expect(call.getState()).toMatchObject({ phase: "ended", message: "Call ended.", activity: null });
  expect(call.getState().conversation.turns).toHaveLength(1);
  await call.end();
  expect(log.filter((line) => line.startsWith("end "))).toHaveLength(1);
});

test("the call ends itself when its time is up", async () => {
  const { call, fire } = harness(RELAY);
  call.begin();
  await settled();
  fire(RELAY.maxDurationSeconds * 1000);
  await settled();
  expect(call.getState()).toMatchObject({ phase: "ended", message: "Time's up for this call." });
});

test("a turn the server marks as the last ends the call after its reply", async () => {
  const last = TURN_EVENTS.map((event) => (event.type === "done" ? { ...event, data: { ...event.data, sessionEnded: true } } : event));
  const { call, log } = harness(RELAY, { api: { turn: async (_id, _file, onEvent) => last.forEach(onEvent) } });
  call.begin();
  await settled();
  call.talk();
  await settled();
  expect(log.some((line) => line.startsWith("play "))).toBe(true);
  expect(call.getState()).toMatchObject({ phase: "ended", message: "Call ended." });
});

test("a microphone refusal fails the call with a short sentence and closes the session", async () => {
  const { call, log } = harness(RELAY, { deps: { record: async () => Promise.reject(new DOMException("denied", "NotAllowedError")) } });
  call.begin();
  await settled();
  expect(call.getState()).toMatchObject({ phase: "failed", message: "Allow the microphone to talk." });
  expect(log).toContain(`end ${SESSION_ID}`);
});

test("a gone session ends the call; another failure stays in the call", async () => {
  const gone = harness(RELAY, { api: { turn: async () => Promise.reject(new ApiError(404, "Not found", null)) } });
  gone.call.begin();
  await settled();
  gone.call.talk();
  await settled();
  expect(gone.call.getState().phase).toBe("ended");
  const busy = harness(RELAY, { api: { turn: async () => Promise.reject(new ApiError(429, "No voice time left today.", { detail: "No voice time left today." })) } });
  busy.call.begin();
  await settled();
  busy.call.talk();
  await settled();
  expect(busy.call.getState()).toMatchObject({ phase: "live", activity: "ready" });
  expect(busy.call.getState().conversation.problem).toBe("No voice time left today.");
});

test("the agent gets the token only, and its tool calls are re-checked before they act", async () => {
  const { call, log, actions, agent, setTranscript } = harness(AGENT);
  call.begin();
  await settled();
  expect(log).toContain("connect fixture-conversation-token-not-a-credential");
  agent().onConnected();
  expect(call.getState().activity).toBe("listening");
  agent().onUserSpeech("Why do Ajrakh printers use alum?");
  expect(call.getState()).toMatchObject({ activity: "thinking", conversation: { heardLive: "Why do Ajrakh printers use alum?" } });
  expect(await agent().onToolCall({ name: "show_sources", parameters: { answerId: ANSWER_ID } })).toBe(false);
  expect(await agent().onToolCall({ name: "show_on_map", parameters: { craftSlug: "Kutch-Ajrakh" } })).toBe(true);
  expect(await agent().onToolCall({ name: "show_on_map", parameters: { craftSlug: "Bagru-Dabu" } })).toBe(false);
  expect(await agent().onToolCall({ name: "open_stage", parameters: { stageId: ANSWER_ID } })).toBe(false);
  expect(await agent().onToolCall({ name: "offer_image", parameters: { stageId: STAGE_ID } })).toBe(true);
  expect(await agent().onToolCall({ name: "open_url", parameters: { url: "https://example.com" } })).toBe(false);
  const mapped: ClientToolCall = { name: "show_on_map", parameters: { craftSlug: "Kutch-Ajrakh" } };
  setTranscript({ ...TRANSCRIPT, turns: [{ ...TRANSCRIPT.turns[0], actions: [...TRANSCRIPT.turns[0].actions, mapped] }] });
  agent().onAgentReply();
  await settled();
  expect(actions.map((action) => action.name)).toEqual(["show_on_map", "offer_image", "show_sources"]);
  expect(call.getState().conversation).toMatchObject({ heardLive: null, sources: TRANSCRIPT.sources });
  agent().onAgentReply();
  await settled();
  expect(actions).toHaveLength(3);
});

test("an image is offered only for a stage the media options list", async () => {
  const { call, agent } = harness(AGENT, { deps: { imageStages: async () => new Set() } });
  call.begin();
  await settled();
  expect(await agent().onToolCall({ name: "offer_image", parameters: { stageId: STAGE_ID } })).toBe(false);
});

test("a dropped agent call fails and closes the session; an agent hang-up ends it", async () => {
  const dropped = harness(AGENT);
  dropped.call.begin();
  await settled();
  const logged: unknown[] = [];
  const original = console.error;
  console.error = (...args: unknown[]) => void logged.push(...args);
  try {
    dropped.agent().onEnd({ by: "error", message: "ICE failed" });
    await settled();
  } finally {
    console.error = original;
  }
  expect(String(logged[0])).toContain("ICE failed");
  expect(dropped.call.getState()).toMatchObject({ phase: "failed", message: "The call dropped." });
  expect(dropped.log).toContain(`end ${SESSION_ID}`);
  const hungUp = harness(AGENT);
  hungUp.call.begin();
  await settled();
  hungUp.agent().onEnd({ by: "agent", message: null });
  await settled();
  expect(hungUp.call.getState()).toMatchObject({ phase: "ended", message: "Call ended." });
  expect(hungUp.log).toContain("hang up");
});

test("closing the panel ends a live session with keepalive, but a strict-mode remount keeps it", async () => {
  const kept = harness(RELAY);
  kept.call.begin();
  kept.call.dispose();
  kept.call.begin();
  await settled();
  kept.fire(0);
  expect(kept.log.filter((line) => line.startsWith("start "))).toHaveLength(1);
  expect(kept.call.getState().phase).toBe("live");
  kept.call.dispose();
  kept.fire(0);
  await settled();
  expect(kept.log).toContain(`end ${SESSION_ID} keepalive`);
  expect(kept.log).toContain("cancel");
  expect(kept.call.getState().phase).toBe("idle");
});

test("leaving the page ends a live session at once with keepalive", async () => {
  const { call, log } = harness(AGENT);
  call.begin();
  await settled();
  call.abandon();
  await settled();
  expect(log).toContain("hang up");
  expect(log).toContain(`end ${SESSION_ID} keepalive`);
  expect(call.getState().phase).toBe("idle");
});
