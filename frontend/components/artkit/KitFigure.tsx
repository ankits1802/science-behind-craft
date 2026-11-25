import type { ReactNode } from "react";

import { movingPart, type KitDiagramSpec } from "@/lib/componentSpecsKit";

import { kitIds } from "./kitIds";
import { KitPanelView } from "./KitPanelView";
import { KitTextures } from "./KitTextures";
import { NearKitPlay } from "./NearKitPlay";

type FigureProps = { spec: KitDiagramSpec; label: string; renderUnit: (ref: string) => ReactNode; unitText?: (ref: string) => string };

export function kitFigureId(label: string): string {
  return `${kitIds(label).base}-figure`;
}

export function KitFigure({ spec, label, renderUnit, unitText }: FigureProps) {
  const ids = kitIds(label);
  const figureId = kitFigureId(label);
  const motions = spec.panels.map((panel) => (movingPart(panel) === null ? null : (panel.motion ?? null)));
  return (
    <div className="kv-kit" id={figureId} data-layout={spec.layout} data-count={spec.panels.length}>
      <KitTextures ids={ids} />
      <ol className="kv-kit-panels">
        {spec.panels.map((panel, index) => (
          <KitPanelView key={`${panel.label}-${index}`} panel={panel} index={index} layout={spec.layout} ids={ids} renderUnit={renderUnit} />
        ))}
      </ol>
      {motions.some((motion) => motion !== null) ? <NearKitPlay figureId={figureId} labels={spec.panels.map((panel) => unitText?.(panel.label) ?? "")} motions={motions} /> : null}
    </div>
  );
}
