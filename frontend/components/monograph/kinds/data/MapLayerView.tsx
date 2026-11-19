import type { ReactNode } from "react";

import { SpecDrawing } from "@/components/monograph/kinds/plates/SpecDrawing";
import { mapLayerShape, type MapExplorer, type ToggleGroup } from "@/lib/componentSpecsData";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

import { FigureHeadView, labelledBy, TextLines } from "./DataParts";

type RenderUnit = (ref: string) => ReactNode;

function Toggles({ group }: { group: ToggleGroup }) {
  return (
    <div className={group.classes.join(" ")} role="group" aria-label={group.label} {...{ [`data-${group.marker}`]: "" }}>
      {group.options.map((option) => (
        <button key={option.value} type="button" {...{ [`data-${group.optionKey}`]: option.value }} aria-pressed={option.pressed ? "true" : "false"}>
          {option.label}
        </button>
      ))}
    </div>
  );
}

function MapColumn({ map, renderUnit }: { map: MapExplorer; renderUnit: RenderUnit }) {
  return (
    <div className="rs-mapcol">
      <div className="rs-ctl">
        {map.controls.map((group) => (
          <Toggles key={group.marker} group={group} />
        ))}
      </div>
      <div className="rs-map" tabIndex={0} role="group" aria-roledescription="map" aria-label={map.mapLabel} aria-describedby={map.key.id}>
        <SpecDrawing element={map.drawing} />
        <div className="rs-inset" aria-hidden="true">
          <SpecDrawing element={map.inset.drawing} />
          <p>{renderUnit(map.inset.caption)}</p>
        </div>
        <div className="rs-tip" hidden></div>
      </div>
      <p className="vh" id={map.key.id}>
        {renderUnit(map.key.unit)}
      </p>
      <p className="vh" role="status" aria-live="polite" data-map-live=""></p>
      <div className="rs-legend" data-legend=""></div>
      <p className="rs-cap">{renderUnit(map.caption)}</p>
    </div>
  );
}

function MapSide({ map, renderUnit }: { map: MapExplorer; renderUnit: RenderUnit }) {
  return (
    <div className="rs-side">
      <TextLines lines={map.side} renderUnit={renderUnit} />
      <p className="rank-cap" data-rank-cap="">
        {renderUnit(map.rank.caption)}
      </p>
      <table className="rank-t" data-rank=""></table>
      <div className="actions rank-more start" data-count="1">
        <button className="btn sm" type="button" data-rank-all="" aria-expanded="false">
          {map.rank.more}
        </button>
      </div>
      <p className="src-note" data-rank-src=""></p>
    </div>
  );
}

function ExplorerView({ map, renderUnit }: { map: MapExplorer; renderUnit: RenderUnit }) {
  return (
    <figure className="fig" aria-labelledby={labelledBy(map.head)}>
      <FigureHeadView head={map.head} renderUnit={renderUnit} />
      <div className="rs" data-comp={map.comp} id={map.id}>
        <div className="rs-grid">
          <MapColumn map={map} renderUnit={renderUnit} />
          <MapSide map={map} renderUnit={renderUnit} />
        </div>
      </div>
    </figure>
  );
}

export function MapLayerView({ spec, renderUnit }: ComponentViewProps) {
  const layer = parseShape(mapLayerShape, spec);
  if (layer.drawing) return <SpecDrawing element={layer.drawing} />;
  if (layer.explorer) return <ExplorerView map={layer.explorer} renderUnit={renderUnit} />;
  throw new RangeError(`A ${layer.setting} map layer has its part`);
}
