"use client";

import { PhoneOff, RotateCw } from "lucide-react";

import { ActionGroup } from "@/components/ui/ActionGroup";
import type { VoicePhase } from "@/lib/voiceCall";

export function VoiceControls({
  phase,
  onEnd,
  onAgain,
  onClose
}: {
  phase: VoicePhase;
  onEnd: () => void;
  onAgain: () => void;
  onClose: () => void;
}) {
  if (phase === "starting" || phase === "live") {
    return (
      <ActionGroup fill>
        <button type="button" className="field-button" onClick={onEnd} data-testid="voice-end">
          <PhoneOff className="h-4 w-4" aria-hidden />
          End
        </button>
      </ActionGroup>
    );
  }
  if (phase === "ended" || phase === "failed") {
    return (
      <ActionGroup>
        <button type="button" className="field-button-secondary" onClick={onClose}>
          Close
        </button>
        <button type="button" className="field-button" onClick={onAgain}>
          <RotateCw className="h-4 w-4" aria-hidden />
          {phase === "failed" ? "Try again" : "Talk again"}
        </button>
      </ActionGroup>
    );
  }
  return null;
}
