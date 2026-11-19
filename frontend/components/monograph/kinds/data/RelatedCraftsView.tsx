import type { ReactNode } from "react";

import { HeldText } from "@/components/monograph/kinds/plates/HeldText";
import { relatedCraftsShape, type RelatedCraft } from "@/lib/componentSpecsData";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

const PLATE_BLEED = { x: -50, y: -50, width: 400, height: 250 };

function CraftCard({ craft, weave, renderUnit }: { craft: RelatedCraft; weave: string; renderUnit: (ref: string) => ReactNode }) {
  return (
    <div className="rel-card">
      <div className="tplate kv-kin-sw" data-tile={craft.tile}>
        <svg className="kv-sw-svg" viewBox="0 0 300 150" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
          <rect {...PLATE_BLEED} fill={`url(#tile-${craft.tile})`} />
          <rect {...PLATE_BLEED} fill={`url(#${weave})`} />
        </svg>
        <span className="kv-sw-l">
          <HeldText nodes={craft.swatch} />
        </span>
        <span className="tp-body">
          <span className="tp-top">{craft.top}</span>
          <span className="tp-name">
            <span className="native en">{craft.name}</span>
          </span>
        </span>
        <span className="tp-label">
          <span className="tp-foot">
            <span>{`${craft.place} · ${craft.sources} sources`}</span>
            <span className="tags">
              {craft.monograph ? <span className="tag mono">Monograph</span> : null}
              {craft.gi ? (
                <span className="tag">
                  GI<span className="vh"> registered</span>
                </span>
              ) : null}
            </span>
          </span>
        </span>
      </div>
      <div className="rel-share">
        <span className="k">
          <HeldText nodes={craft.shares} />
        </span>
        <p>{renderUnit(craft.sentence)}</p>
      </div>
    </div>
  );
}

export function RelatedCraftsView({ spec, renderUnit }: ComponentViewProps) {
  const related = parseShape(relatedCraftsShape, spec);
  return (
    <div className="kv-related">
      <div className="end-block">
        <div className="end-h">
          <h3>{renderUnit(related.title)}</h3>
          <span className="kicker">{related.kicker}</span>
        </div>
        <p className="end-dek">{renderUnit(related.description)}</p>
        <div className="related">
          {related.crafts.map((craft) => (
            <CraftCard key={craft.name} craft={craft} weave={related.weave} renderUnit={renderUnit} />
          ))}
        </div>
      </div>
    </div>
  );
}
