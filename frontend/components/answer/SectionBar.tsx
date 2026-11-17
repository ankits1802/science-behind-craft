"use client";

import { Loader2 } from "lucide-react";

import { useExplainerReading } from "@/components/answer/ExplainerReading";
import { scrollToStep } from "@/components/guide/guideMotion";
import { headingView } from "@/lib/answerLanguages";
import type { SectionView } from "@/lib/explainerState";
import { sectionAnchor, workingLabel } from "@/lib/explainerView";
import { cn } from "@/lib/utils";

export function SectionBar({
  sections,
  active,
  streaming,
  reduce,
  onPick
}: {
  sections: readonly SectionView[];
  active: string | null;
  streaming: boolean;
  reduce: boolean;
  onPick: (id: string) => void;
}) {
  const { language, original } = useExplainerReading();
  if (sections.length < 2) return null;
  return (
    <nav aria-label="Sections" className="-mx-4 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0" data-testid="section-bar">
      <ol className="flex w-max gap-1.5 sm:w-auto sm:flex-wrap">
        {sections.map((section) => {
          const current = section.id === active;
          const working = workingLabel(section.state, streaming);
          const heading = headingView({ id: section.id, heading: section.title, original: section.original, sentences: [] }, language, original);
          return (
            <li key={section.id}>
              <a
                href={`#${sectionAnchor(section.id)}`}
                aria-current={current ? "location" : undefined}
                onClick={(event) => {
                  event.preventDefault();
                  onPick(section.id);
                  scrollToStep(sectionAnchor(section.id), reduce);
                }}
                className={cn(
                  "inline-flex min-h-9 items-center gap-1.5 rounded-full border px-3.5 text-[13px] font-semibold transition pointer-coarse:min-h-11",
                  current
                    ? "border-purple-300 bg-purple-100 text-purple-800 dark:border-purple-800 dark:bg-purple-950/60 dark:text-purple-200"
                    : "border-transparent text-ink-700 hover:border-line-200 hover:bg-card",
                  section.state === "EMPTY" ? "text-ink-500" : null
                )}
              >
                {working ? <Loader2 className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none" aria-hidden /> : null}
                <span lang={heading.lang} dir={heading.dir}>
                  {heading.text}
                </span>
                {working ? <span className="sr-only">, {working.toLowerCase()}</span> : null}
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
