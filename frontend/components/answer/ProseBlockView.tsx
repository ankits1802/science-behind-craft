"use client";

import { useExplainerReading } from "@/components/answer/ExplainerReading";
import { ExplainerSentence } from "@/components/answer/ExplainerSentence";
import { paragraphAttributes } from "@/lib/answerLanguages";
import type { ExplainerSentence as Sentence } from "@/lib/explainerBlockBase";
import type { ProseBlock } from "@/lib/explainerContract";

export function CitedText({ id, sentences, className }: { id: string; sentences: readonly Sentence[]; className: string }) {
  const { language, original } = useExplainerReading();
  const paragraph = paragraphAttributes({ id, heading: "", sentences: [...sentences] }, language, original);
  return (
    <p lang={paragraph.lang} dir={paragraph.dir} className={className}>
      {sentences.map((sentence) => (
        <ExplainerSentence key={sentence.id} sentence={sentence} />
      ))}
    </p>
  );
}

export function ProseBlockView({ block }: { block: ProseBlock }) {
  return <CitedText id={block.id} sentences={block.sentences} className="text-[15px] leading-8 text-ink-700 md:text-base md:leading-8" />;
}
