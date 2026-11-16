"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

import { fetchAskConfig } from "@/lib/askConfig";
import type { VoiceAvailability } from "@/lib/voiceContract";
import { detectVoiceSupport } from "@/lib/voiceDevice";
import { NO_VOICE, NO_VOICE_SUPPORT, voiceAvailabilityOf, voiceOffered, type VoiceSupport } from "@/lib/voiceRules";
import { logUnexpected } from "@/lib/voiceCall";

let detected: VoiceSupport | null = null;

function supportSnapshot(): VoiceSupport {
  detected ??= detectVoiceSupport();
  return detected;
}

function serverSupport(): VoiceSupport {
  return NO_VOICE_SUPPORT;
}

function subscribeNever(): () => void {
  return () => undefined;
}

export function useVoiceSupport(): VoiceSupport {
  return useSyncExternalStore(subscribeNever, supportSnapshot, serverSupport);
}

export function useVoiceOffered(availability: VoiceAvailability): boolean {
  return voiceOffered(availability, useVoiceSupport());
}

export function useVoiceAvailability(): VoiceAvailability {
  const [availability, setAvailability] = useState<VoiceAvailability>(NO_VOICE);
  useEffect(() => {
    let cancelled = false;
    fetchAskConfig()
      .then((raw) => {
        if (!cancelled) setAvailability(voiceAvailabilityOf(raw?.voice));
      })
      .catch(logUnexpected);
    return () => {
      cancelled = true;
    };
  }, []);
  return availability;
}
