"use client";

import { useId, useMemo } from "react";

import { LegacyScope } from "@/components/monograph/LegacyScope";
import { useMonographSlot } from "@/components/monograph/MonographSlotContext";
import { sourceReliabilityLabel } from "@/lib/citations";
import { explainerSpecShape, parseToolSpec, type QuoteCard } from "@/lib/componentSpecsTools";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import type { SourceReliability } from "@/lib/types";

const MARKS = ["a", "b", "c", "d"] as const;

function Mark({ letter, keyed }: { letter: (typeof MARKS)[number]; keyed: boolean }) {
  return keyed ? (
    <span className={`mk ${letter}`} aria-hidden="true">
      {letter}
    </span>
  ) : null;
}

function Card({ card, renderUnit }: { card: QuoteCard; renderUnit: ComponentViewProps["renderUnit"] }) {
  const { sources } = useMonographSlot();
  const source = sources[card.source];
  if (!source) return null;
  const grade = source.grade as SourceReliability | null;
  return (
    <figure className="qcard">
      <figcaption>
        <b>
          <Mark letter="a" keyed={card.keyed} />
          {source.number}
        </b>
        <strong>{source.title}</strong>
        <span>{card.byline}</span>
      </figcaption>
      <blockquote>
        <Mark letter="b" keyed={card.keyed} />
        {card.quoteUnit ? renderUnit(card.quoteUnit) : card.quote}
      </blockquote>
      <p className="qmeta">
        <span className="loc">
          <Mark letter="c" keyed={card.keyed} />
          {card.locator}
        </span>
        {grade ? (
          <span className="relw">
            <Mark letter="d" keyed={card.keyed} />
            <span className={`rel ${grade}`} aria-hidden="true" />
            {sourceReliabilityLabel(grade)}
          </span>
        ) : null}
      </p>
    </figure>
  );
}

export function ExplainerView({ spec, renderUnit }: ComponentViewProps) {
  const explainer = useMemo(() => parseToolSpec(explainerSpecShape, spec), [spec]);
  const titleId = useId();
  return (
    <LegacyScope scope="mb">
      <section className="howcite" aria-labelledby={titleId}>
        <div className="wrap">
          <div className="hc-grid">
            <div className="hc-text">
              <p className="chapter-no">{renderUnit(explainer.kicker)}</p>
              <h3 className="t-h2" id={titleId}>
                {renderUnit(explainer.title)}
              </h3>
              <p className="hc-sent">{renderUnit(explainer.sentence)}</p>
              <ol className="hc-keys">
                {explainer.keys.map((ref) => (
                  <li key={ref}>{renderUnit(ref)}</li>
                ))}
              </ol>
            </div>
            <div className="hc-cards" role="group" aria-label={explainer.cardsLabel}>
              {explainer.cards.map((card) => (
                <Card key={`${card.source}-${card.locator}`} card={card} renderUnit={renderUnit} />
              ))}
            </div>
          </div>
        </div>
      </section>
    </LegacyScope>
  );
}
