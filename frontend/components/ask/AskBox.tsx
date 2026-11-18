"use client";

import type { ReactNode } from "react";

import { DictationControl } from "@/components/ask/DictationControl";
import type { Dictation } from "@/components/ask/useDictation";
import { ActionGroup } from "@/components/ui/ActionGroup";
import type { AnswerLanguage } from "@/lib/answerLanguages";
import { QUESTION_MAX } from "@/lib/askRequest";

function stopAction(dictation: Dictation, busy: boolean, onStop: () => void): { label: string; act: () => void } | null {
  if (dictation.listening) return { label: "Stop dictation", act: dictation.stop };
  return busy ? { label: "Stop the answer", act: onStop } : null;
}

export function AskBox({
  value,
  onChange,
  onSubmit,
  onStop,
  busy,
  canAsk,
  dictation,
  language,
  options
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  busy: boolean;
  canAsk: boolean;
  dictation: Dictation;
  language: AnswerLanguage;
  options: ReactNode;
}) {
  const stop = stopAction(dictation, busy, onStop);
  return (
    <form
      className="panel grid gap-4 p-4 shadow-lg md:p-[22px]"
      onSubmit={(event) => {
        event.preventDefault();
        if (canAsk) onSubmit();
      }}
      data-testid="ask-box"
    >
      <label htmlFor="ask-question" className="sr-only">
        Your question
      </label>
      <textarea
        id="ask-question"
        value={value}
        maxLength={QUESTION_MAX}
        rows={2}
        dir="auto"
        readOnly={dictation.listening}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Escape" && dictation.listening) {
            event.preventDefault();
            dictation.stop();
            return;
          }
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            if (canAsk) onSubmit();
          }
        }}
        placeholder="Why does alum fix madder on cotton?"
        className="min-h-16 w-full resize-none bg-transparent px-1 text-[17px] leading-relaxed text-ink-900 placeholder:text-ink-300 md:text-xl"
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <DictationControl dictation={dictation} language={language} onStart={() => dictation.start(value)} />
        <ActionGroup inline align="end" className="max-sm:w-full">
          {stop ? (
            <button type="button" onClick={stop.act} aria-label={stop.label} className="field-button-secondary min-h-11 rounded-full px-5">
              Stop
            </button>
          ) : null}
          <button type="submit" disabled={!canAsk} className="field-button min-h-11 px-6 text-[15px] font-semibold">
            Ask
          </button>
        </ActionGroup>
      </div>
      {options}
    </form>
  );
}
