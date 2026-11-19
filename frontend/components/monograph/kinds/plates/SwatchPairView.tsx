import { swatchPairShape, type PairSwatch } from "@/lib/componentSpecsPlates";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

import { HeldText } from "./HeldText";
import { SpecDrawings } from "./SpecDrawing";

const SWATCH_SIZE = 100;

function SwatchFrame({ swatch, weave }: { swatch: PairSwatch; weave: string }) {
  return (
    <span className="sw-frame">
      <svg viewBox={`0 0 ${SWATCH_SIZE} ${SWATCH_SIZE}`} aria-hidden="true">
        <rect width={SWATCH_SIZE} height={SWATCH_SIZE} fill={`var(--dye-${swatch.ground})`} />
        <SpecDrawings elements={swatch.motif} />
        <rect width={SWATCH_SIZE} height={SWATCH_SIZE} fill={`url(#${weave})`} />
      </svg>
      <b>{swatch.label}</b>
    </span>
  );
}

export function SwatchPairView({ spec, renderUnit }: ComponentViewProps) {
  const pair = parseShape(swatchPairShape, spec);
  return (
    <li className={pair.wide ? "ws-card wide" : "ws-card"} id={pair.id}>
      <div className="ws-vis">
        <div className={pair.pairClass} role="img" aria-label={pair.description}>
          {pair.swatches.map((swatch) => (
            <SwatchFrame key={swatch.label} swatch={swatch} weave={pair.weave} />
          ))}
        </div>
      </div>
      <p className="when">{renderUnit(pair.when)}</p>
      <h3>{renderUnit(pair.title)}</h3>
      {pair.texts.map((unit) => (
        <p key={unit} className="ws-t">
          {renderUnit(unit)}
        </p>
      ))}
      {pair.go ? (
        <p className="ws-go">
          <button className="text-link" type="button" data-goto-stage={pair.go.stage}>
            <HeldText nodes={pair.go.label} />
          </button>
        </p>
      ) : null}
    </li>
  );
}
