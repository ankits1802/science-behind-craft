"use client";

import { useEffect, useMemo } from "react";
import { Loader2, MessageCircleQuestion, RotateCw } from "lucide-react";

import { CitationProvider, type CitationLookup } from "@/components/answer/CitationContext";
import { ExplainerSentence } from "@/components/answer/ExplainerSentence";
import type { OpenCitation } from "@/components/answer/SourceDialog";
import { FieldDialog } from "@/components/dialogs/FieldDialog";
import { failureMessage, useRemote } from "@/components/hooks/useRemote";
import type { Term, TermSpan } from "@/lib/explainerContract";
import { fetchTerm } from "@/lib/termSummary";

type Looked = { key: string; term: Term | null };

function useTermSummary(span: TermSpan | null, language: string) {
  const load = useMemo(() => (span ? (): Promise<Looked> => fetchTerm(span.termKey, language).then((term) => ({ key: span.termKey, term })) : null), [span, language]);
  return useRemote(load);
}

function termLookup(term: Term, onOpen: (open: OpenCitation) => void): CitationLookup {
  const numbers = new Map(term.sources.map((source, index) => [source.id, index + 1]));
  const sourcesById = new Map(term.sources.map((source) => [source.id, source]));
  return {
    numbers,
    sourcesById,
    onOpen: (citation) => onOpen({ citation, source: sourcesById.get(citation.sourceId) ?? null, number: numbers.get(citation.sourceId) ?? null })
  };
}

function TermBody({ term, onOpen }: { term: Term; onOpen: (open: OpenCitation) => void }) {
  const lookup = useMemo(() => termLookup(term, onOpen), [term, onOpen]);
  return (
    <CitationProvider value={lookup}>
      <p className="mt-3 text-[15px] leading-7 text-ink-700" data-testid="term-summary">
        {term.summary.map((sentence) => (
          <ExplainerSentence key={sentence.id} sentence={{ ...sentence, terms: [] }} />
        ))}
      </p>
    </CitationProvider>
  );
}

export function TermSheet({
  span,
  language,
  onClose,
  onMissing,
  onAsk,
  onOpenCitation
}: {
  span: TermSpan | null;
  language: string;
  onClose: () => void;
  onMissing: (termKey: string) => void;
  onAsk: ((term: Term) => void) | null;
  onOpenCitation: (open: OpenCitation) => void;
}) {
  const remote = useTermSummary(span, language);
  const looked = remote.data && span && remote.data.key === span.termKey ? remote.data : null;
  const term = looked?.term ?? null;
  const missing = looked !== null && term === null;

  useEffect(() => {
    if (missing && span) onMissing(span.termKey);
  }, [missing, span, onMissing]);

  return (
    <FieldDialog
      open={span !== null && !missing}
      onClose={onClose}
      title={term?.label ?? span?.text ?? ""}
      description={term && term.localNames.length > 0 ? `Also called ${term.localNames.join(", ")}` : undefined}
      className="max-w-lg"
      footer={
        <>
          {term && onAsk ? (
            <button type="button" className="field-button" onClick={() => onAsk(term)}>
              <MessageCircleQuestion className="h-4 w-4" aria-hidden />
              Ask about it
            </button>
          ) : null}
          <button type="button" className="field-button-secondary" onClick={onClose}>
            Close
          </button>
        </>
      }
    >
      {term ? <TermBody term={term} onOpen={onOpenCitation} /> : null}
      {!term && !remote.failure ? (
        <p role="status" className="mt-3 flex items-center gap-2 text-sm text-ink-500">
          <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden />
          Looking it up…
        </p>
      ) : null}
      {remote.failure ? (
        <div role="alert" className="mt-3 flex flex-wrap items-center gap-3 text-sm text-error-600">
          <span>{failureMessage(remote.failure, "Couldn't load this term.")}</span>
          <button type="button" className="field-button-secondary min-h-9 px-3 py-1.5 text-xs" onClick={remote.retry}>
            <RotateCw className="h-3.5 w-3.5" aria-hidden />
            Try again
          </button>
        </div>
      ) : null}
    </FieldDialog>
  );
}
