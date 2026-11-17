"use client";

import { useMemo, useState, type FormEvent } from "react";
import { Presentation } from "lucide-react";

import { Toggle } from "@/components/ui/Toggle";
import { apiErrorMessage } from "@/lib/api";
import type { ExplainerVersionDocument } from "@/lib/learningContract";
import { buildLesson } from "@/lib/lessonApi";
import type { LessonPack } from "@/lib/lessonContract";
import { chosenInOrder, LESSON_SECTIONS_MAX, lessonRequest, lessonSections } from "@/lib/lessonView";
import { cn } from "@/lib/utils";

const BUILD_FAILED = "Couldn't build the lesson. Try again.";

export function LessonBuilder({ document, onBuilt }: { document: ExplainerVersionDocument; onBuilt: (pack: LessonPack) => void }) {
  const sections = useMemo(() => lessonSections(document.explainer), [document]);
  const [title, setTitle] = useState("");
  const [chosen, setChosen] = useState<ReadonlySet<string>>(() => new Set(sections.slice(0, LESSON_SECTIONS_MAX).map((section) => section.id)));
  const [quiz, setQuiz] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ref = { explainerId: document.mark.explainerId, version: document.mark.version };
  const request = lessonRequest(ref, title, chosenInOrder(sections, chosen), quiz);

  function flip(id: string) {
    setChosen((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else if (next.size < LESSON_SECTIONS_MAX) next.add(id);
      return next;
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!request || busy) return;
    setBusy(true);
    setError(null);
    try {
      onBuilt(await buildLesson(request));
    } catch (cause) {
      setError(apiErrorMessage(cause, BUILD_FAILED));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="panel grid min-w-0 gap-5 p-4 md:p-6" data-testid="lesson-builder">
      <label className="grid min-w-0 gap-1">
        <span className="field-label">Title</span>
        <input className="field-input" value={title} maxLength={200} placeholder={document.explainer.question} onChange={(event) => setTitle(event.target.value)} />
      </label>
      <fieldset className="grid min-w-0 gap-2">
        <legend className="field-label mb-2">Sections · {chosen.size} chosen</legend>
        {sections.length === 0 ? <p className="text-sm text-ink-500">This version has no finished sections.</p> : null}
        {sections.map((section) => {
          const on = chosen.has(section.id);
          return (
            <label
              key={section.id}
              className={cn("flex min-h-12 min-w-0 cursor-pointer items-center gap-3 rounded-md border px-3 py-2 transition", on ? "border-purple-300 bg-purple-50 dark:border-purple-800 dark:bg-purple-950/40" : "border-line-200 bg-card hover:border-purple-300")}
              data-testid="lesson-section"
              data-chosen={on ? "true" : "false"}
            >
              <input type="checkbox" className="h-4 w-4 shrink-0 accent-purple-700" checked={on} onChange={() => flip(section.id)} />
              <span className="min-w-0 flex-1 break-words text-sm font-medium text-ink-900">{section.title}</span>
            </label>
          );
        })}
      </fieldset>
      <Toggle label="Add a quiz" description="Questions from the chosen sections, with an answer key." checked={quiz} onChange={setQuiz} />
      {error ? (
        <p role="alert" className="rounded-md border border-red-200 bg-error-100 px-3 py-2 text-sm text-error-600">
          {error}
        </p>
      ) : null}
      <button type="submit" className="field-button w-full sm:w-fit sm:justify-self-end" disabled={!request || busy} data-testid="lesson-build">
        <Presentation className="h-4 w-4" aria-hidden />
        {busy ? "Building…" : "Build the lesson"}
      </button>
    </form>
  );
}
