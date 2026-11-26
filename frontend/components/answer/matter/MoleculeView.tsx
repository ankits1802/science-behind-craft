"use client";

import { useRef, useState } from "react";
import { Move3d, Pause, Rotate3d, RotateCw, ZoomIn, ZoomOut, type LucideIcon } from "lucide-react";

import { MoleculeCaption } from "@/components/answer/matter/MoleculeCaption";
import { useMolecule, type MoleculeStatus } from "@/components/answer/matter/useMolecule";
import { useMoleculeTurn, type MoleculeTurn } from "@/components/answer/matter/useMoleculeTurn";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { MapRetry } from "@/components/map/MapRetry";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import type { Molecule3dBlock } from "@/lib/explainerMatter";
import type { MoleculeScene } from "@/lib/moleculeViewer";

export const TURN_STEP_DEGREES = 90;
export const TURN_STEP_MILLISECONDS = 600;
export const ZOOM_STEP = 1.25;

export type MoleculeMove = "turn" | "tilt" | "zoomIn" | "zoomOut";

export const MOLECULE_MOVES: readonly { move: MoleculeMove; label: string; Icon: LucideIcon }[] = [
  { move: "turn", label: "Turn", Icon: RotateCw },
  { move: "tilt", label: "Tilt", Icon: Rotate3d },
  { move: "zoomIn", label: "Zoom in", Icon: ZoomIn },
  { move: "zoomOut", label: "Zoom out", Icon: ZoomOut }
];

export function moveMolecule(scene: MoleculeScene, move: MoleculeMove, reduce: boolean): void {
  const milliseconds = reduce ? 0 : TURN_STEP_MILLISECONDS;
  if (move === "turn") scene.turn(TURN_STEP_DEGREES, milliseconds);
  else if (move === "tilt") scene.tilt(TURN_STEP_DEGREES, milliseconds);
  else scene.zoom(move === "zoomIn" ? ZOOM_STEP : 1 / ZOOM_STEP, milliseconds);
}

export type TurnControl = Pick<MoleculeTurn, "wanted" | "motion" | "toggle">;

function TurnButton({ turn }: { turn: TurnControl }) {
  const pausable = turn.motion && turn.wanted;
  const Icon = pausable ? Pause : RotateCw;
  return (
    <Button variant="quiet" size="sm" aria-pressed={turn.motion ? turn.wanted : undefined} onClick={turn.toggle} data-testid="molecule-turn">
      <Icon className="h-4 w-4" aria-hidden />
      {pausable ? "Pause" : "Turn"}
    </Button>
  );
}

export function MoleculeTools({ scene, turn, exploring, reduce, onExplore }: { scene: MoleculeScene; turn: TurnControl; exploring: boolean; reduce: boolean; onExplore: (on: boolean) => void }) {
  return (
    <ActionGroup align="start" role="toolbar" aria-label="3D view" data-testid="molecule-tools">
      {MOLECULE_MOVES.map(({ move, label, Icon }) =>
        move === "turn" ? (
          <TurnButton key={move} turn={turn} />
        ) : (
          <Button key={move} variant="quiet" size="sm" onClick={() => moveMolecule(scene, move, reduce)}>
            <Icon className="h-4 w-4" aria-hidden />
            {label}
          </Button>
        )
      )}
      <Button variant="quiet" size="sm" aria-pressed={exploring} onClick={() => onExplore(!exploring)}>
        <Move3d className="h-4 w-4" aria-hidden />
        Explore
      </Button>
    </ActionGroup>
  );
}

function FrameCover({ status }: { status: MoleculeStatus }) {
  if (status === "ready") return null;
  const loading = status !== "failed";
  return <div role={loading ? "status" : undefined} aria-label={loading ? "Loading 3D view" : undefined} className={loading ? "kv-sk motion-pulse absolute inset-0" : "absolute inset-0 bg-sunk"} data-testid="molecule-placeholder" />;
}

export function MoleculeView({ block }: { block: Molecule3dBlock }) {
  const reduce = useAppReducedMotion();
  const frameRef = useRef<HTMLDivElement | null>(null);
  const figureRef = useRef<HTMLElement | null>(null);
  const molecule = useMolecule(frameRef, block.pubchemCid);
  const [exploring, setExploring] = useState(false);
  const scene = molecule.status === "ready" ? molecule.scene : null;
  const turn = useMoleculeTurn(scene, figureRef, exploring, () => {
    if (scene) moveMolecule(scene, "turn", true);
  });
  if (molecule.status === "hidden") return null;
  return (
    <figure ref={figureRef} className="m-0 grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3" data-testid="molecule-3d" data-status={molecule.status} data-turning={turn.turning ? "true" : "false"} {...turn.holds}>
      <div className="relative isolate min-w-0 overflow-hidden rounded-plate border border-rule bg-sunk">
        <div ref={frameRef} aria-hidden className="relative aspect-[4/3] w-full" data-testid="molecule-frame" />
        <FrameCover status={molecule.status} />
        {scene && !exploring ? <div aria-hidden className="absolute inset-0" data-testid="molecule-guard" /> : null}
      </div>
      {molecule.status === "failed" ? <MapRetry message="The 3D view could not be drawn. Try again in a moment." onRetry={molecule.retry} /> : null}
      {scene ? <MoleculeTools scene={scene} turn={turn} exploring={exploring} reduce={reduce} onExplore={setExploring} /> : null}
      <MoleculeCaption block={block} />
    </figure>
  );
}
