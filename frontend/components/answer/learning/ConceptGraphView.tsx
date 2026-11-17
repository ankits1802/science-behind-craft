"use client";

import { useState } from "react";
import Link from "next/link";

import { ConceptGraphFigure } from "@/components/answer/learning/ConceptGraphFigure";
import { CitedText } from "@/components/answer/ProseBlockView";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import type { CraftLink } from "@/lib/answerShapes";
import { chosenNode, LIST_CRAFTS_START, nodeChoiceLabel, shownCrafts } from "@/lib/conceptGraph";
import type { ConceptGraphBlock, ConceptNode } from "@/lib/explainerLearning";
import { cn } from "@/lib/utils";

function ConceptChoice({ nodes, current, onChoose }: { nodes: readonly ConceptNode[]; current: string; onChoose: (termKey: string) => void }) {
  return (
    <div role="group" aria-label="Shared concept" className="flex min-w-0 flex-wrap gap-2" data-testid="concept-choice">
      {nodes.map((node) => {
        const on = node.termKey === current;
        return (
          <button
            key={node.termKey}
            type="button"
            aria-pressed={on}
            onClick={() => onChoose(node.termKey)}
            className={cn(
              "min-h-10 rounded-full border px-3.5 text-sm font-semibold transition-colors pointer-coarse:min-h-11",
              on ? "border-purple-700 bg-purple-700 text-white" : "border-line-200 bg-card text-ink-700 hover:border-purple-300 hover:bg-purple-50 dark:hover:bg-purple-950/40"
            )}
          >
            {nodeChoiceLabel(node)}
          </button>
        );
      })}
    </div>
  );
}

function CraftList({ node, focus, all, onShowAll }: { node: ConceptNode; focus: CraftLink | null; all: boolean; onShowAll: () => void }) {
  const crafts = shownCrafts(node, all);
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2">
      <ul className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2" aria-label={`Crafts that share ${node.label}`} data-testid="concept-list">
        {crafts.map((entry) => (
          <li key={entry.craft.slug} className="grid min-w-0 gap-1 rounded-md border border-line-200 bg-card p-3" data-testid="concept-list-craft" data-focus={entry.craft.slug === focus?.slug ? "true" : "false"}>
            <Link href={entry.craft.path} className="w-fit break-words font-display text-sm font-bold text-purple-700 underline-offset-2 hover:underline dark:text-purple-300">
              {entry.craft.name}
            </Link>
            <CitedText id={entry.sentence.id} sentences={[entry.sentence]} className="text-sm leading-7 text-ink-700" />
          </li>
        ))}
      </ul>
      {!all && node.crafts.length > LIST_CRAFTS_START ? (
        <button type="button" onClick={onShowAll} className="field-button-secondary w-fit rounded-full" data-testid="concept-show-all">
          Show all {node.crafts.length}
        </button>
      ) : null}
    </div>
  );
}

export function ConceptGraphView({
  focus,
  nodes,
  reduce,
  initialTermKey = null
}: {
  focus: CraftLink | null;
  nodes: readonly ConceptNode[];
  reduce: boolean;
  initialTermKey?: string | null;
}) {
  const [termKey, setTermKey] = useState<string | null>(initialTermKey);
  const [all, setAll] = useState(false);
  if (nodes.length === 0) return null;
  const node = chosenNode(nodes, termKey);
  const choose = (key: string) => {
    setTermKey(key);
    setAll(false);
  };
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3" data-testid="concept-graph" data-concept={node.termKey}>
      {nodes.length > 1 ? <ConceptChoice nodes={nodes} current={node.termKey} onChoose={choose} /> : null}
      <ConceptGraphFigure node={node} focus={focus} reduce={reduce} />
      <CraftList node={node} focus={focus} all={all} onShowAll={() => setAll(true)} />
    </div>
  );
}

export function ConceptGraphBlockView({ block }: { block: ConceptGraphBlock }) {
  const reduce = useAppReducedMotion();
  return <ConceptGraphView focus={block.focus} nodes={block.nodes} reduce={reduce} />;
}
