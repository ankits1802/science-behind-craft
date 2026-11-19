import { paint } from "@/lib/componentSpecsScienceParts";
import { SWATCH_MARKS, type ChemistryPart, type LaneItem, type LaneSpecies } from "@/lib/componentSpecsSciencePlayers";

import { EquationView } from "./parts/Chemistry";
import { RichText } from "./parts/Drawing";
import { PUBCHEM } from "./parts/props";
import type { RenderUnit } from "./parts/Text";

const isMark = (swatch: LaneSpecies["swatch"]): swatch is (typeof SWATCH_MARKS)[number] =>
  typeof swatch === "string" && (SWATCH_MARKS as readonly string[]).includes(swatch);

function Species({ species }: { species: LaneSpecies }) {
  const swatch = species.swatch;
  return (
    <div className="spc">
      {isMark(swatch) ? (
        <span className={`ssw ${swatch}`} aria-hidden="true" />
      ) : (
        <span className="ssw" style={{ background: paint(swatch) }} aria-hidden="true" />
      )}
      <span className="nm">
        <RichText runs={species.name} />
      </span>
      {species.formula ? (
        <span className="fm">
          <RichText runs={species.formula} />
        </span>
      ) : null}
      <span className="st">
        <RichText runs={species.state} />
        {species.cid !== null ? (
          <a className="cid" href={PUBCHEM(species.cid)} rel="noopener" target="_blank">{`CID ${species.cid}`}</a>
        ) : null}
      </span>
    </div>
  );
}

function LaneEntry({ item }: { item: LaneItem }) {
  if (item.item === "species") return <Species species={item} />;
  if (item.item === "plus") {
    return (
      <span className="op" aria-hidden="true">
        +
      </span>
    );
  }
  return (
    <span className="arr">
      <i className="ln" aria-hidden="true" />
      <small>{item.label}</small>
    </span>
  );
}

export function ChemistryPartView({ part, renderUnit }: { part: ChemistryPart; renderUnit: RenderUnit }) {
  if (part.part === "none") return <p className="eq-none">{renderUnit(part.unit)}</p>;
  if (part.part === "equation") return <EquationView equation={part.equation} renderUnit={renderUnit} />;
  return (
    <div className="lane" role="group" aria-label={part.label}>
      {part.items.map((item, index) => <LaneEntry key={index} item={item} />)}
    </div>
  );
}
