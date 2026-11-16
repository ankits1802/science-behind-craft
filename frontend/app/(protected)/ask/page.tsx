"use client";

import dynamic from "next/dynamic";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { RotateCw } from "lucide-react";

import { AnswerView } from "@/components/answer/AnswerView";
import { NotEnoughEvidence } from "@/components/answer/NotEnoughEvidence";
import { AskBox } from "@/components/ask/AskBox";
import { useAnswerStream } from "@/components/ask/useAnswerStream";
import { useAuth } from "@/components/AuthProvider";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { useGsapHeadline } from "@/components/guide/useGsapHeadline";
import { LanguagePicker } from "@/components/LanguagePicker";
import { useThemePreferences } from "@/components/ThemeProvider";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { useVoiceOffered } from "@/components/voice/useVoiceOffer";
import { detectedLanguage, englishOf, languageFor, resolvedLanguage } from "@/lib/answerLanguages";
import { FALLBACK_ASK_CONFIG, fetchAskConfig, normaliseAskConfig, type AskConfig } from "@/lib/askConfig";
import { useCraftCatalogue } from "@/lib/craftCatalogue";
import { canAskDeep } from "@/lib/permissions";
import type { AnswerMode } from "@/lib/types";

const VoicePanel = dynamic(() => import("@/components/voice/VoicePanel").then((module) => module.VoicePanel), { ssr: false });

const STARTERS = ["Why does alum fix madder dye on cotton?", "What happens to clay when terracotta is fired?", "How does indigo turn blue on the cloth?"];

export default function AskPage() {
  return (
    <Suspense fallback={null}>
      <AskScreen />
    </Suspense>
  );
}

function AskScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const reduce = useAppReducedMotion();
  const headline = useGsapHeadline<HTMLHeadingElement>(reduce);
  const { catalogue } = useCraftCatalogue();
  const { state, ask, stop, clear } = useAnswerStream();
  const { preferences, update } = useThemePreferences();
  const [config, setConfig] = useState<AskConfig>(FALLBACK_ASK_CONFIG);
  const [configReady, setConfigReady] = useState(false);
  const [question, setQuestion] = useState(() => params.get("q") ?? "");
  const [craftSlug, setCraftSlug] = useState<string | null>(() => params.get("craft"));
  const [mode, setMode] = useState<AnswerMode>("HYBRID");
  const [voiceOpen, setVoiceOpen] = useState(false);
  const autoAsked = useRef(false);

  useEffect(() => {
    let cancelled = false;
    fetchAskConfig()
      .then((raw) => {
        if (cancelled) return;
        const next = normaliseAskConfig(raw);
        setConfig(next);
        setMode((current) => (next.modes.includes(current) ? current : next.defaultMode));
        setConfigReady(true);
      })
      .catch(() => {
        if (!cancelled) setConfigReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const modes = useMemo(() => config.modes.filter((value) => value !== "DEEP" || canAskDeep(user)), [config.modes, user]);
  const craftName = useMemo(() => {
    if (!craftSlug) return null;
    return catalogue?.crafts.find((craft) => craft.slug === craftSlug)?.name ?? craftSlug;
  }, [catalogue, craftSlug]);

  const busy = state.phase === "matching" || state.phase === "streaming";
  const choice = preferences.answerLanguage;
  const detected = useMemo(() => detectedLanguage(question, config.languages) ?? englishOf(config.languages), [config.languages, question]);
  const voiceOffered = useVoiceOffered(config.voice);

  function run(text: string, slug: string | null = craftSlug, chosen: AnswerMode = mode) {
    const trimmed = text.trim();
    if (!trimmed) return;
    setQuestion(trimmed);
    const search = new URLSearchParams();
    search.set("q", trimmed);
    if (slug) search.set("craft", slug);
    router.replace(`${pathname}?${search.toString()}`, { scroll: false });
    void ask({ question: trimmed, mode: chosen, craftSlug: slug, language: resolvedLanguage(choice, trimmed, config.languages).code });
  }

  useEffect(() => {
    if (autoAsked.current || !configReady) return;
    const initial = params.get("q");
    if (!initial) return;
    autoAsked.current = true;
    void ask({ question: initial, mode: "HYBRID", craftSlug: params.get("craft"), language: resolvedLanguage(choice, initial, config.languages).code });
  }, [ask, params, configReady, choice, config.languages]);

  const started = state.phase !== "idle";

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      {!started ? (
        <header className="pt-4 text-center md:pt-10">
          <p className="eyebrow">KalaVigyan</p>
          <h1 ref={headline} className="display-title mt-3 text-3xl md:text-4xl">
            Ask about any Indian craft.
          </h1>
        </header>
      ) : (
        <h1 className="sr-only">Answer</h1>
      )}

      <AskBox
        value={question}
        onChange={setQuestion}
        onSubmit={() => run(question)}
        onStop={stop}
        busy={busy}
        mode={mode}
        modes={modes}
        onMode={setMode}
        voiceAvailable={voiceOffered}
        onVoice={() => setVoiceOpen(true)}
        craftLabel={craftName}
        onClearCraft={() => setCraftSlug(null)}
        languageControl={
          config.languages.length > 1 ? (
            <LanguagePicker
              value={choice}
              languages={config.languages}
              detected={detected}
              onChange={(next) => update({ answerLanguage: next })}
              disabled={busy}
            />
          ) : null
        }
      />

      {!started ? (
        <ActionGroup>
          {STARTERS.map((starter) => (
            <button key={starter} type="button" className="field-button-secondary" onClick={() => run(starter)}>
              {starter}
            </button>
          ))}
        </ActionGroup>
      ) : null}

      {state.phase === "ambiguous" && state.match?.status === "AMBIGUOUS" ? (
        <section className="panel p-5" aria-labelledby="which-craft">
          <h2 id="which-craft" className="font-display text-lg font-bold text-ink-900">
            Which craft?
          </h2>
          <ActionGroup align="start" className="mt-3">
            {state.match.candidates.map((candidate) => (
              <button
                key={candidate.slug}
                type="button"
                className="field-button-secondary"
                onClick={() => {
                  setCraftSlug(candidate.slug);
                  run(question, candidate.slug);
                }}
              >
                {candidate.name}
              </button>
            ))}
          </ActionGroup>
        </section>
      ) : null}

      {state.phase === "failed" ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-red-200 bg-error-100 px-4 py-3 text-sm text-error-600">
          <span>{state.error ?? "Couldn't answer that."}</span>
          <button type="button" className="field-button-secondary min-h-9 px-3 py-1.5 text-xs" onClick={() => run(question)}>
            <RotateCw className="h-3.5 w-3.5" aria-hidden />
            Try again
          </button>
        </div>
      ) : null}

      {started && state.phase !== "ambiguous" ? (
        <AnswerView
          key={`${state.payload.question}:${state.payload.language}`}
          payload={state.payload}
          language={languageFor(state.payload.language, config.languages)}
          streaming={busy}
          status={state.status}
          onFollowUp={(next) => {
            clear();
            run(next);
          }}
        />
      ) : null}

      {state.phase === "empty" && state.notice ? (
        <NotEnoughEvidence
          message={state.notice}
          onResearch={
            state.payload.mode === "VERIFIED" && modes.includes("HYBRID")
              ? () => {
                  setMode("HYBRID");
                  run(question, craftSlug, "HYBRID");
                }
              : undefined
          }
        />
      ) : null}

      {voiceOffered ? (
        <VoicePanel
          open={voiceOpen}
          onClose={() => setVoiceOpen(false)}
          craftSlug={craftSlug}
          mode={mode}
          question={question}
          availability={config.voice}
          onTranscript={(text) => setQuestion(text)}
        />
      ) : null}
    </div>
  );
}
