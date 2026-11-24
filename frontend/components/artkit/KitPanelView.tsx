import type { ReactNode } from "react";

import type { KitLayout } from "@/lib/artKit";
import { kitMotionClass } from "@/lib/artKitMotion";
import { movingPart, type KitPanel } from "@/lib/componentSpecsKit";

import { KitKey } from "./KitKey";
import { PANEL_BOXES, PlacedPart } from "./KitPartArt";
import { partIds, type KitIds, type Moving } from "./kitIds";

type RenderUnit = (ref: string) => ReactNode;
type PanelProps = { panel: KitPanel; index: number; layout: KitLayout; ids: KitIds; renderUnit: RenderUnit };

const SECTION_BOX = [{ x: 0, y: 0, size: 120 }];

function Arrow() {
  return (
    <svg className="kv-kit-arrow" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M3 10 H15 M10.5 5.5 L15.5 10 L10.5 14.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function PanelArt({ panel, index, layout, ids }: Omit<PanelProps, "renderUnit">) {
  const section = layout === "section";
  const boxes = section ? SECTION_BOX : PANEL_BOXES[panel.parts.length];
  const moves = movingPart(panel);
  const moving = (at: number): Moving | undefined => (moves === at && panel.motion ? { className: kitMotionClass(panel.motion), panel: index } : undefined);
  return (
    <div className="kv-kit-art">
      <svg viewBox={section ? "0 0 120 120" : "0 0 240 160"} aria-hidden="true" focusable="false">
        {panel.parts.map((part, at) => (
          <PlacedPart key={`${part.part}-${at}`} part={part} ids={partIds(ids, `p${index}-${at}`)} box={boxes[at]} moving={moving(at)} />
        ))}
      </svg>
    </div>
  );
}

export function KitPanelView({ panel, index, layout, ids, renderUnit }: PanelProps) {
  return (
    <li className="kv-kit-panel" data-kit-panel={index}>
      {panel.via ? (
        <p className="kv-kit-via">
          <Arrow />
          <span>{renderUnit(panel.via)}</span>
        </p>
      ) : null}
      <p className="kv-kit-step">
        {layout === "section" ? null : <span className="kv-kit-num">{index + 1}</span>}
        <span>{renderUnit(panel.label)}</span>
      </p>
      <PanelArt panel={panel} index={index} layout={layout} ids={ids} />
      <KitKey parts={panel.parts} ids={ids} renderUnit={renderUnit} />
      {panel.text ? <p className="kv-kit-text">{renderUnit(panel.text)}</p> : null}
    </li>
  );
}
