"use client";

import { motion } from "framer-motion";
import { History } from "lucide-react";

import { ImageStrip } from "@/components/answer/ImageStrip";
import { ProcessLadder } from "@/components/answer/ProcessLadder";
import { ProseBlockView } from "@/components/answer/ProseBlockView";
import { riseItem } from "@/components/guide/guideMotion";
import type { ExplainerBlock, ReuseMarker } from "@/lib/explainerContract";
import { reusedLabel } from "@/lib/explainerView";

function ReuseNote({ reuse }: { reuse: ReuseMarker }) {
  return (
    <p className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-line-200 bg-surface-50 px-2.5 py-1 text-[11px] font-semibold text-ink-500" data-testid="reuse-marker">
      <History className="h-3 w-3" aria-hidden />
      {reusedLabel(reuse.storedAt)}
    </p>
  );
}

function BlockBody({ block }: { block: ExplainerBlock }) {
  switch (block.kind) {
    case "prose":
      return <ProseBlockView block={block} />;
    case "process_ladder":
      return <ProcessLadder block={block} />;
    case "images":
      return <ImageStrip block={block} />;
  }
}

export function ExplainerBlockView({ block, reduce }: { block: ExplainerBlock; reduce: boolean }) {
  return (
    <motion.div variants={riseItem(reduce)} initial="hidden" animate="show" data-testid="explainer-block" data-kind={block.kind} data-block-id={block.id}>
      {block.reuse ? <ReuseNote reuse={block.reuse} /> : null}
      <BlockBody block={block} />
    </motion.div>
  );
}
