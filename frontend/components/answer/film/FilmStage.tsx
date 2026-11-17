"use client";

import { useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { renderBlock } from "@/components/answer/blockRenderers";
import { ExplainerReadingProvider, useExplainerReading } from "@/components/answer/ExplainerReading";
import { FilmSceneProvider } from "@/components/answer/FilmScene";
import { swapVariants } from "@/components/guide/guideMotion";
import { headingView } from "@/lib/answerLanguages";
import { DISCIPLINE_LABEL } from "@/lib/explainerView";
import type { FilmCaption as Caption, FilmScene } from "@/lib/filmScenes";
import type { ListenMark } from "@/lib/listen";

export function FilmCaption({ caption }: { caption: Caption }) {
  const before = caption.mark ? caption.text.slice(0, caption.mark.from) : caption.text;
  const word = caption.mark ? caption.text.slice(caption.mark.from, caption.mark.to) : "";
  const after = caption.mark ? caption.text.slice(caption.mark.to) : "";
  return (
    <p
      lang={caption.lang}
      dir={caption.dir}
      className="min-h-[3.5rem] text-balance text-center font-display text-base font-semibold leading-7 text-ink-900 md:min-h-[4rem] md:text-lg"
      data-testid="film-caption"
      data-narrated={caption.narrated ? "true" : "false"}
    >
      {before}
      {word ? (
        <mark className="rounded-sm bg-purple-200 text-ink-900 dark:bg-purple-800 dark:text-white" data-testid="film-caption-word">
          {word}
        </mark>
      ) : null}
      {after}
    </p>
  );
}

function SceneHeading({ scene }: { scene: FilmScene }) {
  const { language } = useExplainerReading();
  const title = headingView({ id: scene.section.id, heading: scene.section.title, original: scene.section.original, sentences: [] }, language, false);
  return (
    <div className="mb-3 min-w-0">
      <p className="eyebrow">{DISCIPLINE_LABEL[scene.section.discipline]}</p>
      <p lang={title.lang} dir={title.dir} className="mt-0.5 font-display text-lg font-bold text-ink-900">
        {title.text}
      </p>
    </div>
  );
}

export function FilmStage({ scene, progress, mark, reduce }: { scene: FilmScene; progress: number; mark: ListenMark | null; reduce: boolean }) {
  const reading = useExplainerReading();
  const narrated = useMemo(() => ({ ...reading, listen: mark }), [reading, mark]);
  const shown = useMemo(() => ({ progress }), [progress]);
  const content = useMemo(() => renderBlock(scene.block), [scene.block]);
  return (
    <div className="relative min-w-0 overflow-y-auto overscroll-contain rounded-lg border border-line-200 bg-card p-3 sm:p-5 max-h-[46dvh] lg:max-h-[58dvh]" data-testid="film-stage">
      <AnimatePresence mode="wait" initial={false}>
        <motion.div key={scene.block.id} variants={swapVariants(reduce)} initial="hidden" animate="show" exit="exit" className="min-w-0" data-testid="film-scene" data-kind={scene.block.kind} data-block-id={scene.block.id}>
          <SceneHeading scene={scene} />
          <ExplainerReadingProvider value={narrated}>
            <FilmSceneProvider value={shown}>{content}</FilmSceneProvider>
          </ExplainerReadingProvider>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
