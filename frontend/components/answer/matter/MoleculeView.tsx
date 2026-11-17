"use client";

import { useRef, useState } from "react";
import { Move3d, RotateCw } from "lucide-react";

import { MoleculeCaption } from "@/components/answer/matter/MoleculeCaption";
import { useMolecule, type MoleculeStatus } from "@/components/answer/matter/useMolecule";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { RetryLine } from "@/components/RemotePanels";
import type { Molecule3dBlock } from "@/lib/explainerMatter";
import type { MoleculeScene } from "@/lib/moleculeViewer";
import { cn } from "@/lib/utils";

export const TURN_STEP_DEGREES = 90;
export const TURN_STEP_MILLISECONDS = 600;

const TOOL = "inline-flex min-h-9 items-center gap-1.5 rounded-full border px-3 text-xs font-semibold transition-colors pointer-coarse:min-h-11";
const TOOL_RESTING = "border-line-200 bg-card text-ink-700 hover:border-purple-300 hover:bg-purple-50 dark:hover:bg-purple-950/40";
const TOOL_ON = "border-purple-700 bg-purple-700 text-white";

function MoleculeTools({ scene, exploring, reduce, onExplore }: { scene: MoleculeScene; exploring: boolean; reduce: boolean; onExplore: (on: boolean) => void }) {
  return (
    <div role="toolbar" aria-label="3D view" className="flex flex-wrap gap-2" data-testid="molecule-tools">
      <button type="button" className={cn(TOOL, TOOL_RESTING)} onClick={() => scene.turn(TURN_STEP_DEGREES, reduce ? 0 : TURN_STEP_MILLISECONDS)}>
        <RotateCw className="h-3.5 w-3.5" aria-hidden />
        Turn
      </button>
      <button type="button" aria-pressed={exploring} className={cn(TOOL, exploring ? TOOL_ON : TOOL_RESTING)} onClick={() => onExplore(!exploring)}>
        <Move3d className="h-3.5 w-3.5" aria-hidden />
        Explore
      </button>
    </div>
  );
}

function FrameCover({ status }: { status: MoleculeStatus }) {
  if (status === "ready") return null;
  const loading = status !== "failed";
  return (
    <div
      role={loading ? "status" : undefined}
      aria-label={loading ? "Loading 3D view" : undefined}
      className={cn("absolute inset-0 bg-field-100", loading ? "animate-pulse" : null)}
      data-testid="molecule-placeholder"
    />
  );
}

export function MoleculeView({ block }: { block: Molecule3dBlock }) {
  const reduce = useAppReducedMotion();
  const frameRef = useRef<HTMLDivElement | null>(null);
  const molecule = useMolecule(frameRef, block.pubchemCid, reduce);
  const [exploring, setExploring] = useState(false);
  if (molecule.status === "hidden") return null;
  const ready = molecule.status === "ready" && molecule.scene !== null;
  return (
    <figure className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3" data-testid="molecule-3d" data-status={molecule.status}>
      <div className="relative isolate min-w-0 overflow-hidden rounded-lg border border-line-200 bg-surface-50">
        <div ref={frameRef} aria-hidden className="relative aspect-[4/3] w-full" data-testid="molecule-frame" />
        <FrameCover status={molecule.status} />
        {ready && !exploring ? <div aria-hidden className="absolute inset-0" data-testid="molecule-guard" /> : null}
      </div>
      {molecule.status === "failed" ? <RetryLine message="The 3D view didn't load." onRetry={molecule.retry} /> : null}
      <MoleculeCaption block={block} />
      {ready && molecule.scene ? <MoleculeTools scene={molecule.scene} exploring={exploring} reduce={reduce} onExplore={setExploring} /> : null}
    </figure>
  );
}
