import type { ReactNode } from "react";

import { ART_KIT } from "@/lib/artKit";
import { partMaterials, type KitPart } from "@/lib/componentSpecsKit";

import { paint, url, type KitIds } from "./kitIds";

type RenderUnit = (ref: string) => ReactNode;

export function KitSwatch({ material, ids }: { material: string; ids: KitIds }) {
  const earth = material === ART_KIT.earth;
  return (
    <span className="kv-kit-swatch" aria-hidden="true" data-kit-swatch={material}>
      <svg viewBox="0 0 16 16" focusable="false">
        <rect width="16" height="16" fill={earth ? "var(--sunk)" : paint(material)} />
        <rect width="16" height="16" fill={url(earth ? ids.strata : ids.weave)} />
      </svg>
    </span>
  );
}

function Swatches({ materials, ids }: { materials: string[]; ids: KitIds }) {
  return (
    <span className="kv-kit-swatches" data-empty={materials.length ? undefined : ""}>
      {materials.map((material) => (
        <KitSwatch key={material} material={material} ids={ids} />
      ))}
    </span>
  );
}

function KeyItem({ part, ids, renderUnit }: { part: KitPart; ids: KitIds; renderUnit: RenderUnit }) {
  return (
    <li className="kv-kit-key-item" data-kit-key={part.part}>
      <span className="kv-kit-key-row">
        <Swatches materials={partMaterials(part)} ids={ids} />
        <span className="kv-kit-key-text">{renderUnit(part.label)}</span>
      </span>
      {part.part === "section" ? (
        <ol className="kv-kit-layers">
          {part.layers.map((layer, at) => (
            <li key={`${layer.label}-${at}`} className="kv-kit-key-row">
              <Swatches materials={[layer.material]} ids={ids} />
              <span className="kv-kit-key-text">{renderUnit(layer.label)}</span>
            </li>
          ))}
        </ol>
      ) : null}
    </li>
  );
}

export function KitKey({ parts, ids, renderUnit }: { parts: KitPart[]; ids: KitIds; renderUnit: RenderUnit }) {
  return (
    <ul className="kv-kit-key">
      {parts.map((part, at) => (
        <KeyItem key={`${part.label}-${at}`} part={part} ids={ids} renderUnit={renderUnit} />
      ))}
    </ul>
  );
}
