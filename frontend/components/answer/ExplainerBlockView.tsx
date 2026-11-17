"use client";

import { motion } from "framer-motion";
import { History } from "lucide-react";

import { hasRenderer, renderBlock } from "@/components/answer/blockRenderers";
import { useAuth } from "@/components/AuthProvider";
import { riseItem } from "@/components/guide/guideMotion";
import type { ReuseMarker } from "@/lib/explainerBlockBase";
import { reusedLabel, type TypedBlock } from "@/lib/explainerView";
import { canHideGenerated } from "@/lib/permissions";
import { hiddenFrom } from "@/lib/simulationView";

function ReuseNote({ reuse }: { reuse: ReuseMarker }) {
  return (
    <p className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-line-200 bg-surface-50 px-2.5 py-1 text-[11px] font-semibold text-ink-500" data-testid="reuse-marker">
      <History className="h-3 w-3" aria-hidden />
      {reusedLabel(reuse.storedAt)}
    </p>
  );
}

function BlockFrame({ block, reduce }: { block: TypedBlock; reduce: boolean }) {
  return (
    <motion.div variants={riseItem(reduce)} initial="hidden" animate="show" data-testid="explainer-block" data-kind={block.kind} data-block-id={block.id}>
      {block.reuse ? <ReuseNote reuse={block.reuse} /> : null}
      {renderBlock(block)}
    </motion.div>
  );
}

function HiddenBlockFrame({ block, reduce }: { block: TypedBlock; reduce: boolean }) {
  const canHide = canHideGenerated(useAuth().user);
  return hiddenFrom(block, canHide) ? null : <BlockFrame block={block} reduce={reduce} />;
}

export function ExplainerBlockView({ block, reduce }: { block: TypedBlock; reduce: boolean }) {
  if (!hasRenderer(block)) return null;
  if (hiddenFrom(block, false)) return <HiddenBlockFrame block={block} reduce={reduce} />;
  return <BlockFrame block={block} reduce={reduce} />;
}
