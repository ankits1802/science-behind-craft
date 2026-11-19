import { Fragment } from "react";

import type { Differs } from "@/lib/componentSpecsScienceParts";

import type { RenderUnit } from "./Text";

export function PlayerDiffers({ differs, renderUnit }: { differs: Differs; renderUnit: RenderUnit }) {
  return (
    <details className="differs">
      <summary>
        <span>{differs.summary}</span>
      </summary>
      <div className="differs-body">
        {differs.body.map((unit) => <p key={unit}>{renderUnit(unit)}</p>)}
      </div>
    </details>
  );
}

export function NoteDiffers({ differs, renderUnit }: { differs: Differs; renderUnit: RenderUnit }) {
  return (
    <details className="differs">
      <summary className="differ">{differs.summary}</summary>
      <div className="differs-body">
        {differs.body.map((unit, index) => (
          <Fragment key={unit}>
            {index > 0 ? " " : null}
            {renderUnit(unit)}
          </Fragment>
        ))}
      </div>
    </details>
  );
}
