"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import type { UnderstoodChange } from "@/components/answer/UnderstoodLine";
import { focusAskOption, type AskOptionsProps } from "@/components/ask/AskOptions";
import { useAnswerStream } from "@/components/ask/useAnswerStream";
import { useAskConfig } from "@/components/ask/useAskConfig";
import { useDictation } from "@/components/ask/useDictation";
import { useAuth } from "@/components/AuthProvider";
import { useThemePreferences } from "@/components/ThemeProvider";
import { resolvedLanguage } from "@/lib/answerLanguages";
import type { AskRequest } from "@/lib/answerStream";
import { changeableParts, type AskConfig } from "@/lib/askConfig";
import { craftOptions, pickForQuestion, samePick, type CraftPick } from "@/lib/askCraft";
import { askedDepth, depthLabel, depthParam } from "@/lib/askDepth";
import { askable, plannedAsk, QUESTION_MAX, reasksOnChange, type AskChange, type AskSettings } from "@/lib/askRequest";
import { useCraftCatalogue } from "@/lib/craftCatalogue";
import type { Depth } from "@/lib/explainerContract";

function useAskSettings(config: AskConfig) {
  const params = useSearchParams();
  const { preferences, update } = useThemePreferences();
  const [question, setQuestion] = useState(() => params.get("q") ?? "");
  const [pick, setPick] = useState<CraftPick>(() => ({ craftSlug: params.get("craft"), anyCraft: false }));
  const [pickedDepth, setPickedDepth] = useState<Depth | null>(() => depthParam(params.get("depth")));
  const languageChoice = preferences.answerLanguage;
  const settings = useMemo<AskSettings>(
    () => ({ pick, depth: askedDepth(pickedDepth, config), pickedDepth, languageChoice, languages: config.languages }),
    [pick, pickedDepth, config, languageChoice]
  );
  return { params, question, setQuestion, setPick, setPickedDepth, update, settings };
}

function useAutoAsk(params: URLSearchParams, settings: AskSettings | null, ask: (request: AskRequest) => Promise<void>): () => void {
  const asked = useRef(false);
  useEffect(() => {
    if (asked.current || !settings) return;
    const initial = params.get("q");
    if (!initial) return;
    asked.current = true;
    const planned = plannedAsk(initial, settings);
    if (planned) void ask(planned.request);
  }, [ask, params, settings]);
  return useCallback(() => {
    asked.current = true;
  }, []);
}

export function useAskScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const { catalogue } = useCraftCatalogue();
  const { config, ready } = useAskConfig();
  const { state, round, ask, stop, clear } = useAnswerStream();
  const { params, question, setQuestion, setPick, setPickedDepth, update, settings } = useAskSettings(config);
  const language = resolvedLanguage(settings.languageChoice, question, config.languages);
  const dictation = useDictation(language, setQuestion, QUESTION_MAX);
  const settleAutoAsk = useAutoAsk(params, ready && user ? settings : null, ask);
  const craftChoices = useMemo(() => craftOptions(catalogue, settings.pick, state.understood), [catalogue, settings.pick, state.understood]);
  const asked = state.question;
  const busy = state.phase === "asking" || state.phase === "streaming";
  const reask = reasksOnChange(state.phase !== "idle", asked, question);

  function run(text: string, change: AskChange = {}) {
    const pick = change.pick ?? pickForQuestion(settings.pick, asked, text);
    const planned = plannedAsk(text, settings, { ...change, pick });
    if (!planned) return;
    settleAutoAsk();
    dictation.abort();
    if (!samePick(pick, settings.pick)) setPick(pick);
    setQuestion(planned.request.question);
    router.replace(`${pathname}?${planned.search}`, { scroll: false });
    void ask(planned.request);
  }

  function choose(next: AskChange, keep: () => void) {
    keep();
    if (reask) run(question, next);
  }

  const options: AskOptionsProps = {
    understood: state.understood,
    craft: {
      pick: settings.pick,
      options: craftChoices,
      onPick: (next) => {
        if (!samePick(next, settings.pick)) choose({ pick: next }, () => setPick(next));
      }
    },
    depth: { value: settings.depth, options: config.depths, onPick: (next) => choose({ depth: next }, () => setPickedDepth(next)) },
    language: { choice: settings.languageChoice, languages: config.languages, question, onPick: (next) => choose({ languageChoice: next }, () => update({ answerLanguage: next })) }
  };
  const canAsk = askable(question) && !(busy && question.trim() === asked.trim());
  const understood = useMemo<UnderstoodChange>(() => ({ parts: changeableParts(config), onChange: focusAskOption }), [config]);
  const shownDepth = depthLabel(state.understood?.depth, config);
  return { state, round, config, question, setQuestion, language, dictation, busy, canAsk, options, understood, shownDepth, run, stop, clear };
}
