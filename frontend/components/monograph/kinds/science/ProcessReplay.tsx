import type { CSSProperties } from "react";

import type { ComponentViewProps } from "@/lib/componentViewContract";
import { processReplayShape, type ProcessReplaySpec } from "@/lib/componentSpecsScienceExplainers";
import { parseShape } from "@/lib/shape";

import { RichText } from "./parts/Drawing";
import { Tick } from "./parts/icons";
import type { RenderUnit } from "./parts/Text";

const order = (index: number) => ({ "--i": index }) as CSSProperties;

function Progress({ replay }: { replay: ProcessReplaySpec }) {
  return (
    <nav className="prog" aria-label="Progress">
      <ol>
        {replay.stages.map((stage) => (
          <li key={stage.label} className="is-done" data-kv-a={stage.startMs} data-kv-b={stage.endMs}>
            <span className="pg-ok" aria-hidden="true">
              <Tick />
            </span>
            <span className="pg-l">{stage.label}</span>
            <span className="pg-d">{stage.detail}</span>
            <span className="vh pg-state" />
          </li>
        ))}
      </ol>
      <p className="vh" role="status" data-kv-made-status="" />
    </nav>
  );
}

function Made({ replay, renderUnit }: { replay: ProcessReplaySpec; renderUnit: RenderUnit }) {
  return (
    <div className="kv-made-grid">
      <div className="kv-made-col">
        <p className="kicker">{renderUnit(replay.sourcesKicker)}</p>
        <ol className="kv-made-src" data-kv-made-src="">
          {replay.sources.map((source, index) => (
            <li key={index} className="kv-ms" style={order(index)}>
              <b>{index + 1}</b>
              <span className="kv-ms-t">{source.title}</span>
              <span className="relw">
                <span className={`rel ${source.grade}`} aria-hidden="true" />
                {source.grade}
              </span>
            </li>
          ))}
        </ol>
      </div>
      <div className="kv-made-col">
        <p className="kicker">{renderUnit(replay.sectionsKicker)}</p>
        <ol className="kv-made-sec" data-kv-made-sec="">
          {replay.sections.map((section, index) => (
            <li key={index} className="kv-mw" style={order(index)}>
              <b>{index + 1}</b>
              <span className="kv-mw-t">{section.title}</span>
              <span className="kv-mw-f">
                <span className="kv-ok">
                  <Tick />
                </span>
                <span>
                  <RichText runs={section.made} />
                </span>
              </span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

export function ProcessReplay({ spec, renderUnit }: ComponentViewProps) {
  const replay = parseShape(processReplayShape, spec);
  return (
    <div className="kv-made-how" data-kv-made="">
      <div className="kv-made-top">
        <button className="btn sm" type="button" data-kv-made-play="">
          {replay.play}
        </button>
      </div>
      <div className="understood kv-understood">
        <p>{renderUnit(replay.understood)}</p>
        <p className="u-a">{renderUnit(replay.angles)}</p>
      </div>
      <Progress replay={replay} />
      <Made replay={replay} renderUnit={renderUnit} />
      <p className="kv-made-ready" data-kv-made-ready="">
        {renderUnit(replay.ready)}
      </p>
    </div>
  );
}
