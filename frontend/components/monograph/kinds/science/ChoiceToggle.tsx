"use client";

import { useContext } from "react";

import { KitSceneTextures } from "@/components/artkit/KitScene";
import { kitIds } from "@/components/artkit/kitIds";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { choiceToggleShape, type ChoiceOption } from "@/lib/componentSpecsScienceLab";
import { parseShape } from "@/lib/shape";

import { PanelPartView, stageDrawings } from "./ChoicePanelParts";
import { NoteDiffers } from "./parts/Differs";
import { OpenExperiment } from "./parts/LabContext";
import type { RenderUnit } from "./parts/Text";

function Result({ option, shown, renderUnit }: { option: ChoiceOption; shown: boolean; renderUnit: RenderUnit }) {
  return (
    <div data-res={option.value} hidden={!shown}>
      <h4>{renderUnit(option.heading)}</h4>
      {option.parts.map((part, index) =>
        part.part === "text" ? <p key={part.unit}>{renderUnit(part.unit)}</p> : <NoteDiffers key={index} differs={part.differs} renderUnit={renderUnit} />
      )}
    </div>
  );
}

export function ChoiceToggle({ component, spec, renderUnit }: ComponentViewProps) {
  const toggle = parseShape(choiceToggleShape, spec);
  const ids = kitIds(component.label);
  const open = useContext(OpenExperiment);
  const chosen = toggle.options[0].value;
  return (
    <div className="lab-panel" data-exp={toggle.experiment} hidden={open !== null && open !== toggle.experiment}>
      <div className="lab-txt">
        <p className="switch-q" id={toggle.questionId}>
          {renderUnit(toggle.question)}
        </p>
        <div className="seg" role="group" aria-labelledby={toggle.questionId} data-choice={toggle.experiment}>
          {toggle.options.map((option) => (
            <button key={option.value} type="button" data-v={option.value} aria-pressed={option.value === chosen}>
              {option.label}
            </button>
          ))}
        </div>
        <div className="lab-res">
          {toggle.options.map((option) => <Result key={option.value} option={option} shown={option.value === chosen} renderUnit={renderUnit} />)}
        </div>
        {toggle.textParts.map((part, index) => <PanelPartView key={index} part={part} chosen={chosen} name={`t${index}`} ids={ids} renderUnit={renderUnit} />)}
      </div>
      <div className="lab-vis">
        {toggle.visualParts.map((part, index) => <PanelPartView key={index} part={part} chosen={chosen} name={`v${index}`} ids={ids} renderUnit={renderUnit} />)}
      </div>
      <KitSceneTextures ids={ids} scenes={stageDrawings([...toggle.textParts, ...toggle.visualParts])} />
    </div>
  );
}
