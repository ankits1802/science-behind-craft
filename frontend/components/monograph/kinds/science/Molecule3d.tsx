import type { ComponentViewProps } from "@/lib/componentViewContract";
import { molecule3dShape, type AtomKeyItem, type MoleculeModel } from "@/lib/componentSpecsScienceFigures";
import { parseShape } from "@/lib/shape";

import { Drawing, RichText } from "./parts/Drawing";
import { PUBCHEM, swatchStyle } from "./parts/props";
import { Blocks, FigureHeadLines } from "./parts/Text";

const DIAL_TURNS = 359;

export const turnedDegrees = (yaw: number) => Math.round((yaw * 180) / Math.PI);

function Model({ model }: { model: MoleculeModel }) {
  const turned = turnedDegrees(model.yaw);
  return (
    <figure className="mol" data-cid={model.cid} data-yaw={model.yaw} data-pitch={model.pitch} aria-labelledby={`${model.key}-n`}>
      <div className="mol-stage">
        <div
          className="mol-dial"
          role="slider"
          tabIndex={0}
          aria-label={model.dialLabel}
          aria-valuemin={0}
          aria-valuemax={DIAL_TURNS}
          aria-valuenow={turned}
          aria-valuetext={`Turned ${turned} degrees`}
          aria-describedby={`${model.key}-d`}
        >
          <Drawing node={model.drawing} />
        </div>
        <span className="mol-tag" aria-hidden="true">
          3D
        </span>
        <button className="btn sm mol-turn" type="button">
          Turn
        </button>
      </div>
      <figcaption>
        <span className="mn" id={`${model.key}-n`}>
          {model.name}
        </span>
        <span className="mf">
          <RichText runs={model.formula} />
        </span>
        <span className="mc">
          <span id={`${model.key}-d`}>{model.atoms}</span>
          <a href={PUBCHEM(model.cid)} rel="noopener" target="_blank">{`PubChem CID ${model.cid}`}</a>
        </span>
        <span className="ms">{model.note}</span>
      </figcaption>
    </figure>
  );
}

function KeyItem({ item }: { item: AtomKeyItem }) {
  const mark = item.swatch === "ring" ? <i className="ring" /> : item.swatch ? <i style={swatchStyle(item.swatch)} /> : null;
  return (
    <span>
      {mark}
      {item.label}
    </span>
  );
}

export function Molecule3d({ spec, renderUnit }: ComponentViewProps) {
  const figure = parseShape(molecule3dShape, spec);
  const grid = (
    <div className={`mol-grid n${figure.molecules.length}`}>
      {figure.molecules.map((model) => <Model key={model.key} model={model} />)}
    </div>
  );
  return (
    <figure className={figure.side.length ? "mols mol-two" : "mols"}>
      <FigureHeadLines head={figure.head} renderUnit={renderUnit} />
      {figure.side.length ? (
        <div className="mol-split">
          {grid}
          <div className="mol-side">
            <Blocks blocks={figure.side} renderUnit={renderUnit} />
          </div>
        </div>
      ) : (
        grid
      )}
      <p className="atomkey">
        {figure.key.map((item) => <KeyItem key={item.label} item={item} />)}
      </p>
    </figure>
  );
}
