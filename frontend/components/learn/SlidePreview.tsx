"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Check } from "lucide-react";

import { ExplainerSentence } from "@/components/answer/ExplainerSentence";
import { PictureView } from "@/components/answer/ImageStrip";
import { riseItem, staggerParent } from "@/components/guide/guideMotion";
import type { QuizBlock } from "@/lib/explainerLearning";
import { countNoun } from "@/lib/format";
import type { LessonPack, Slide } from "@/lib/lessonContract";
import { slideCaption } from "@/lib/lessonView";
import { cn } from "@/lib/utils";

function SlidePicture({ slide }: { slide: Slide }) {
  const [broken, setBroken] = useState(false);
  if (!slide.image || broken) return null;
  return (
    <div className="max-w-xs">
      <PictureView media={slide.image} onBroken={() => setBroken(true)} />
    </div>
  );
}

function QuizBody({ quiz, index }: { quiz: QuizBlock | null; index: number | null }) {
  const question = quiz && index !== null ? quiz.questions[index] : undefined;
  if (!question) return null;
  return (
    <div className="grid min-w-0 gap-2">
      <p className="break-words text-sm font-semibold text-ink-900">{question.prompt}</p>
      <ul className="grid gap-1">
        {question.options.map((option, place) => (
          <li key={option.termKey} className="flex min-w-0 items-center gap-2 text-sm text-ink-700">
            {place === question.answer ? <Check className="h-4 w-4 shrink-0 text-success-600" aria-hidden /> : <span className="h-4 w-4 shrink-0" aria-hidden />}
            <span className="min-w-0 break-words">{option.text}</span>
            {place === question.answer ? <span className="sr-only">(answer)</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SlideBody({ slide, pack }: { slide: Slide; pack: LessonPack }) {
  if (slide.kind === "SECTION") {
    return (
      <div className="grid min-w-0 gap-3">
        <ul className="grid list-disc gap-1.5 pl-5 text-sm leading-6 text-ink-700">
          {slide.bullets.map((bullet) => (
            <li key={bullet.id} className="break-words">
              <ExplainerSentence sentence={bullet} />
            </li>
          ))}
        </ul>
        <SlidePicture slide={slide} />
      </div>
    );
  }
  if (slide.kind === "QUIZ") return <QuizBody quiz={pack.quiz} index={slide.question} />;
  if (slide.kind === "READING") return <p className="text-sm text-ink-500">{countNoun(pack.readingList.length, "reading")}</p>;
  if (slide.kind === "SOURCES") return <p className="text-sm text-ink-500">{countNoun(pack.sources.length, "source")}</p>;
  return pack.craft ? <p className="text-sm text-ink-500">{pack.craft.name}</p> : null;
}

export function SlidePreview({ pack, reduce }: { pack: LessonPack; reduce: boolean }) {
  const total = pack.slides.length;
  return (
    <motion.ol variants={staggerParent(reduce, 0.04)} initial="hidden" animate="show" className="grid min-w-0 gap-3 md:grid-cols-2" aria-label="Slides" data-testid="slides">
      {pack.slides.map((slide) => (
        <motion.li
          key={slide.number}
          variants={riseItem(reduce, 10)}
          className={cn("panel grid min-w-0 content-start gap-3 p-4", slide.kind === "TITLE" && "md:col-span-2 bg-purple-50 dark:bg-purple-950/40")}
          data-testid="slide"
          data-kind={slide.kind}
        >
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-500">{slideCaption(slide, total)}</p>
          <h3 className={cn("break-words font-display font-bold text-ink-900", slide.kind === "TITLE" ? "text-xl" : "text-base")}>{slide.title}</h3>
          <SlideBody slide={slide} pack={pack} />
        </motion.li>
      ))}
    </motion.ol>
  );
}
