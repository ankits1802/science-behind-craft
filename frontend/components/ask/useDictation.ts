"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

import type { AnswerLanguage } from "@/lib/answerLanguages";
import {
  composeQuestion,
  DICTATION_STOPPED,
  dictationFailure,
  dictationLocale,
  localeOffered,
  openDictation,
  recogniserClass,
  spokenText,
  type DictationSession,
  type RecogniserClass
} from "@/lib/dictation";

export type Dictation = {
  offered: boolean;
  listening: boolean;
  failure: string | null;
  start: (base: string) => void;
  stop: () => void;
  abort: () => void;
};

function subscribeNever(): () => void {
  return () => undefined;
}

function browserRecogniser(): RecogniserClass | null {
  return recogniserClass(window);
}

function serverRecogniser(): RecogniserClass | null {
  return null;
}

function useLocaleVerdicts(Recogniser: RecogniserClass | null, locale: string | null) {
  const [verdicts, setVerdicts] = useState<Readonly<Record<string, boolean>>>({});
  const pending = Recogniser !== null && locale !== null && verdicts[locale] === undefined;
  useEffect(() => {
    if (!pending || !Recogniser || !locale) return;
    let cancelled = false;
    void localeOffered(Recogniser, locale).then((offered) => {
      if (!cancelled) setVerdicts((current) => ({ ...current, [locale]: offered }));
    });
    return () => {
      cancelled = true;
    };
  }, [Recogniser, locale, pending]);
  const refuse = useCallback((refused: string) => setVerdicts((current) => ({ ...current, [refused]: false })), []);
  return { offered: locale !== null && verdicts[locale] === true, refuse };
}

export function useDictation(language: AnswerLanguage, onText: (text: string) => void, limit: number): Dictation {
  const Recogniser = useSyncExternalStore(subscribeNever, browserRecogniser, serverRecogniser);
  const locale = dictationLocale(language.code);
  const { offered, refuse } = useLocaleVerdicts(Recogniser, locale);
  const [listening, setListening] = useState(false);
  const [failure, setFailure] = useState<{ locale: string; message: string } | null>(null);
  const session = useRef<DictationSession | null>(null);
  const write = useRef(onText);

  useEffect(() => {
    write.current = onText;
  });

  useEffect(() => () => session.current?.abort(), [locale]);

  const start = useCallback(
    (base: string) => {
      if (!Recogniser || !locale || session.current) return;
      setFailure(null);
      const fail = (message: string | null) => setFailure(message ? { locale, message } : null);
      let mine: DictationSession | null = null;
      try {
        mine = openDictation(Recogniser, locale, {
          onHeard: (heard) => write.current(composeQuestion(base, spokenText(heard), limit)),
          onFailure: (code) => {
            const found = dictationFailure(code, language);
            if (found?.refusesLanguage) refuse(locale);
            fail(found?.message ?? null);
          },
          onEnd: () => {
            if (session.current !== mine) return;
            session.current = null;
            setListening(false);
          }
        });
      } catch (error) {
        console.error(error);
        fail(DICTATION_STOPPED);
        return;
      }
      session.current = mine;
      setListening(true);
    },
    [Recogniser, language, limit, locale, refuse]
  );

  const stop = useCallback(() => session.current?.stop(), []);
  const abort = useCallback(() => session.current?.abort(), []);

  const shownFailure = failure !== null && failure.locale === locale ? failure.message : null;
  return { offered: Recogniser !== null && offered, listening, failure: shownFailure, start, stop, abort };
}
