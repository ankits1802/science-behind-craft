import type { FormulaChip, PanelPart } from "@/lib/componentSpecsScienceLab";

import { Drawing, RichText } from "./parts/Drawing";
import { PUBCHEM } from "./parts/props";
import { Slot } from "./parts/Slot";
import { Block, type RenderUnit } from "./parts/Text";

const hook = (name: string) => ({ [`data-${name}`]: "" });

function Chip({ chip }: { chip: FormulaChip }) {
  return (
    <span className="formula">
      <b>
        <RichText runs={chip.formula} />
      </b>
      <span>{chip.name}</span>
      {chip.cid !== null ? (
        <a href={PUBCHEM(chip.cid)} rel="noopener" target="_blank">{`PubChem CID ${chip.cid}`}</a>
      ) : (
        <span>{chip.source}</span>
      )}
    </span>
  );
}

function Controls({ part }: { part: Extract<PanelPart, { part: "stepper" | "switch" }> }) {
  if (part.part === "stepper") {
    return (
      <div className="lab-steps">
        <div className="actions" data-count="1">
          <button className="btn sm" type="button" {...hook(part.hook)}>
            <RichText runs={part.action} />
          </button>
        </div>
        <span className="tap-day" role="status" aria-live="polite" {...hook(part.statusHook)}>
          {part.status}
        </span>
      </div>
    );
  }
  return (
    <div className="switch-row lab-sw">
      <span className="sw-text">
        <span className="sw-label" id={`sw-${part.hook}`}>
          <RichText runs={part.label} />
        </span>
        <span className="sw-desc">{part.description}</span>
      </span>
      <button className="switch" type="button" role="switch" aria-checked="false" aria-labelledby={`sw-${part.hook}`} {...hook(`${part.hook}-sw`)} />
    </div>
  );
}

export function PanelPartView({ part, chosen, renderUnit }: { part: PanelPart; chosen: string; renderUnit: RenderUnit }) {
  switch (part.part) {
    case "text":
      return <Block block={part.text} renderUnit={renderUnit} />;
    case "formulas":
      return (
        <div className="forms" data-forms={part.option ?? undefined} hidden={part.option !== null && part.option !== chosen}>
          {part.chips.map((chip) => <Chip key={chip.name} chip={chip} />)}
        </div>
      );
    case "more":
      return (
        <div className="kv-lab-more">
          {part.parts.map((inner, index) => <PanelPartView key={index} part={inner} chosen={chosen} renderUnit={renderUnit} />)}
        </div>
      );
    case "stepper":
    case "switch":
      return <Controls part={part} />;
    default:
      return <Figure part={part} renderUnit={renderUnit} />;
  }
}

function Figure({ part, renderUnit }: { part: Extract<PanelPart, { part: "same" | "chart" | "stage" }>; renderUnit: RenderUnit }) {
  if (part.part === "same") {
    return (
      <div className="lab-same">
        <p className="lk">{renderUnit(part.label)}</p>
        {part.paragraphs.map((unit) => <p key={unit}>{renderUnit(unit)}</p>)}
      </div>
    );
  }
  if (part.part === "chart") {
    return (
      <div className="days">
        <p className="chart-title days-t">{renderUnit(part.title)}</p>
        <div className="days-plot">
          <Slot slot={part.chart} />
        </div>
        <p className="src-line">{renderUnit(part.source)}</p>
      </div>
    );
  }
  return (
    <div className="stagebox">
      <Drawing node={part.drawing} />
      {part.note !== null && part.noteHook !== null ? (
        <p className="sb-note" {...hook(part.noteHook)} hidden>
          {renderUnit(part.note)}
        </p>
      ) : null}
    </div>
  );
}
