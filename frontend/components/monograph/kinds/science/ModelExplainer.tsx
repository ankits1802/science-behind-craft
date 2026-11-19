import type { ComponentViewProps } from "@/lib/componentViewContract";
import { modelExplainerShape, type ExplainerStill, type ModelExplainerSpec } from "@/lib/componentSpecsScienceExplainers";
import { parseShape } from "@/lib/shape";

import { Drawing } from "./parts/Drawing";
import type { RenderUnit } from "./parts/Text";

function Controls({ explainer }: { explainer: ModelExplainerSpec }) {
  const controls = explainer.controls;
  return (
    <div className="kx-c">
      <button className="kx-b" type="button">
        <Drawing node={controls.playIcon} />
        <span>{controls.play}</span>
      </button>
      <div className="kx-s">
        <label className="vh">{controls.sliderLabel}</label>
        <input type="range" min="0" max={controls.sliderMax} step="1" defaultValue={controls.sliderAt} />
        <div className="kx-tk" aria-hidden="true">
          {controls.ticks.map((tick) => <span key={tick}>{tick}</span>)}
        </div>
      </div>
    </div>
  );
}

function Still({ explainer, still, renderUnit }: { explainer: ModelExplainerSpec; still: ExplainerStill; renderUnit: RenderUnit }) {
  return (
    <div className={`model-still ${still.width}`} aria-hidden="true" inert>
      <div className="kx">
        <div className="mb">
          <span className="mb-k">{explainer.badge}</span>
          <span className="mb-d">{explainer.badgeNote}</span>
        </div>
        <h2 className="kx-h">{renderUnit(still.heading)}</h2>
        <p className="kx-l">{renderUnit(still.lede)}</p>
        <div className="kx-st">
          <Drawing node={still.drawing} />
          <p className="kx-ph">{renderUnit(still.phase)}</p>
        </div>
        <Controls explainer={explainer} />
        <p className="kx-n">{renderUnit(still.numbers)}</p>
        <div className="kx-k" aria-label="Key">
          {explainer.key.map((item) => (
            <span key={item.label} className={item.style ?? undefined}>
              <Drawing node={item.icon} />
              {item.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ModelExplainer({ spec, renderUnit }: ComponentViewProps) {
  const explainer = parseShape(modelExplainerShape, spec);
  const { head, model } = explainer;
  return (
    <figure className="model-frame" aria-labelledby={head.titleId ?? undefined}>
      <figcaption className="mf-cap">
        <p className="fig-no" data-fig={head.figure ?? undefined}>
          {renderUnit(head.number)}
        </p>
        <p className="mf-t" id={head.titleId ?? undefined}>
          {renderUnit(head.title)}
        </p>
      </figcaption>
      <div className="model-box">
        <style>{model.stylesheet}</style>
        {explainer.stills.map((still) => <Still key={still.width} explainer={explainer} still={still} renderUnit={renderUnit} />)}
        <iframe className="kv-frame" title={model.title} sandbox={model.sandbox} data-srcdoc={model.document} style={{ height: `${model.height}px` }} />
      </div>
    </figure>
  );
}
