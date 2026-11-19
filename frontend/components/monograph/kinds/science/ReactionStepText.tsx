import type { StepText } from "@/lib/componentSpecsSciencePlayers";

import { PlayerDiffers } from "./parts/Differs";
import type { RenderUnit } from "./parts/Text";

export function ReactionStepText({ text, step, shown, renderUnit }: { text: StepText; step: number; shown: boolean; renderUnit: RenderUnit }) {
  return (
    <section className="rp-step" hidden={!shown} aria-label={`Step ${step}`}>
      <p className="kicker">{renderUnit(text.kicker)}</p>
      <h4>{renderUnit(text.heading)}</h4>
      {text.paragraphs.map((unit) => <p key={unit} className="rp-p">{renderUnit(unit)}</p>)}
      {text.bond !== null ? (
        <p className="rp-bond">
          <span className="kv-mk" aria-hidden="true" />
          {text.bond}
        </p>
      ) : null}
      {text.link !== null ? <p className="rp-link">{renderUnit(text.link)}</p> : null}
      {text.conditions.length ? (
        <dl className="rp-cond">
          {text.conditions.map((condition) => (
            <div key={condition.term}>
              <dt>{renderUnit(condition.term)}</dt>
              <dd>{renderUnit(condition.value)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {text.differs !== null ? <PlayerDiffers differs={text.differs} renderUnit={renderUnit} /> : null}
    </section>
  );
}
