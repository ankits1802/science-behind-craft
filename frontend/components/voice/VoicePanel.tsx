"use client";

import { useEffect, useMemo, useRef } from "react";
import { motion } from "framer-motion";
import { Mic } from "lucide-react";

import { riseItem } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { LanguagePicker } from "@/components/LanguagePicker";
import { useThemePreferences } from "@/components/ThemeProvider";
import { useVoiceCall } from "@/components/voice/useVoiceCall";
import { useSecondsLeft } from "@/components/voice/useSecondsLeft";
import { VoiceCallBody } from "@/components/voice/VoiceCallBody";
import { VoiceConsent } from "@/components/voice/VoiceConsent";
import { VoiceControls } from "@/components/voice/VoiceControls";
import { AUTO_LANGUAGE, languageFor } from "@/lib/answerLanguages";
import { formatClock, spokenClock } from "@/lib/format";
import type { AnswerMode } from "@/lib/types";
import type { VoicePhase } from "@/lib/voiceCall";
import type { ClientToolCall, VoiceAvailability } from "@/lib/voiceContract";
import { voiceLanguage, voiceMode, voicePickerValue } from "@/lib/voiceRules";

export type VoiceHost = {
  stages?: ReadonlyMap<string, string>;
  showOnMap?: () => void;
  openStage?: (stageId: string) => void;
};

export type VoicePanelProps = {
  open: boolean;
  onClose: () => void;
  craftSlug: string | null;
  mode: AnswerMode;
  question?: string;
  availability: VoiceAvailability;
  host?: VoiceHost;
  onTranscript?: (text: string) => void;
};

const NO_STAGES: ReadonlyMap<string, string> = new Map();
const LANGUAGE_PHASES: ReadonlySet<VoicePhase> = new Set(["consent", "ended", "failed"]);

function runAction(action: ClientToolCall, host: VoiceHost | undefined): void {
  if (action.name === "show_on_map") host?.showOnMap?.();
  else if (action.name === "open_stage" || action.name === "offer_image") host?.openStage?.(action.parameters.stageId);
}

export function VoicePanel({ open, onClose, craftSlug, mode, question = "", availability, host, onTranscript }: VoicePanelProps) {
  const reduce = useAppReducedMotion();
  const frame = useRef<HTMLElement | null>(null);
  const stages = host?.stages ?? NO_STAGES;
  const { preferences, update } = useThemePreferences();
  const choice = preferences.answerLanguage;
  const chosen = useMemo(() => voiceLanguage(availability, choice, question), [availability, choice, question]);
  const detected = useMemo(() => voiceLanguage(availability, AUTO_LANGUAGE, question), [availability, question]);
  const { call, state } = useVoiceCall(open, {
    request: () => {
      if (!chosen) throw new RangeError("voice offers no language");
      return { craftSlug, mode: voiceMode(mode), language: chosen.code };
    },
    consentVersion: () => (availability.consentRequired ? availability.noticeVersion : null),
    stageIds: () => new Set(stages.keys()),
    onAction: (action) => runAction(action, host),
    onHeard: (text) => onTranscript?.(text)
  });
  const left = useSecondsLeft(state.phase === "live" ? state.startedAt : null, state.session?.maxDurationSeconds ?? null);

  useEffect(() => {
    if (open) frame.current?.focus({ preventScroll: true });
  }, [open]);

  if (!open) return null;
  const craftName = state.session?.craft?.name ?? null;
  const spokenIn = state.session ? languageFor(state.session.language, availability.languages) : chosen;
  const pickable = chosen !== null && detected !== null && availability.languages.length > 1 && LANGUAGE_PHASES.has(state.phase);

  return (
    <motion.section
      ref={frame}
      tabIndex={-1}
      variants={riseItem(reduce, 12)}
      initial="hidden"
      animate="show"
      aria-label="Voice"
      className="fixed inset-x-3 bottom-[calc(var(--bottom-nav-h,0px)+0.75rem)] z-40 sm:left-auto sm:right-6 sm:w-[26rem] lg:bottom-6"
      data-testid="voice-panel"
    >
      <div className="panel flex max-h-[min(40rem,calc(100dvh-8rem))] flex-col shadow-panel">
        <header className="flex items-center gap-3 border-b border-line-200 px-4 py-3">
          <span aria-hidden className="grid h-8 w-8 place-items-center rounded-full bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300">
            <Mic className="h-4 w-4" />
          </span>
          <h2 className="min-w-0 flex-1 truncate font-display text-base font-bold text-ink-900">{craftName ? `Voice · ${craftName}` : "Voice"}</h2>
          {left !== null ? (
            <span className="font-display text-sm font-semibold tabular-nums text-ink-500">
              <span aria-hidden>{formatClock(left)}</span>
              <span className="sr-only">{`${spokenClock(left)} left`}</span>
            </span>
          ) : pickable ? (
            <LanguagePicker
              value={voicePickerValue(availability, choice, chosen)}
              languages={availability.languages}
              detected={detected}
              onChange={(next) => update({ answerLanguage: next })}
              disabled={state.busy}
              ariaLabel="Voice language"
            />
          ) : null}
        </header>
        {state.phase === "consent" ? (
          <div className="min-h-0 overflow-y-auto px-4 py-4">
            <VoiceConsent notice={state.notice} busy={state.busy} problem={state.message} onAccept={() => void call.accept()} onDecline={onClose} />
          </div>
        ) : (
          <VoiceCallBody call={call} state={state} language={spokenIn} host={{ stages, showOnMap: host?.showOnMap, openStage: host?.openStage }} />
        )}
        <footer className="border-t border-line-200 px-4 py-3 empty:hidden">
          <VoiceControls phase={state.phase} onEnd={() => (state.phase === "live" ? void call.end() : onClose())} onAgain={() => call.retry()} onClose={onClose} />
        </footer>
      </div>
    </motion.section>
  );
}
