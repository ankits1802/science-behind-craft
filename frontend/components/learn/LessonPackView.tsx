"use client";

import { useState } from "react";
import { Download, ExternalLink, Loader2 } from "lucide-react";

import { ListedSources } from "@/components/answer/CitedReading";
import { CitationMenu } from "@/components/learn/ExplainerExport";
import { SlidePreview } from "@/components/learn/SlidePreview";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { apiErrorMessage } from "@/lib/api";
import { sourceByline, sourceHref, sourceReliabilityLabel } from "@/lib/citations";
import { countNoun, formatDate } from "@/lib/format";
import { downloadLessonFile, FILE_FAILED } from "@/lib/lessonApi";
import type { LessonFormat, LessonPack, ReadingItem } from "@/lib/lessonContract";
import { LESSON_FORMAT_LABEL, LESSON_FORMAT_ORDER, slideCountText } from "@/lib/lessonView";

function LessonFiles({ pack }: { pack: LessonPack }) {
  const [busy, setBusy] = useState<LessonFormat | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function fetchFile(format: LessonFormat) {
    setBusy(format);
    setError(null);
    try {
      await downloadLessonFile(pack.id, format);
    } catch (cause) {
      setError(apiErrorMessage(cause, FILE_FAILED));
    } finally {
      setBusy(null);
    }
  }
  return (
    <div className="grid min-w-0 gap-2" data-testid="lesson-files">
      <ActionGroup align="start">
        {LESSON_FORMAT_ORDER.map((format) => (
          <button key={format} type="button" className={format === "pptx" ? "field-button" : "field-button-secondary"} disabled={busy !== null} onClick={() => void fetchFile(format)} data-format={format}>
            {busy === format ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden /> : <Download className="h-4 w-4" aria-hidden />}
            {LESSON_FORMAT_LABEL[format]}
          </button>
        ))}
      </ActionGroup>
      {error ? (
        <p role="alert" className="text-sm text-error-600">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function ReadingEntry({ item }: { item: ReadingItem }) {
  const href = sourceHref(item.source);
  return (
    <li className="grid min-w-0 gap-0.5 rounded-md border border-line-200 bg-card p-3" data-testid="reading-item">
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex min-w-0 items-start gap-1 break-words text-sm font-semibold text-ink-900 hover:text-purple-700 hover:underline">
          <span className="min-w-0">{item.source.title}</span>
          <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          <span className="sr-only">(opens in a new tab)</span>
        </a>
      ) : (
        <span className="break-words text-sm font-semibold text-ink-900">{item.source.title}</span>
      )}
      <span className="text-xs text-ink-500">{sourceByline(item.source)}</span>
      <span className="text-xs text-ink-500">
        {item.source.reliability ? `${sourceReliabilityLabel(item.source.reliability)} · ` : ""}
        {`Cited ${countNoun(item.citedBy, "time")}`}
      </span>
    </li>
  );
}

export function LessonPackView({ pack, reduce }: { pack: LessonPack; reduce: boolean }) {
  const ref = { explainerId: pack.explainerId, version: pack.version };
  return (
    <div className="grid min-w-0 gap-6" data-testid="lesson-pack">
      <section className="panel grid min-w-0 gap-4 p-4 md:p-5">
        <p className="flex flex-wrap gap-x-2 gap-y-1 text-xs text-ink-500">
          {pack.craft ? <span className="font-medium text-ink-700">{pack.craft.name}</span> : null}
          <span>{slideCountText(pack.slides.length)}</span>
          <span>Version {pack.version}</span>
          <span>{formatDate(pack.createdAt)}</span>
        </p>
        <LessonFiles pack={pack} />
        <CitationMenu explainer={ref} />
      </section>
      <section aria-labelledby="slides-heading" className="grid min-w-0 gap-3">
        <h2 id="slides-heading" className="field-label">
          Slides
        </h2>
        <SlidePreview pack={pack} reduce={reduce} />
      </section>
      <section aria-labelledby="reading-heading" className="grid min-w-0 gap-3">
        <h2 id="reading-heading" className="field-label">
          Reading list
        </h2>
        <ol className="grid min-w-0 gap-2 md:grid-cols-2">
          {pack.readingList.map((item) => (
            <ReadingEntry key={item.source.id} item={item} />
          ))}
        </ol>
      </section>
      <ListedSources sources={pack.sources} idPrefix="lesson-source" />
    </div>
  );
}
