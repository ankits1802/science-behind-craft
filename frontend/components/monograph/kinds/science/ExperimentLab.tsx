"use client";

import type { ComponentViewProps } from "@/lib/componentViewContract";
import { experimentLabShape } from "@/lib/componentSpecsScienceLab";
import { parseShape } from "@/lib/shape";

import { OpenExperiment } from "./parts/LabContext";
import { Slot } from "./parts/Slot";

export function ExperimentLab({ spec, renderUnit }: ComponentViewProps) {
  const lab = parseShape(experimentLabShape, spec);
  const open = lab.experiments[0].key;
  return (
    <div className="wif" data-comp="lab" id={lab.id}>
      <div className="lab-head">
        <p className="fig-no" data-fig={lab.figure}>
          {renderUnit(lab.number)}
        </p>
        <div className="lab-pick">
          <div className="seg" role="group" aria-label={lab.pickerLabel} data-exps="">
            {lab.experiments.map((experiment) => (
              <button key={experiment.key} type="button" data-x={experiment.key} aria-pressed={experiment.key === open}>
                {experiment.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      <OpenExperiment.Provider value={open}>
        {lab.experiments.map((experiment) => <Slot key={experiment.key} slot={experiment.toggle} />)}
      </OpenExperiment.Provider>
    </div>
  );
}
