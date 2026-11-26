"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { NO_CHEMISTRY, type RenderedChemistry } from "@/lib/chemistryKeys";
import { cn } from "@/lib/utils";

const RenderedChemistryContext = createContext<RenderedChemistry>(NO_CHEMISTRY);

export function RenderedChemistryProvider({ rendered, children }: { rendered: RenderedChemistry; children?: ReactNode }) {
  return <RenderedChemistryContext.Provider value={rendered}>{children}</RenderedChemistryContext.Provider>;
}

export function useRenderedChemistry(): RenderedChemistry {
  return useContext(RenderedChemistryContext);
}

export function useChemistryHtml(equation: string, display: boolean, held: string | undefined): string | null {
  const [drawn, setDrawn] = useState<{ key: string; html: string } | null>(null);
  const key = `${display}:${equation}`;
  useEffect(() => {
    if (held !== undefined) return;
    let current = true;
    void import("@/lib/chemistry").then(({ renderChemistry }) => {
      if (current) setDrawn({ key, html: renderChemistry(equation, display) });
    });
    return () => {
      current = false;
    };
  }, [display, equation, held, key]);
  if (held !== undefined) return held;
  return drawn !== null && drawn.key === key ? drawn.html : null;
}

export type ChemistryMarkupProps = { html: string | null; text: string; display: boolean; label: string; className?: string; hidden?: boolean };

export function ChemistryMarkup({ html, text, display, label, className, hidden = false }: ChemistryMarkupProps) {
  const shape = cn("kv-chem max-w-full text-ink-1", display ? "flow-root" : "inline-block align-middle", className);
  const named = hidden ? { "aria-hidden": true } : { role: "math", "aria-label": label };
  if (html === null) {
    return (
      <span {...named} className={shape}>
        {text}
      </span>
    );
  }
  return <span {...named} className={shape} dangerouslySetInnerHTML={{ __html: html }} />;
}
