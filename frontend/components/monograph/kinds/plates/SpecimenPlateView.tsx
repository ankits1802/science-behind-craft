import { specimenPlateShape } from "@/lib/componentSpecsPlates";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

import { SpecPicture } from "./SpecPicture";

export function SpecimenPlateView({ spec, renderUnit }: ComponentViewProps) {
  const specimen = parseShape(specimenPlateShape, spec);
  return (
    <div className="hero" data-phase={specimen.phase}>
      <SpecPicture className="hero-img" picture={specimen.picture} />
      <div className="hero-ox" aria-hidden="true"></div>
      <div className="hero-scrim" aria-hidden="true"></div>
      <div className="wrap hero-grid">
        <aside className="label-card on-photo hero-label" aria-labelledby={specimen.nameId}>
          <p className="lc-k">{renderUnit(specimen.kicker)}</p>
          <p className="lc-name" id={specimen.nameId}>
            {renderUnit(specimen.name)}
          </p>
          <p className="lc-s">{renderUnit(specimen.sentence)}</p>
          <div className="vat-row">
            <button className="text-link vat-again" type="button" aria-describedby={specimen.replay.statusId}>
              {specimen.replay.label}
            </button>
          </div>
          <p className="vh" id={specimen.replay.statusId} role="status">
            {renderUnit(specimen.replay.status)}
          </p>
          <p className="lc-credit">{renderUnit(specimen.credit)}</p>
        </aside>
      </div>
    </div>
  );
}
