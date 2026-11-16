import type { Activity, VoiceCallState } from "@/lib/voiceCall";

const RELAY_WORD: Record<Activity, string> = {
  connecting: "Connecting…",
  ready: "Tap to talk",
  recording: "Listening · tap to send",
  thinking: "Thinking…",
  speaking: "Speaking · tap to talk",
  listening: "Listening"
};

const AGENT_WORD: Record<Activity, string> = {
  connecting: "Connecting…",
  ready: "Listening",
  recording: "Listening",
  thinking: "Thinking…",
  speaking: "Speaking",
  listening: "Listening"
};

const ORB_LABEL: Partial<Record<Activity, string>> = {
  ready: "Start talking",
  recording: "Send",
  speaking: "Stop and talk"
};

export function statusWord(state: VoiceCallState): string {
  if (state.phase === "consent" || state.phase === "idle") return "";
  if (state.phase === "starting") return "Starting…";
  if (state.phase === "ending") return "Ending…";
  if (state.phase !== "live" || state.activity === null) return state.message ?? "";
  if (state.activity === "thinking" && state.conversation.status) return state.conversation.status;
  return (state.session?.transport === "AGENT" ? AGENT_WORD : RELAY_WORD)[state.activity];
}

export function orbLabel(activity: Activity | null): string | null {
  return activity ? (ORB_LABEL[activity] ?? null) : null;
}
