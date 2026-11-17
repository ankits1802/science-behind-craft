"use client";

import { motion } from "framer-motion";
import { Loader2, SearchX } from "lucide-react";

import { ExplainerBlockView } from "@/components/answer/ExplainerBlockView";
import { useExplainerReading } from "@/components/answer/ExplainerReading";
import { headingView } from "@/lib/answerLanguages";
import type { SectionView } from "@/lib/explainerState";
import { DISCIPLINE_LABEL, sectionAnchor, workingLabel } from "@/lib/explainerView";

export const SECTION_VIEWPORT = { margin: "-45% 0px -45% 0px", amount: "some" } as const;

function WorkingState({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-200 bg-purple-50 px-2.5 py-1 text-xs font-semibold text-purple-700 dark:border-purple-900 dark:bg-purple-950/50 dark:text-purple-200" data-testid="section-working">
      <Loader2 className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none" aria-hidden />
      {label}
    </span>
  );
}

export function ExplainerSectionView({
  section,
  streaming,
  reduce,
  onActive
}: {
  section: SectionView;
  streaming: boolean;
  reduce: boolean;
  onActive: (id: string) => void;
}) {
  const { language, original } = useExplainerReading();
  const heading = headingView({ id: section.id, heading: section.title, original: section.original, sentences: [] }, language, original);
  const anchor = sectionAnchor(section.id);
  const working = workingLabel(section.state, streaming);

  return (
    <motion.section
      id={anchor}
      aria-labelledby={`${anchor}-title`}
      viewport={SECTION_VIEWPORT}
      onViewportEnter={() => onActive(section.id)}
      className="panel scroll-mt-28 p-4 sm:p-5 md:p-7"
      data-testid="explainer-section"
      data-state={section.state}
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="eyebrow">{DISCIPLINE_LABEL[section.discipline]}</p>
          <h2 id={`${anchor}-title`} lang={heading.lang} dir={heading.dir} className="mt-1 font-display text-xl font-bold text-ink-900 md:text-2xl">
            {heading.text}
          </h2>
        </div>
        {working ? <WorkingState label={working} /> : null}
      </header>
      {section.blocks.length > 0 ? (
        <div className="mt-4 grid gap-6">
          {section.blocks.map((block) => (
            <ExplainerBlockView key={block.id} block={block} reduce={reduce} />
          ))}
        </div>
      ) : null}
      {section.state === "EMPTY" && section.searched ? (
        <p className="mt-3 flex items-start gap-2 text-sm leading-6 text-ink-500" data-testid="section-searched">
          <SearchX className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <span>{section.searched}</span>
        </p>
      ) : null}
    </motion.section>
  );
}
