"use client";

import { ExternalLink } from "lucide-react";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { EvidenceLevelBadge } from "@/components/answer/EvidenceBadge";
import { ClaimList } from "@/components/craft/ClaimList";
import { MATERIAL_KIND_LABEL, MATERIAL_ROLE_LABEL, pubchemHref } from "@/lib/processView";
import type { StageMaterial } from "@/lib/scienceContract";

export function StageMaterials({ materials }: { materials: readonly StageMaterial[] }) {
  return (
    <ul className="grid gap-2 sm:grid-cols-2">
      {materials.map((material) => (
        <li key={material.id} className="rounded-md border border-line-200 bg-card px-3 py-2.5" data-testid="process-material">
          <MaterialHeading material={material} />
          {material.compound ? <CompoundLine compound={material.compound} /> : null}
          {material.quantityText ? <p className="mt-1 text-xs text-ink-500">{material.quantityText}</p> : null}
          <div className="mt-2">
            <ClaimList claims={material.claims} size="compact" />
          </div>
        </li>
      ))}
    </ul>
  );
}

function MaterialHeading({ material }: { material: StageMaterial }) {
  const role = MATERIAL_ROLE_LABEL[material.role];
  const kind = MATERIAL_KIND_LABEL[material.kind];
  return (
    <div className="flex flex-wrap items-start justify-between gap-2">
      <span className="min-w-0">
        <span className="block text-sm font-semibold text-ink-900">{material.name}</span>
        <span className="block text-xs text-ink-500">{kind === role ? role : `${role} · ${kind}`}</span>
      </span>
      <EvidenceLevelBadge level={material.level} />
    </div>
  );
}

function CompoundLine({ compound }: { compound: NonNullable<StageMaterial["compound"]> }) {
  const href = pubchemHref(compound.pubchemCid);
  return (
    <p className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-700">
      {compound.formula ? <ChemEquation equation={compound.formula} display={false} label={compound.formula} className="text-sm" /> : null}
      <span>{compound.name}</span>
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 font-medium text-purple-700 hover:underline dark:text-purple-300">
          PubChem
          <ExternalLink className="h-3 w-3" aria-hidden />
          <span className="sr-only">(opens in a new tab)</span>
        </a>
      ) : null}
    </p>
  );
}
