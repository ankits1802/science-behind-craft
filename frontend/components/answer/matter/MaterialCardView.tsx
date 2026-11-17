"use client";

import type { ReactNode } from "react";
import { ExternalLink, TriangleAlert } from "lucide-react";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { CitedText } from "@/components/answer/ProseBlockView";
import type { MaterialCardBlock } from "@/lib/explainerMatter";
import { materialRoleText, pubchemHref } from "@/lib/processView";
import { wikidataUrl } from "@/lib/supplyView";

const OUTBOUND = "inline-flex items-center gap-0.5 text-xs font-semibold text-purple-700 underline-offset-2 hover:underline dark:text-purple-300";

function Outbound({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={OUTBOUND}>
      {children}
      <ExternalLink className="h-3 w-3" aria-hidden />
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  );
}

function Tile({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid min-w-0 content-start gap-1 rounded-md border border-line-200 bg-surface-50 p-3" data-testid="material-tile">
      <span className="field-label">{label}</span>
      {children}
    </div>
  );
}

function MaterialTiles({ block }: { block: MaterialCardBlock }) {
  const role = materialRoleText(block.role, block.materialKind);
  const pubchem = pubchemHref(block.pubchemCid);
  if (!block.formula && !role) return null;
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 sm:grid-cols-[repeat(2,minmax(0,1fr))]">
      {block.formula ? (
        <Tile label="Formula">
          <ChemEquation equation={block.formula} display={false} label={block.formula} className="text-base" />
          {pubchem ? <Outbound href={pubchem}>PubChem</Outbound> : null}
        </Tile>
      ) : null}
      {role ? (
        <Tile label="Role">
          <span className="text-sm font-medium text-ink-900">{role}</span>
        </Tile>
      ) : null}
    </div>
  );
}

function Handling({ block }: { block: MaterialCardBlock }) {
  if (block.handling.length === 0) return null;
  return (
    <div className="grid min-w-0 gap-1.5 rounded-md border border-amber-500/40 p-3" data-testid="material-handling">
      <span className="inline-flex w-fit items-center gap-1 rounded-full border border-amber-500/30 bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
        <TriangleAlert className="h-3 w-3" aria-hidden />
        Handling
      </span>
      <CitedText id={`${block.id}-handling`} sentences={block.handling} className="text-sm leading-7 text-ink-700" />
    </div>
  );
}

export function MaterialCardView({ block }: { block: MaterialCardBlock }) {
  return (
    <article className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3 rounded-lg border border-line-200 bg-card p-4 sm:p-5" data-testid="material-card">
      <header className="min-w-0">
        <h3 className="break-words font-display text-lg font-bold text-ink-900">{block.name}</h3>
        {block.localNames.length > 0 || block.wikidataId ? (
          <p className="mt-0.5 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 text-sm text-ink-500" data-testid="material-local-names">
            {block.localNames.length > 0 ? (
              <span className="min-w-0 break-words">
                <span className="sr-only">Local names: </span>
                {block.localNames.join(" · ")}
              </span>
            ) : null}
            {block.wikidataId ? <Outbound href={wikidataUrl(block.wikidataId)}>Wikidata</Outbound> : null}
          </p>
        ) : null}
      </header>
      <MaterialTiles block={block} />
      <CitedText id={`${block.id}-facts`} sentences={block.facts} className="text-sm leading-7 text-ink-700" />
      <Handling block={block} />
    </article>
  );
}
