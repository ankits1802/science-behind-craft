import { apiFetch, ApiError } from "@/lib/api";
import { openEventStream, readSseBlocks } from "@/lib/answerStream";
import { parseShape } from "@/lib/shape";
import {
  CONSENT_PATH,
  parseVoiceTurnBlock,
  VOICE_CONSENT_HEADER,
  VOICE_NOTICE_PATH,
  VOICE_SESSION_END_PATH,
  VOICE_SESSION_PATH,
  VOICE_TRANSCRIPT_PATH,
  VOICE_TURN_PATH,
  voiceNoticeShape,
  voiceSessionEndedShape,
  voiceSessionStartedShape,
  voiceTranscriptShape,
  type VoiceNotice,
  type VoiceSessionEnded,
  type VoiceSessionRequest,
  type VoiceSessionStarted,
  type VoiceTranscript,
  type VoiceTurnEvent
} from "@/lib/voiceContract";

export class VoiceConsentRequired extends Error {
  constructor(readonly version: string) {
    super("Voice notice not yet accepted");
    this.name = "VoiceConsentRequired";
  }
}

export function consentVersionOf(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.status !== 403) return null;
  const version = (error.headers?.get(VOICE_CONSENT_HEADER) ?? "").trim();
  return version || null;
}

export async function fetchVoiceNotice(): Promise<VoiceNotice> {
  return parseShape(voiceNoticeShape, await apiFetch<unknown>(VOICE_NOTICE_PATH));
}

export async function acceptVoiceNotice(version: string): Promise<void> {
  await apiFetch<unknown>(CONSENT_PATH, { method: "POST", body: JSON.stringify({ kind: "VOICE_NOTICE", noticeVersion: version }) });
}

export async function startVoiceSession(request: VoiceSessionRequest): Promise<VoiceSessionStarted> {
  try {
    return parseShape(voiceSessionStartedShape, await apiFetch<unknown>(VOICE_SESSION_PATH, { method: "POST", body: JSON.stringify(request) }));
  } catch (error) {
    const version = consentVersionOf(error);
    if (version) throw new VoiceConsentRequired(version);
    throw error;
  }
}

export async function endVoiceSession(voiceSessionId: string, keepalive = false): Promise<VoiceSessionEnded> {
  return parseShape(voiceSessionEndedShape, await apiFetch<unknown>(VOICE_SESSION_END_PATH(voiceSessionId), { method: "POST", keepalive }));
}

export async function fetchVoiceTranscript(voiceSessionId: string): Promise<VoiceTranscript> {
  return parseShape(voiceTranscriptShape, await apiFetch<unknown>(VOICE_TRANSCRIPT_PATH(voiceSessionId)));
}

export async function streamRelayTurn(voiceSessionId: string, recording: File, onEvent: (event: VoiceTurnEvent) => void, signal?: AbortSignal): Promise<void> {
  const form = new FormData();
  form.append("audio", recording, recording.name);
  const stream = await openEventStream(VOICE_TURN_PATH(voiceSessionId), { body: form, json: false, signal, fallback: "Couldn't hear that. Try again." });
  await readSseBlocks(stream, (block) => {
    const event = parseVoiceTurnBlock(block);
    if (event) onEvent(event);
  });
}
