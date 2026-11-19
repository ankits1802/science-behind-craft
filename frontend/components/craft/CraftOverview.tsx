"use client";

import { motion } from "framer-motion";

import { ExplainerSentence } from "@/components/answer/ExplainerSentence";
import { CitedProse, useCraftClaims } from "@/components/craft/CraftClaims";
import { CraftGlossary } from "@/components/craft/CraftGlossary";
import { ContributedPlates } from "@/components/craft/ContributedPlates";
import { CraftPictures } from "@/components/craft/CraftPictures";
import { CraftSearched } from "@/components/craft/CraftSearched";
import { CraftRegister, CraftSummary } from "@/components/craft/CraftSummary";
import { OpenQuestions } from "@/components/craft/OpenQuestions";
import { SourcesDiffer } from "@/components/craft/SourcesDiffer";
import { riseItem, staggerParent } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { NO_PLATES, type ContributedPlate } from "@/lib/craftContributed";
import type { CraftPage, OverviewSection } from "@/lib/craftPageContract";
import { overviewPictures, registerFacts, shownSentence } from "@/lib/craftPageView";
import { cn } from "@/lib/utils";

function SectionBody({ section }: { section: OverviewSection }) {
  const index = useCraftClaims();
  if (section.basis === "CURATED") return <CitedProse sentences={section.sentences} className="mt-3" />;
  return (
    <ul className="mt-3 grid gap-2.5">
      {section.sentences.map((sentence) => (
        <li key={sentence.id} className="text-[15px] leading-7 text-ink-700">
          <ExplainerSentence sentence={shownSentence(index, sentence)} />
        </li>
      ))}
    </ul>
  );
}

export function CraftOverview({ page, contributed = NO_PLATES }: { page: CraftPage; contributed?: readonly ContributedPlate[] }) {
  const reduce = useAppReducedMotion();
  const { overview } = page;
  const summarised = overview.lede.length + overview.keyFacts.length > 0;
  const thin = page.curation?.coverage === "THIN";
  const aside = thin || page.openQuestions.length + page.glossary.length > 0;
  return (
    <div className="grid gap-5" data-testid="craft-overview">
      {summarised ? <CraftSummary lede={overview.lede} keyFacts={overview.keyFacts} /> : <CraftRegister facts={registerFacts(page.craft)} />}
      <CraftPictures pictures={overviewPictures(page.pictures)} />
      <ContributedPlates plates={contributed} />
      <div className={cn("grid items-start gap-5", aside && "lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]")}>
        <motion.div variants={staggerParent(reduce)} initial="hidden" animate="show" className="grid min-w-0 gap-5">
          {overview.sections.map((section) => (
            <motion.section
              key={section.discipline}
              variants={riseItem(reduce)}
              aria-labelledby={`craft-section-${section.discipline}`}
              className="panel p-5 md:p-6"
              data-testid="craft-section"
              data-basis={section.basis}
            >
              <h2 id={`craft-section-${section.discipline}`} className="font-display text-lg font-bold text-ink-900">
                {section.title}
              </h2>
              <SectionBody section={section} />
            </motion.section>
          ))}
          <SourcesDiffer rows={page.sourcesDiffer} />
        </motion.div>
        {aside ? (
          <div className="grid min-w-0 gap-5">
            <OpenQuestions questions={page.openQuestions} />
            <CraftGlossary terms={page.glossary} />
            <CraftSearched curation={page.curation} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
