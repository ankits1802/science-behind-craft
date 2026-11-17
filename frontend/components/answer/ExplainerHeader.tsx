"use client";

import { Play, RefreshCw } from "lucide-react";

import { UnderstoodLine, type UnderstoodChange } from "@/components/answer/UnderstoodLine";
import { SegmentedChoice } from "@/components/ui/SegmentedChoice";
import { ENGLISH, type AnswerLanguage } from "@/lib/answerLanguages";
import type { Understood } from "@/lib/explainerContract";

export const ORIGINAL_TEXT = "original";
export const TRANSLATED_TEXT = "translated";

export type ShownText = { translated: boolean; original: boolean; onShow: (value: string) => void };

export function ExplainerHeader({
  understood,
  depthLabel,
  language,
  change,
  shown,
  onListen,
  onFresh
}: {
  understood: Understood | null;
  depthLabel: string | null;
  language: AnswerLanguage;
  change: UnderstoodChange;
  shown: ShownText;
  onListen: (() => void) | null;
  onFresh: (() => void) | null;
}) {
  if (!understood && !shown.translated && !onListen && !onFresh) return null;
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      {understood ? <UnderstoodLine understood={understood} depthLabel={depthLabel} language={language} change={change} /> : <span />}
      <div className="flex flex-wrap items-center gap-2">
        {shown.translated ? (
          <SegmentedChoice
            label="Answer text"
            value={shown.original ? ORIGINAL_TEXT : TRANSLATED_TEXT}
            options={[
              { value: TRANSLATED_TEXT, label: language.autonym },
              { value: ORIGINAL_TEXT, label: ENGLISH.label }
            ]}
            onChange={shown.onShow}
          />
        ) : null}
        {onFresh ? (
          <button type="button" className="field-button-secondary min-h-10 rounded-full px-4" onClick={onFresh} data-testid="fresh-research">
            <RefreshCw className="h-4 w-4" aria-hidden />
            Research again
          </button>
        ) : null}
        {onListen ? (
          <button type="button" className="field-button min-h-10 rounded-full px-4" onClick={onListen} data-testid="listen-start">
            <Play className="h-4 w-4" aria-hidden />
            Listen
          </button>
        ) : null}
      </div>
    </div>
  );
}
