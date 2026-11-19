import { labelCardShape } from "@/lib/componentSpecsPlates";
import { parseShape } from "@/lib/shape";

import { heldComponent, type NestingViewProps } from "./nesting";
import { SpecDrawing } from "./SpecDrawing";

export function LabelCardView(props: NestingViewProps) {
  const { spec, renderUnit } = props;
  const card = parseShape(labelCardShape, spec);
  const variant = card.variant;
  return (
    <div className={`label-card ${variant}`}>
      <p className={`lc-k ${variant}-k`}>{renderUnit(card.kicker)}</p>
      <div className={`${variant}-seal`}>
        <SpecDrawing element={card.seal} />
        <p className="lc-s">{renderUnit(card.sentence)}</p>
      </div>
      {heldComponent(props, card.inset)}
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
