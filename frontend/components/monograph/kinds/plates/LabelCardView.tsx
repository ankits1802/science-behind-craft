import { labelCardShape } from "@/lib/componentSpecsPlates";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

import { SpecDrawing } from "./SpecDrawing";

export function LabelCardView({ spec, renderUnit }: ComponentViewProps) {
  const card = parseShape(labelCardShape, spec);
  const variant = card.variant;
  return (
    <div className={`label-card ${variant}`}>
      <p className={`lc-k ${variant}-k`}>{renderUnit(card.kicker)}</p>
      <div className={`${variant}-seal`}>
        <SpecDrawing element={card.seal} />
        <p className="lc-s">{renderUnit(card.sentence)}</p>
      </div>
      <dl className={`${variant}-facts`}>
        {card.facts.map((fact) => (
          <div key={fact.term}>
            <dt>{renderUnit(fact.term)}</dt>
            <dd>{renderUnit(fact.value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
