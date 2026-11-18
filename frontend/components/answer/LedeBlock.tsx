"use client";

import { useId } from "react";
import { motion } from "framer-motion";

import { hasRenderer } from "@/components/answer/blockRenderers";
import { ExplainerBlockView } from "@/components/answer/ExplainerBlockView";
import { useExplainerReading } from "@/components/answer/ExplainerReading";
import { CitedText } from "@/components/answer/ProseBlockView";
import { riseItem } from "@/components/guide/guideMotion";
import { attributesForText } from "@/lib/answerLanguages";
import type { LedeBlock as Lede } from "@/lib/explainerContract";

export function LedeBlock({ lede, reduce }: { lede: Lede; reduce: boolean }) {
  const { language } = useExplainerReading();
  const titleId = useId();
  const headline = attributesForText(lede.headline, language);
  return (
    <motion.section
      variants={riseItem(reduce)}
      initial="hidden"
      animate="show"
      aria-labelledby={titleId}
      className="panel p-4 sm:p-5 md:p-7"
      data-testid="answer-lede"
    >
      <h2 id={titleId} lang={headline.lang} dir={headline.dir} className="display-title break-words text-2xl leading-tight md:text-3xl">
        {lede.headline}
      </h2>
      <CitedText id={lede.id} sentences={lede.sentences} className="mt-3 text-base leading-8 text-ink-900 md:text-[17px]" />
      {lede.figure && hasRenderer(lede.figure) ? (
        <div className="mt-5">
          <ExplainerBlockView block={lede.figure} reduce={reduce} />
        </div>
      ) : null}
    </motion.section>
  );
}
