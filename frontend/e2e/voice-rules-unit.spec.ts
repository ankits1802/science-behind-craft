import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import nextConfig, { CONTENT_SECURITY_POLICY, ELEVENLABS_CONNECT_SOURCES } from "../next.config";
import { attributesForText, paragraphAttributes, sentenceView } from "@/lib/answerLanguages";
import { normaliseAskConfig } from "@/lib/askConfig";
import { splitSseBuffer } from "@/lib/answerStream";
import { agentEndOf } from "@/lib/elevenLabsAgent";
import { formatClock, spokenClock } from "@/lib/format";
import { mediaOptionsShape, offeredStageIds } from "@/lib/mediaContract";
import { shownStageNames } from "@/lib/processView";
import { craftProcessShape } from "@/lib/scienceContract";
import { parseShape } from "@/lib/shape";
import { EMPTY_CONVERSATION, reduceRelayEvent } from "@/lib/voiceConversation";
import { parseVoiceTurnBlock, voiceAvailabilityShape, voiceTranscriptShape, type ClientToolCall, type VoiceAvailability } from "@/lib/voiceContract";
import { pickRecordingType, recordingFileName, recordingTypes } from "@/lib/voiceDevice";
import {
  EMPTY_LEDGER,
  isHeldToolCall,
  NO_VOICE,
  prepayAction,
  toolCallOf,
  unappliedActions,
  voiceAvailabilityOf,
  voiceFailure,
  voiceLanguage,
  voiceMode,
  voiceOffered,
  voicePickerValue,
  type HeldFacts
} from "@/lib/voiceRules";

const SHARED = join(__dirname, "..", "..", "shared");
const golden = (name: string): unknown => JSON.parse(readFileSync(join(SHARED, name), "utf8"));
const AVAILABLE = parseShape(voiceAvailabilityShape, golden("voice.availability.golden.json"));
const FULL_SUPPORT = { agent: true, relayTypes: ["audio/webm"] };
const ANSWER_ID = "b51bc0fe-dddf-57fc-84ad-138e6851a223";
const STAGE_ID = "575d3427-7a90-568d-87d5-bb0f1c602591";

function quietly<T>(run: () => T): { value: T; logged: unknown[] } {
  const logged: unknown[] = [];
  const original = console.error;
  console.error = (...args: unknown[]) => void logged.push(...args);
  try {
    return { value: run(), logged };
  } finally {
    console.error = original;
  }
}

test("the voice button is offered only for configured voice this browser can carry", () => {
  expect(voiceOffered(AVAILABLE, FULL_SUPPORT)).toBe(true);
  expect(voiceOffered(AVAILABLE, { agent: false, relayTypes: ["audio/webm"] })).toBe(false);
  expect(voiceOffered({ ...AVAILABLE, transport: "RELAY" }, { agent: false, relayTypes: ["audio/ogg"] })).toBe(true);
  expect(voiceOffered({ ...AVAILABLE, transport: "RELAY" }, { agent: true, relayTypes: [] })).toBe(false);
  expect(voiceOffered(NO_VOICE, FULL_SUPPORT)).toBe(false);
});

test("less than the 30 seconds a session needs hides voice; unlimited keeps it", () => {
  expect(voiceOffered({ ...AVAILABLE, remainingSeconds: 29 }, FULL_SUPPORT)).toBe(false);
  expect(voiceOffered({ ...AVAILABLE, remainingSeconds: 30 }, FULL_SUPPORT)).toBe(true);
  expect(voiceOffered({ ...AVAILABLE, remainingSeconds: null }, FULL_SUPPORT)).toBe(true);
});

test("the config's voice block is the contract's availability, and a block off the contract hides voice loudly", () => {
  expect(normaliseAskConfig({ modes: ["HYBRID"], voice: golden("voice.availability.golden.json") }).voice).toEqual(AVAILABLE);
  const legacy = quietly(() => voiceAvailabilityOf({ configured: false, languages: [] }));
  expect(legacy.value).toEqual(NO_VOICE);
  expect(String(legacy.logged[0])).toContain("answers/config voice.transport");
  expect(quietly(() => voiceAvailabilityOf(undefined)).logged).toEqual([]);
});

const URDU = { code: "ur", label: "Urdu", autonym: "اردو", script: "Arab", direction: "rtl" } as const;
const ENGLISH_ONLY: VoiceAvailability = { ...AVAILABLE, languages: [{ code: "en", label: "English", autonym: "English", script: "Latn", direction: "ltr" }] };

test("voice asks in the ask mode it can serve and an offered language", () => {
  expect(voiceMode("VERIFIED")).toBe("VERIFIED");
  expect(voiceMode("HYBRID")).toBe("HYBRID");
  expect(voiceMode("DEEP")).toBe("HYBRID");
  expect(voiceLanguage(AVAILABLE, "hi")?.code).toBe("hi");
  expect(voiceLanguage(ENGLISH_ONLY, "hi")?.code).toBe("en");
  expect(voiceLanguage(AVAILABLE, "bn")?.code).toBe("en");
  expect(voiceLanguage(NO_VOICE, "en")).toBeNull();
});

test("the voice languages are the ones the config lists, not a list in the client", () => {
  const config = normaliseAskConfig({ modes: ["HYBRID"], voice: golden("voice.availability.golden.json") });
  expect(config.voice.languages.map((language) => language.code)).toEqual(["en", "hi", "ta", "ur"]);
  const withBengali = { ...(golden("voice.availability.golden.json") as Record<string, unknown>), languages: [{ code: "bn", label: "Bengali", autonym: "বাংলা", script: "Beng", direction: "ltr" }] };
  expect(voiceAvailabilityOf(withBengali).languages.map((language) => language.code)).toEqual(["bn"]);
  const offContract = quietly(() => voiceAvailabilityOf({ ...withBengali, languages: [{ code: "bn", label: "Bengali" }] }));
  expect(offContract.value).toEqual(NO_VOICE);
  expect(String(offContract.logged[0])).toContain("answers/config voice.languages");
});

test("the dock follows the Ask preference: a chosen language, or Auto by the question's script", () => {
  expect(voiceLanguage(AVAILABLE, "auto", "अजरख में फिटकरी क्यों?")?.code).toBe("hi");
  expect(voiceLanguage(AVAILABLE, "auto", "پھٹکری کیوں؟")?.code).toBe("ur");
  expect(voiceLanguage(AVAILABLE, "auto", "")?.code).toBe("en");
  expect(voiceLanguage(AVAILABLE, "ta", "Why alum?")?.code).toBe("ta");
  const hindi = voiceLanguage(AVAILABLE, "hi");
  expect(hindi && voicePickerValue(AVAILABLE, "hi", hindi)).toBe("hi");
  expect(hindi && voicePickerValue(AVAILABLE, "auto", hindi)).toBe("auto");
  const english = voiceLanguage(AVAILABLE, "bn");
  expect(english && voicePickerValue(AVAILABLE, "bn", english)).toBe("en");
});

test("an Urdu transcript is drawn right to left, and an English fallback left to right", () => {
  const urdu = voiceLanguage(AVAILABLE, "ur");
  expect(urdu).toEqual(URDU);
  expect(attributesForText("اجرک میں پھٹکری کیوں استعمال ہوتی ہے؟", urdu)).toEqual({ lang: "ur", dir: "rtl" });
  expect(attributesForText("I could not hear that.", urdu)).toEqual({ lang: "en", dir: "ltr" });
  const said = "پھٹکری رنگ پکا کرتی ہے۔";
  const sentence = { id: "t1.1", text: said, level: "PROVISIONAL" as const, citations: [], translated: true, original: "Alum fastens the colours." };
  expect(sentenceView(sentence, urdu, false)).toEqual({ text: said, lang: "ur", dir: "rtl" });
  expect(paragraphAttributes({ id: "t1", heading: "", sentences: [sentence] }, urdu, false)).toEqual({ lang: "ur", dir: "rtl" });
  const untranslated = { id: "t1.2", text: "Alum fastens the colours.", level: "PROVISIONAL" as const, citations: [] };
  expect(sentenceView(untranslated, urdu, false)).toEqual({ text: untranslated.text, lang: "en", dir: "ltr" });
});

const HELD: HeldFacts = {
  craftSlug: "Kutch-Ajrakh",
  stageIds: new Set([STAGE_ID]),
  answerIds: new Set([ANSWER_ID]),
  imageStageIds: new Set([STAGE_ID])
};

test("each client tool is re-checked against what the browser holds", () => {
  const call = (raw: unknown) => toolCallOf(raw) as ClientToolCall;
  expect(isHeldToolCall(call({ name: "show_on_map", parameters: { craftSlug: "Kutch-Ajrakh" } }), HELD)).toBe(true);
  expect(isHeldToolCall(call({ name: "show_on_map", parameters: { craftSlug: "Bagru-Dabu" } }), HELD)).toBe(false);
  expect(isHeldToolCall(call({ name: "show_on_map", parameters: { craftSlug: "Kutch-Ajrakh" } }), { ...HELD, craftSlug: null })).toBe(false);
  expect(isHeldToolCall(call({ name: "open_stage", parameters: { stageId: STAGE_ID } }), HELD)).toBe(true);
  expect(isHeldToolCall(call({ name: "open_stage", parameters: { stageId: ANSWER_ID } }), HELD)).toBe(false);
  expect(isHeldToolCall(call({ name: "show_sources", parameters: { answerId: ANSWER_ID } }), HELD)).toBe(true);
  expect(isHeldToolCall(call({ name: "show_sources", parameters: { answerId: STAGE_ID } }), HELD)).toBe(false);
  expect(isHeldToolCall(call({ name: "offer_image", parameters: { stageId: STAGE_ID } }), HELD)).toBe(true);
  expect(isHeldToolCall(call({ name: "offer_image", parameters: { stageId: STAGE_ID } }), { ...HELD, imageStageIds: new Set() })).toBe(false);
});

test("a tool call off the contract is ignored, never applied", () => {
  expect(toolCallOf({ name: "open_url", parameters: { url: "https://example.com" } })).toBeNull();
  expect(toolCallOf({ name: "open_stage", parameters: { stageId: "1; drop" } })).toBeNull();
  expect(toolCallOf({ name: "show_sources", parameters: { answerId: ANSWER_ID, extra: true } })).toBeNull();
  expect(toolCallOf("show_sources")).toBeNull();
});

test("a transcript action already applied through the agent is not applied again, and a repeat is", () => {
  const show: ClientToolCall = { name: "show_sources", parameters: { answerId: ANSWER_ID } };
  const map: ClientToolCall = { name: "show_on_map", parameters: { craftSlug: "Kutch-Ajrakh" } };
  const prepaid = prepayAction(EMPTY_LEDGER, map);
  const first = unappliedActions([{ turnId: "t1", actions: [show, map] }], prepaid);
  expect(first.calls).toEqual([show]);
  const again = unappliedActions([{ turnId: "t1", actions: [show, map] }, { turnId: "t2", actions: [map] }], first.ledger);
  expect(again.calls).toEqual([map]);
  expect(unappliedActions([{ turnId: "t1", actions: [show, map] }, { turnId: "t2", actions: [map] }], again.ledger).calls).toEqual([]);
});

test("the relay turn stream builds the same turn the transcript stores", () => {
  const { blocks } = splitSseBuffer(readFileSync(join(SHARED, "voice.turn.golden.sse"), "utf8"));
  const conversation = blocks.map(parseVoiceTurnBlock).reduce((state, event) => (event ? reduceRelayEvent(state, event) : state), EMPTY_CONVERSATION);
  const stored = parseShape(voiceTranscriptShape, golden("voice.transcript.golden.json"));
  const strip = (turn: (typeof stored.turns)[number]) => ({ ...turn, sentences: turn.sentences.map(({ translated: _translated, ...sentence }) => sentence) });
  expect(conversation.turns.map(strip)).toEqual(stored.turns.map(strip));
  expect(conversation.sources).toEqual(stored.sources);
  expect(conversation.draft).toBeNull();
  expect(conversation.status).toBeNull();
});

test("an error frame before done keeps no half turn and says why", () => {
  const events = [
    'event: heard\ndata: {"text":"What is alum?","language":"en"}',
    'event: error\ndata: {"message":"Couldn\'t answer that."}',
    'event: done\ndata: {"turnId":"bd260d55-39e8-5cbf-9e4d-8dbe58ea75df","answerId":null,"billedSeconds":3,"remainingSeconds":500,"sessionEnded":false}'
  ].map(parseVoiceTurnBlock);
  const conversation = events.reduce((state, event) => (event ? reduceRelayEvent(state, event) : state), EMPTY_CONVERSATION);
  expect(conversation.problem).toBe("Couldn't answer that.");
  expect(conversation.turns).toEqual([
    { turnId: "bd260d55-39e8-5cbf-9e4d-8dbe58ea75df", ordinal: 1, heard: "What is alum?", answerId: null, sentences: [], spoken: "", actions: [] }
  ]);
});

test("the recording type is the first the session accepts that the browser records", () => {
  expect(recordingTypes((type) => type === "audio/ogg" || type === "audio/mp4")).toEqual(["audio/ogg", "audio/mp4"]);
  expect(pickRecordingType(["audio/webm", "audio/ogg", "audio/mp4", "audio/wav"], ["audio/mp4", "audio/ogg"])).toBe("audio/ogg");
  expect(pickRecordingType(["audio/wav"], ["audio/webm"])).toBeNull();
});

test("a relay recording is named by the naming convention", () => {
  const capturedAt = new Date(Date.UTC(2026, 10, 16, 10, 34, 12));
  expect(recordingFileName("audio/webm", capturedAt, "Kutch Ajrakh")).toBe("KalaVigyan_Voice-Session_2026-11-16_1604_Kutch-Ajrakh_Recording.webm");
  expect(recordingFileName("audio/mp4", capturedAt, null)).toBe("KalaVigyan_Voice-Session_2026-11-16_1604_Recording.m4a");
  expect(() => recordingFileName("audio/flac", capturedAt, null)).toThrow(RangeError);
});

test("offer_image needs the media options to offer that stage an image today", () => {
  const options = parseShape(mediaOptionsShape, golden("media.options.golden.json"));
  expect([...offeredStageIds(options, "IMAGE")]).toEqual([STAGE_ID, "eb895bd5-83a3-511a-9e64-ba7e452afea8"]);
  expect(offeredStageIds(options, "VIDEO").size).toBe(0);
  expect(offeredStageIds({ ...options, kinds: [{ kind: "IMAGE", remainingToday: 0 }] }, "IMAGE").size).toBe(0);
  expect(offeredStageIds({ ...options, kinds: [{ kind: "IMAGE", remainingToday: null }] }, "IMAGE").size).toBe(2);
});

test("the craft page names the stages it drew, by id", () => {
  const process = parseShape(craftProcessShape, golden("science.process.golden.json"));
  const names = shownStageNames(process);
  expect(names.size).toBe(3);
  expect(names.has(STAGE_ID)).toBe(true);
  expect(shownStageNames(null).size).toBe(0);
});

test("the call clock reads as minutes and seconds", () => {
  expect(formatClock(540)).toBe("9:00");
  expect(formatClock(59.2)).toBe("1:00");
  expect(formatClock(5)).toBe("0:05");
  expect(formatClock(-3)).toBe("0:00");
  expect(spokenClock(541)).toBe("9 minutes 1 second");
  expect(spokenClock(120)).toBe("2 minutes");
  expect(spokenClock(0)).toBe("0 seconds");
});

test("microphone refusals and server sentences become short messages", () => {
  expect(voiceFailure(new DOMException("denied", "NotAllowedError"), "x")).toBe("Allow the microphone to talk.");
  expect(voiceFailure(new DOMException("none", "NotFoundError"), "x")).toBe("No microphone found.");
  expect(voiceFailure(new TypeError("Failed to fetch"), "Couldn't start voice. Try again.")).toBe("Couldn't start voice. Try again.");
});

test("an ElevenLabs disconnect says who ended the call", () => {
  expect(agentEndOf({ reason: "user" })).toEqual({ by: "user", message: null });
  expect(agentEndOf({ reason: "agent" })).toEqual({ by: "agent", message: null });
  expect(agentEndOf({ reason: "error", message: "ICE failed", context: { type: "error" } })).toEqual({ by: "error", message: "ICE failed" });
});

test("the CSP lets the browser reach the ElevenLabs hosts the pinned SDK connects to", async () => {
  const sdk = join(__dirname, "..", "node_modules", "@elevenlabs", "client", "dist", "utils");
  const location = readFileSync(join(sdk, "location.js"), "utf8");
  const webrtc = readFileSync(join(sdk, "WebRTCConnection.js"), "utf8");
  const livekit = /global:\s*"(wss:\/\/[^"]+)"/g;
  const hosts = [...location.matchAll(livekit)].map((match) => match[1]).filter((url) => url.includes("livekit"));
  expect(hosts).toEqual(["wss://livekit.rtc.elevenlabs.io"]);
  expect(webrtc).toContain('const DEFAULT_LIVEKIT_WS_URL = "wss://livekit.rtc.elevenlabs.io"');
  expect(ELEVENLABS_CONNECT_SOURCES).toEqual(["wss://livekit.rtc.elevenlabs.io", "https://livekit.rtc.elevenlabs.io"]);
  const rules = await nextConfig.headers!();
  const csp = rules[0].headers.find((header) => header.key === "Content-Security-Policy")?.value;
  expect(csp).toBe(CONTENT_SECURITY_POLICY);
  const connect = csp?.split("; ").find((directive) => directive.startsWith("connect-src "))?.split(" ") ?? [];
  expect(connect).toEqual([
    "connect-src",
    "'self'",
    "https://accounts.google.com/gsi/",
    "wss://livekit.rtc.elevenlabs.io",
    "https://livekit.rtc.elevenlabs.io",
    "https://kalavigyan-media-626159998512.s3.ap-south-1.amazonaws.com"
  ]);
  expect(csp).toContain("frame-ancestors 'none'");
});
