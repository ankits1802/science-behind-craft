"use client";

import { Check, MessageSquareQuote } from "lucide-react";

import { CitedText } from "@/components/answer/ProseBlockView";
import type { ExpertViewBlock } from "@/lib/explainerExperts";
import { agreementText, seatLabel } from "@/lib/expertPanel";

export function ExpertSeatCard({ block }: { block: ExpertViewBlock }) {
  const agreement = agreementText(block);
  return (
    <article className="grid h-full min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-2 rounded-lg border border-line-200 bg-card p-4" data-testid="expert-seat" data-seat={block.seat}>
      <h3 className="flex min-w-0 items-center gap-2 font-display text-base font-bold text-ink-900">
        <span aria-hidden className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-purple-100 text-purple-800 dark:bg-purple-950/70 dark:text-purple-200">
          <MessageSquareQuote className="h-4 w-4" />
        </span>
        <span className="min-w-0 break-words">{seatLabel(block.seat)}</span>
      </h3>
      <CitedText id={block.id} sentences={block.take} className="text-sm leading-7 text-ink-700" />
      {agreement ? (
        <p className="flex items-center gap-1.5 text-xs font-medium text-ink-500" data-testid="expert-agrees">
          <Check className="h-3.5 w-3.5 shrink-0" aria-hidden />
          {agreement}
        </p>
      ) : null}
    </article>
  );
}
