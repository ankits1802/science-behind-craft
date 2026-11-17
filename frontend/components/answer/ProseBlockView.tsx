"use client";

import { useExplainerReading } from "@/components/answer/ExplainerReading";
import { ExplainerSentence } from "@/components/answer/ExplainerSentence";
import { paragraphAttributes } from "@/lib/answerLanguages";
import type { ProseBlock } from "@/lib/explainerContract";

export function ProseBlockView({ block }: { block: ProseBlock }) {
  const { language, original } = useExplainerReading();
  const paragraph = paragraphAttributes({ id: block.id, heading: "", sentences: block.sentences }, language, original);
  return (
    <p lang={paragraph.lang} dir={paragraph.dir} className="text-[15px] leading-8 text-ink-700 md:text-base md:leading-8">
      {block.sentences.map((sentence) => (
        <ExplainerSentence key={sentence.id} sentence={sentence} />
      ))}
    </p>
  );
}
