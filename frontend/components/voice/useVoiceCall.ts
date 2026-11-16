"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

import { connectAgent } from "@/lib/elevenLabsAgent";
import { fetchMediaOptions, offeredStageIds } from "@/lib/mediaContract";
import { AgentTransport } from "@/lib/voiceAgent";
import { VoiceCall, type TransportFactory, type VoiceCallDeps, type VoiceCallOptions, type VoiceCallState } from "@/lib/voiceCall";
import type { VoiceSessionStarted } from "@/lib/voiceContract";
import { detectVoiceSupport, playSpeech, startRecording } from "@/lib/voiceDevice";
import { RelayTransport } from "@/lib/voiceRelay";
import { acceptVoiceNotice, endVoiceSession, fetchVoiceNotice, fetchVoiceTranscript, startVoiceSession, streamRelayTurn } from "@/lib/voiceSession";

const TRANSPORTS: Record<VoiceSessionStarted["transport"], TransportFactory> = {
  AGENT: (host) => new AgentTransport(host),
  RELAY: (host) => new RelayTransport(host)
};

function browserVoiceDeps(): VoiceCallDeps {
  return {
    api: {
      notice: fetchVoiceNotice,
      accept: acceptVoiceNotice,
      start: startVoiceSession,
      end: endVoiceSession,
      transcript: fetchVoiceTranscript,
      turn: streamRelayTurn
    },
    connectAgent,
    record: startRecording,
    play: playSpeech,
    imageStages: async (craftSlug) => offeredStageIds(await fetchMediaOptions(craftSlug), "IMAGE"),
    recordingTypes: detectVoiceSupport().relayTypes,
    now: () => Date.now(),
    schedule: (ms, run) => {
      const timer = setTimeout(run, ms);
      return () => clearTimeout(timer);
    }
  };
}

export function useVoiceCall(open: boolean, options: VoiceCallOptions): { call: VoiceCall; state: VoiceCallState } {
  const [call] = useState(() => new VoiceCall(browserVoiceDeps(), TRANSPORTS));
  const state = useSyncExternalStore(call.subscribe, call.getState, call.getState);

  useEffect(() => {
    call.configure(options);
  });

  useEffect(() => {
    if (!open) return;
    call.begin();
    const leave = (event: PageTransitionEvent) => {
      if (!event.persisted) call.abandon();
    };
    window.addEventListener("pagehide", leave);
    return () => {
      window.removeEventListener("pagehide", leave);
      call.dispose();
    };
  }, [call, open]);

  return { call, state };
}
