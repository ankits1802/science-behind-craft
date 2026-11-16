import type { DisconnectionDetails } from "@elevenlabs/client";

import { CLIENT_TOOL_NAMES } from "@/lib/voiceContract";

export type AgentEnd = { by: "user" | "agent" | "error"; message: string | null };

export type AgentEvents = {
  onConnected: () => void;
  onSpeaking: (speaking: boolean) => void;
  onUserSpeech: (text: string) => void;
  onAgentReply: () => void;
  onToolCall: (raw: unknown) => Promise<boolean>;
  onEnd: (end: AgentEnd) => void;
};

export type AgentCall = {
  end: () => Promise<void>;
  level: () => number;
};

export function agentEndOf(details: DisconnectionDetails): AgentEnd {
  if (details.reason === "error") return { by: "error", message: details.message || null };
  return { by: details.reason, message: null };
}

export async function connectAgent(conversationToken: string, events: AgentEvents): Promise<AgentCall> {
  const { Conversation } = await import("@elevenlabs/client");
  let speaking = false;
  const clientTools = Object.fromEntries(
    CLIENT_TOOL_NAMES.map((name) => [name, async (parameters: unknown) => ((await events.onToolCall({ name, parameters })) ? "shown" : "ignored")])
  );
  const call = await Conversation.startSession({
    conversationToken,
    connectionType: "webrtc",
    textOnly: false,
    clientTools,
    onConnect: () => events.onConnected(),
    onModeChange: ({ mode }) => {
      speaking = mode === "speaking";
      events.onSpeaking(speaking);
    },
    onMessage: ({ role, message }) => (role === "user" ? events.onUserSpeech(message) : events.onAgentReply()),
    onDisconnect: (details) => events.onEnd(agentEndOf(details)),
    onError: (message) => console.error(new Error(`ElevenLabs: ${message}`))
  });
  return {
    end: () => call.endSession(),
    level: () => (speaking ? call.getOutputVolume() : call.getInputVolume())
  };
}
