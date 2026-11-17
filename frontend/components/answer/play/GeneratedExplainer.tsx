"use client";

import { useState } from "react";
import { Code2, Eye, EyeOff, Sparkles } from "lucide-react";

import { useAnswerId } from "@/components/answer/AnswerContext";
import { GeneratedCode } from "@/components/answer/play/GeneratedCode";
import { GeneratedSources } from "@/components/answer/play/GeneratedSources";
import { SandboxFrame } from "@/components/answer/play/SandboxFrame";
import { useSimulationHiding, type HidingControls } from "@/components/answer/play/useSimulationHiding";
import { useAuth } from "@/components/AuthProvider";
import { ActionGroup } from "@/components/ui/ActionGroup";
import type { SimulationBlock } from "@/lib/explainerPlay";
import { canHideGenerated } from "@/lib/permissions";
import { generatedCaption, keptAsPiece, valueBases } from "@/lib/simulationView";

const FIGURE = "grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3 rounded-lg border bg-card p-4 sm:p-5";

function Caption({ block }: { block: SimulationBlock }) {
  return (
    <p className="flex min-w-0 items-start gap-1.5 text-xs font-medium text-ink-500" data-testid="generated-caption">
      <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-purple-700 dark:text-purple-300" aria-hidden />
      <span className="min-w-0 break-words">{generatedCaption(block)}</span>
    </p>
  );
}

function HidingFailed({ hiding }: { hiding: HidingControls | null }) {
  if (!hiding?.failed) return null;
  return (
    <p role="alert" className="text-sm text-error-600" data-testid="generated-hiding-failed">
      Couldn&apos;t save. Try again.
    </p>
  );
}

function HiddenExplainer({ block, hiding }: { block: SimulationBlock; hiding: HidingControls | null }) {
  return (
    <figure className={`${FIGURE} border-dashed border-line-200`} data-testid="generated-explainer" data-hidden="true" lang="en">
      <Caption block={block} />
      <p className="flex min-w-0 items-center gap-2 text-sm text-ink-700">
        <EyeOff className="h-4 w-4 shrink-0 text-ink-500" aria-hidden />
        <span className="min-w-0 break-words">Hidden · {block.title}</span>
      </p>
      {hiding ? (
        <ActionGroup align="start">
          <button type="button" className="field-button-secondary" disabled={hiding.busy} onClick={() => hiding.change(false)} data-testid="generated-show">
            <Eye className="h-4 w-4" aria-hidden />
            Show again
          </button>
        </ActionGroup>
      ) : null}
      <HidingFailed hiding={hiding} />
    </figure>
  );
}

export function GeneratedExplainerView({ block, canHide, hiding }: { block: SimulationBlock; canHide: boolean; hiding: HidingControls | null }) {
  const [code, setCode] = useState(false);
  const bases = valueBases(block);
  if (bases === null) return null;
  if (hiding?.hidden ?? block.hidden) return canHide ? <HiddenExplainer block={block} hiding={hiding} /> : null;
  const codeId = `${block.id}-code`;
  const titleId = `${block.id}-title`;
  return (
    <figure className={`${FIGURE} border-line-200`} aria-labelledby={titleId} data-testid="generated-explainer" data-hidden="false" lang="en">
      <header className="grid min-w-0 gap-1">
        <Caption block={block} />
        <h3 id={titleId} className="break-words font-display text-lg font-bold text-ink-900">
          {block.title}
        </h3>
      </header>
      <SandboxFrame block={block} />
      <GeneratedSources values={block.values} bases={bases} />
      <ActionGroup align="start">
        <button
          type="button"
          className="field-button-secondary"
          aria-expanded={code}
          aria-controls={code ? codeId : undefined}
          onClick={() => setCode((open) => !open)}
          data-testid="generated-view-code"
        >
          <Code2 className="h-4 w-4" aria-hidden />
          {code ? "Close code" : "View code"}
        </button>
        {hiding ? (
          <button type="button" className="field-button-secondary" disabled={hiding.busy} onClick={() => hiding.change(true)} data-testid="generated-hide">
            <EyeOff className="h-4 w-4" aria-hidden />
            Hide explainer
          </button>
        ) : null}
      </ActionGroup>
      {code ? <GeneratedCode id={codeId} html={block.html} /> : null}
      <HidingFailed hiding={hiding} />
    </figure>
  );
}

export function GeneratedExplainer({ block }: { block: SimulationBlock }) {
  const canHide = canHideGenerated(useAuth().user) && keptAsPiece(block);
  const answerId = useAnswerId();
  const hiding = useSimulationHiding(canHide ? answerId : null, block.id, block.hidden);
  return <GeneratedExplainerView block={block} canHide={canHide} hiding={hiding} />;
}
