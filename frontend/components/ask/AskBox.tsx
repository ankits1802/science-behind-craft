"use client";

import { useRef, type ReactNode } from "react";
import { ArrowUp, Mic, Square } from "lucide-react";

import { SegmentedChoice } from "@/components/ui/SegmentedChoice";
import { MODE_LABEL } from "@/lib/askConfig";
import type { AnswerMode } from "@/lib/types";
import { cn } from "@/lib/utils";

export const QUESTION_MAX = 1000;

export function AskBox({
  value,
  onChange,
  onSubmit,
  onStop,
  busy,
  mode,
  modes,
  onMode,
  voiceAvailable,
  onVoice,
  craftLabel,
  onClearCraft,
  languageControl
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  busy: boolean;
  mode: AnswerMode;
  modes: AnswerMode[];
  onMode: (mode: AnswerMode) => void;
  voiceAvailable: boolean;
  onVoice: () => void;
  craftLabel: string | null;
  onClearCraft: () => void;
  languageControl?: ReactNode;
}) {
  const area = useRef<HTMLTextAreaElement | null>(null);
  const empty = value.trim().length === 0;

  return (
    <form
      className="panel grid gap-3 p-3 shadow-md md:p-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!busy && !empty) onSubmit();
      }}
      data-testid="ask-box"
    >
      {craftLabel ? (
        <div className="flex items-center gap-2 text-xs">
          <span className="rounded-full border border-purple-300 bg-purple-50 px-2.5 py-1 font-semibold text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">
            {craftLabel}
          </span>
          <button type="button" onClick={onClearCraft} className="font-medium text-ink-500 hover:text-ink-900">
            Any craft
          </button>
        </div>
      ) : null}
      <label htmlFor="ask-question" className="sr-only">
        Your question
      </label>
      <textarea
        id="ask-question"
        ref={area}
        value={value}
        maxLength={QUESTION_MAX}
        rows={2}
        dir="auto"
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            if (!busy && !empty) onSubmit();
          }
        }}
        placeholder="Why does alum fix madder on cotton?"
        className="min-h-14 w-full resize-none bg-transparent px-1 text-base leading-7 text-ink-900 outline-hidden placeholder:text-ink-300"
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          {modes.length > 1 ? (
            <SegmentedChoice
              label="Mode"
              value={mode}
              options={modes.map((value) => ({ value, label: MODE_LABEL[value] }))}
              onChange={(next) => onMode(next as AnswerMode)}
              disabled={busy}
            />
          ) : null}
          {languageControl}
        </div>
        <div className="flex items-center gap-2">
          {voiceAvailable ? (
            <button
              type="button"
              onClick={onVoice}
              aria-label="Ask by voice"
              data-testid="voice-button"
              className="grid h-11 w-11 place-items-center rounded-full border border-line-200 bg-card text-ink-700 transition hover:border-purple-300 hover:bg-purple-50 hover:text-purple-700"
            >
              <Mic className="h-5 w-5" aria-hidden />
            </button>
          ) : null}
          {busy ? (
            <button
              type="button"
              onClick={onStop}
              aria-label="Stop"
              className="grid h-11 w-11 place-items-center rounded-full bg-ink-900 text-card transition hover:opacity-90"
            >
              <Square className="h-4 w-4" aria-hidden />
            </button>
          ) : (
            <button
              type="submit"
              disabled={empty}
              aria-label="Ask"
              className={cn(
                "grid h-11 w-11 place-items-center rounded-full bg-purple-700 text-white transition hover:bg-purple-800 hover:shadow-cta",
                "disabled:cursor-not-allowed disabled:bg-line-200 disabled:text-ink-500 disabled:shadow-none"
              )}
            >
              <ArrowUp className="h-5 w-5" aria-hidden />
            </button>
          )}
        </div>
      </div>
    </form>
  );
}
