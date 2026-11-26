"use client";

import { useState } from "react";

import { DrawnPair } from "@/components/review/DrawnPair";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import type { DrawnSide, PageProposalView } from "@/lib/pageProposalContract";
import { emptyWords, firstScreens, sidesToDraw } from "@/lib/pageProposalView";

const DRAW_HINT = "The site's renderer draws each version at 390 and 1440 px, about a minute for both.";

export function PageShots({ view, onDraw }: { view: PageProposalView; onDraw: (side: DrawnSide) => Promise<string | null> }) {
  const [drawing, setDrawing] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const missing = sidesToDraw(view);
  const empty = emptyWords(view);

  async function draw() {
    setDrawing(true);
    setProblem(null);
    for (const side of missing) {
      const refused = await onDraw(side);
      if (refused) {
        setProblem(refused);
        break;
      }
    }
    setDrawing(false);
  }

  return (
    <section className="grid gap-4" data-testid="page-shots">
      <h4 className="font-ui text-h4 text-ink-1">The page as it stands and as it will be</h4>
      {firstScreens(view).map((pair) => (
        <DrawnPair key={pair.key} pair={pair} empty={empty} />
      ))}
      {missing.length ? (
        <div className="grid gap-2">
          <p className="max-w-measure font-ui text-label text-ink-3">{DRAW_HINT}</p>
          <ActionGroup align="start">
            <Button variant="quiet" busy={drawing} busyLabel="Drawing" onClick={() => void draw()}>
              Draw it
            </Button>
          </ActionGroup>
        </div>
      ) : null}
      {problem ? (
        <p role="alert" className="font-ui text-ui text-error">
          {problem}
        </p>
      ) : null}
    </section>
  );
}
