import { fileName } from "@/lib/naming";
import { RELAY_AUDIO_TYPES } from "@/lib/voiceContract";
import { NO_VOICE_SUPPORT, type VoiceSupport } from "@/lib/voiceRules";

type RelayAudioType = (typeof RELAY_AUDIO_TYPES)[number];

const RECORDING_EXTENSION: Record<RelayAudioType, string> = {
  "audio/webm": "webm",
  "audio/ogg": "ogg",
  "audio/mp4": "m4a",
  "audio/wav": "wav"
};

const LEVEL_GAIN = 4;
const TIMESLICE_MS = 250;
const FULL_FRACTION = 0.9;

function isRelayAudioType(type: string): type is RelayAudioType {
  return (RELAY_AUDIO_TYPES as readonly string[]).includes(type);
}

export function recordingTypes(isTypeSupported: (type: string) => boolean): string[] {
  return RELAY_AUDIO_TYPES.filter((type) => isTypeSupported(type));
}

export function pickRecordingType(offered: readonly string[], supported: readonly string[]): string | null {
  return offered.find((type) => supported.includes(type)) ?? null;
}

export function recordingFileName(type: string, capturedAt: Date, craftName: string | null): string {
  if (!isRelayAudioType(type)) throw new RangeError(`not a relay audio type: ${type}`);
  return fileName({ entity: "Voice-Session", what: "Recording", ext: RECORDING_EXTENSION[type], date: capturedAt, time: true, craft: craftName });
}

export function detectVoiceSupport(): VoiceSupport {
  if (typeof window === "undefined" || typeof navigator.mediaDevices?.getUserMedia !== "function") return NO_VOICE_SUPPORT;
  const agent = typeof RTCPeerConnection === "function" && typeof AudioWorkletNode === "function";
  const relayTypes = typeof MediaRecorder === "function" ? recordingTypes((type) => MediaRecorder.isTypeSupported(type)) : [];
  return { agent, relayTypes };
}

export type Recording = {
  stop: () => Promise<File>;
  cancel: () => void;
  level: () => number;
};

export type RecordingLimits = { bitsPerSecond: number; maxBytes: number; onFull: () => void };

export function fullAt(maxBytes: number): number {
  return Math.floor(maxBytes * FULL_FRACTION);
}

export async function startRecording(type: string, name: string, limits: RecordingLimits): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  const recorder = new MediaRecorder(stream, { mimeType: type, audioBitsPerSecond: limits.bitsPerSecond });
  const chunks: Blob[] = [];
  let recorded = 0;
  recorder.addEventListener("dataavailable", (event) => {
    if (event.data.size === 0) return;
    chunks.push(event.data);
    recorded += event.data.size;
    if (recorded >= fullAt(limits.maxBytes) && recorder.state === "recording") limits.onFull();
  });
  const context = new AudioContext();
  const analyser = context.createAnalyser();
  analyser.fftSize = 512;
  context.createMediaStreamSource(stream).connect(analyser);
  const samples = new Float32Array(analyser.fftSize);
  const release = () => {
    stream.getTracks().forEach((track) => track.stop());
    void context.close();
  };
  const stopped = new Promise<File>((resolve) => {
    recorder.addEventListener("stop", () => {
      release();
      resolve(new File(chunks, name, { type }));
    });
  });
  recorder.start(TIMESLICE_MS);
  return {
    stop: () => {
      if (recorder.state !== "inactive") recorder.stop();
      return stopped;
    },
    cancel: () => {
      chunks.length = 0;
      if (recorder.state !== "inactive") recorder.stop();
    },
    level: () => {
      analyser.getFloatTimeDomainData(samples);
      let sum = 0;
      for (const sample of samples) sum += sample * sample;
      return Math.min(1, Math.sqrt(sum / samples.length) * LEVEL_GAIN);
    }
  };
}

export function playSpeech(path: string, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const audio = new Audio(path);
    const silence = () => {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    };
    audio.addEventListener("ended", () => resolve(), { once: true });
    audio.addEventListener("error", () => reject(new Error(`speech playback failed (${audio.error?.code ?? "unknown"})`)), { once: true });
    signal.addEventListener(
      "abort",
      () => {
        silence();
        resolve();
      },
      { once: true }
    );
    audio.play().catch(reject);
  });
}
