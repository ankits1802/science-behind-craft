"use client";

import "katex/dist/katex.min.css";

import { ChemistryMarkup, useChemistryHtml, useRenderedChemistry } from "@/components/answer/RenderedChemistry";
import { chemistryKey, equationPieces } from "@/lib/chemistryKeys";
import { cn } from "@/lib/utils";

type EquationProps = { equation: string; display?: boolean; label?: string; className?: string };

function ChemTerm({ piece }: { piece: string }) {
  const held = useRenderedChemistry()[chemistryKey(piece, false)];
  const html = useChemistryHtml(piece, false, held);
  return <ChemistryMarkup html={html} text={piece} display={false} label={piece} className="kv-chem-term" hidden />;
}

export function ChemEquation({ equation, display = true, label, className }: EquationProps) {
  const pieces = equationPieces(equation);
  const held = useRenderedChemistry()[chemistryKey(equation, display)];
  const html = useChemistryHtml(equation, display, pieces.length > 1 ? "" : held);
  if (pieces.length < 2) return <ChemistryMarkup html={html} text={equation} display={display} label={label ?? equation} className={className} />;
  return (
    <span role="math" aria-label={label ?? equation} className={cn("kv-chem kv-chem-terms max-w-full text-ink-1", display ? "block" : "inline", className)} data-testid="chem-terms">
      {pieces.map((piece, at) => (
        <span key={`${piece}-${at}`}>
          {at > 0 ? " " : null}
          <ChemTerm piece={piece} />
        </span>
      ))}
    </span>
  );
}
