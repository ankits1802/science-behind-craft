import type { ComponentViewProps } from "@/lib/componentViewContract";
import { materialCardsShape, type MaterialCard } from "@/lib/componentSpecsScienceExplainers";
import { parseShape } from "@/lib/shape";

import { swatchStyle } from "./parts/props";
import { Slot } from "./parts/Slot";
import type { RenderUnit } from "./parts/Text";

function Card({ card, renderUnit }: { card: MaterialCard; renderUnit: RenderUnit }) {
  return (
    <div className="mat">
      {card.swatch === "crystal" ? (
        <span className="msw crys" aria-hidden="true" />
      ) : (
        <span className="msw" style={swatchStyle(card.swatch)} aria-hidden="true" />
      )}
      <p className="mk2">{renderUnit(card.role)}</p>
      <h4>{renderUnit(card.name)}</h4>
      <p className="loc">{renderUnit(card.local)}</p>
      {card.botanical ? <p className="bot">{renderUnit(card.botanical)}</p> : null}
      <p className="chem">{renderUnit(card.chemistry)}</p>
      <div className="facts">
        {card.facts.map((fact) => <p key={fact}>{renderUnit(fact)}</p>)}
      </div>
    </div>
  );
}

export function MaterialCards({ spec, renderUnit }: ComponentViewProps) {
  const section = parseShape(materialCardsShape, spec);
  return (
    <section className="sec" id={section.id} aria-labelledby={section.headingId}>
      <div className="spread">
        <div className="main">
          <h3 className="sec-h" id={section.headingId}>
            <span className="sw sw-mat" aria-hidden="true" />
            {section.heading}
          </h3>
          <p className="sec-intro t-body">{renderUnit(section.intro)}</p>
        </div>
      </div>
      <div className="mats">
        {section.cards.map((card) => <Card key={card.name} card={card} renderUnit={renderUnit} />)}
      </div>
      {section.after.map((slot) => <Slot key={slot.component} slot={slot} />)}
    </section>
  );
}
