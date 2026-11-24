import type { ReactNode } from "react";

import { swatchCardsShape, type ColourCard, type Swatch } from "@/lib/componentSpecsPlates";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

const SWATCH_SIZE = 80;
const JOINS = { becomes: { className: "pair-arrow", mark: "→" }, or: { className: "pair-arrow vs", mark: "or" } } as const;

function SwatchFigure({ swatch, weave, renderUnit }: { swatch: Swatch; weave: string; renderUnit: (ref: string) => ReactNode }) {
  return (
    <figure>
      <div className="sq">
        <span className="swatch">
          <svg viewBox={`0 0 ${SWATCH_SIZE} ${SWATCH_SIZE}`} aria-hidden="true">
            <rect width={SWATCH_SIZE} height={SWATCH_SIZE} fill={`var(--dye-${swatch.dye})`} />
            <rect width={SWATCH_SIZE} height={SWATCH_SIZE} fill={`url(#${weave})`} />
          </svg>
        </span>
      </div>
      <figcaption>{renderUnit(swatch.caption)}</figcaption>
    </figure>
  );
}

type ColourProps = { colour: ColourCard; weave: string; renderUnit: (ref: string) => ReactNode };

function Swatches({ colour, weave, renderUnit }: ColourProps) {
  if (!colour.after) return null;
  const join = colour.before && colour.join ? JOINS[colour.join] : null;
  return (
    <div className="pair">
      {colour.before && join ? (
        <>
          <SwatchFigure swatch={colour.before} weave={weave} renderUnit={renderUnit} />
          <span className={join.className} aria-hidden="true">
            {join.mark}
          </span>
        </>
      ) : null}
      <SwatchFigure swatch={colour.after} weave={weave} renderUnit={renderUnit} />
    </div>
  );
}

function Colour({ colour, weave, renderUnit }: ColourProps) {
  return (
    <li className="colour">
      <Swatches colour={colour} weave={weave} renderUnit={renderUnit} />
      <h3>{renderUnit(colour.name)}</h3>
      <p className="agent">{renderUnit(colour.agent)}</p>
      <p className="ctext">
        {renderUnit(colour.text)}
        {colour.why ? (
          <>
            {" "}
            {renderUnit(colour.why)}
          </>
        ) : null}
      </p>
    </li>
  );
}

export function SwatchCardsView({ spec, renderUnit }: ComponentViewProps) {
  const cards = parseShape(swatchCardsShape, spec);
  return (
    <section className="four" aria-labelledby={cards.titleId}>
      <div className="wrap">
        <div className="four-head">
          <div>
            <p className="chapter-no">{renderUnit(cards.chapterNo)}</p>
            <h2 className="t-h2" id={cards.titleId}>
              {renderUnit(cards.title)}
            </h2>
          </div>
          <div>
            <p className="four-intro">{renderUnit(cards.intro)}</p>
          </div>
        </div>
        <ul className="colours">
          {cards.colours.map((colour) => (
            <Colour key={colour.name} colour={colour} weave={cards.weave} renderUnit={renderUnit} />
          ))}
        </ul>
      </div>
    </section>
  );
}
