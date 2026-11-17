"use client";

import { Database } from "lucide-react";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { CHIP_SHAPE, QUOTED_CHIP_TONE } from "@/components/answer/CitationChip";
import { useCitations } from "@/components/answer/CitationContext";
import { sourceHref } from "@/lib/citations";
import type { Molecule3dBlock } from "@/lib/explainerMatter";
import { cn } from "@/lib/utils";

function SourceChip({ sourceId }: { sourceId: string }) {
  const { numbers, sourcesById } = useCitations();
  const source = sourcesById.get(sourceId) ?? null;
  const number = numbers.get(sourceId) ?? null;
  const href = source ? sourceHref(source) : null;
  const label = `Source ${number ?? ""}${source ? `: ${source.title}` : ""}`;
  const body = (
    <>
      <Database className="h-2.5 w-2.5" aria-hidden />
      <span className="tabular-nums">{number ?? "·"}</span>
    </>
  );
  if (!href) {
    return (
      <span aria-label={label} title={source?.title} className={cn(CHIP_SHAPE, QUOTED_CHIP_TONE)} data-testid="source-chip">
        {body}
      </span>
    );
  }
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" aria-label={`${label} (opens in a new tab)`} title={source?.title} className={cn(CHIP_SHAPE, QUOTED_CHIP_TONE)} data-testid="source-chip">
      {body}
    </a>
  );
}

export function MoleculeCaption({ block }: { block: Molecule3dBlock }) {
  return (
    <figcaption className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-sm text-ink-700" data-testid="molecule-caption">
      <span className="break-words font-display text-base font-bold text-ink-900">{block.name}</span>
      {block.formula ? <ChemEquation equation={block.formula} display={false} label={block.formula} /> : null}
      <span className="text-xs text-ink-500">PubChem CID {block.pubchemCid}</span>
      <SourceChip sourceId={block.sourceId} />
    </figcaption>
  );
}
