import type { ComponentViewProps } from "@/lib/componentViewContract";
import { equationCardShape } from "@/lib/componentSpecsScienceFigures";
import { parseShape } from "@/lib/shape";

import { EquationLineView } from "./parts/Chemistry";

export function EquationCard({ spec, renderUnit }: ComponentViewProps) {
  const card = parseShape(equationCardShape, spec);
  return (
    <div className="kv-hyp wrap">
      <div className="kv-hyp-in">
        <p className="kicker">{renderUnit(card.kicker)}</p>
        <p className="kv-hyp-t">{renderUnit(card.title)}</p>
      </div>
      <div className="bn-spec">
        <div className="hyp">
          <p className="hyp-mark">{renderUnit(card.mark)}</p>
          <div className="eq hyp-eq">
            <EquationLineView line={card.line} />
          </div>
          <p className="hyp-why">{renderUnit(card.why)}</p>
        </div>
      </div>
    </div>
  );
}
