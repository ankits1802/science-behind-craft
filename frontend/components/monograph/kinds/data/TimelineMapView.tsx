import type { ReactNode } from "react";

import { SpecDrawing } from "@/components/monograph/kinds/plates/SpecDrawing";
import { pythonJson, timelineMapShape, type TimelineMapSpec } from "@/lib/componentSpecsData";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

import { FigureHeadView, labelledBy, TextLines } from "./DataParts";
import { EventCardBody, TimelineAxisView, TimelineListView } from "./TimelineAxisView";

type RenderUnit = (ref: string) => ReactNode;

function Controls({ map, renderUnit }: { map: TimelineMapSpec; renderUnit: RenderUnit }) {
  return (
    <div className="tl-ctl">
      <div className="tl-play">
        <div className="actions start" data-count="1">
          <button className="btn sm" type="button" data-play="" aria-pressed="false" aria-label={map.play}>
            <svg viewBox="0 0 14 14" aria-hidden="true">
              <path d="M3 2 L12 7 L3 12 Z" fill="currentColor" />
            </svg>
            <span>Play</span>
          </button>
        </div>
        <p className="tl-status" role="status" aria-live="polite" data-tl-status="">
          {renderUnit(map.status)}
        </p>
      </div>
      <div className="switch-row">
        <span className="sw-text">
          <span className="sw-label" id={map.supply.labelId}>
            {map.supply.label}
          </span>
          <span className="sw-desc">{map.supply.description}</span>
        </span>
        <button className="switch" type="button" role="switch" aria-checked="false" aria-labelledby={map.supply.labelId} data-supply=""></button>
      </div>
    </div>
  );
}

function Grid({ map, renderUnit }: { map: TimelineMapSpec; renderUnit: RenderUnit }) {
  return (
    <div className="tl-grid">
      <div className="tl-mapcol">
        <div className="tl-map" data-views={pythonJson(map.views)}>
          <SpecDrawing element={map.drawing} />
        </div>
        <div className="tl-legend" aria-hidden="true">
          {map.legend.map((item) => (
            <span key={item.label} className="lg-item">
              <span className={item.swatch.join(" ")}></span>
              {item.label}
            </span>
          ))}
        </div>
        <p className="tl-cap">{renderUnit(map.caption)}</p>
      </div>
      <div className="tl-side">
        <div className="tl-card" data-card="">
          {map.cards.map((card, index) => (
            <div key={index} data-evc={index} hidden={index !== map.rest}>
              <EventCardBody card={card} renderUnit={renderUnit} />
            </div>
          ))}
        </div>
        <div className="tl-supply" data-supply-note="" hidden>
          <TextLines lines={map.supplyNote} renderUnit={renderUnit} />
        </div>
      </div>
    </div>
  );
}

export function TimelineMapView({ spec, renderUnit }: ComponentViewProps) {
  const map = parseShape(timelineMapShape, spec);
  return (
    <figure className="fig" aria-labelledby={labelledBy(map.head)}>
      <FigureHeadView head={map.head} renderUnit={renderUnit} />
      <div className="tl" data-comp={map.comp} id={map.id} data-rest={map.rest} data-events={pythonJson(map.events)}>
        <Controls map={map} renderUnit={renderUnit} />
        <Grid map={map} renderUnit={renderUnit} />
        <TimelineAxisView axis={map.axis} events={map.events} rest={map.rest} />
        <TimelineListView items={map.items} events={map.events} rest={map.rest} renderUnit={renderUnit} />
      </div>
    </figure>
  );
}
