import {
  componentSlotShape,
  differsShape,
  domId,
  figureKey,
  label,
  positive,
  richShape,
  svgNodeShape,
  textBlockShape,
  unitRef,
  type ComponentSlot,
  type Differs,
  type Rich,
  type SvgNode,
  type TextBlock
} from "@/lib/componentSpecsScienceParts";
import { stillOr, type KitScene } from "@/lib/componentSpecsKitScene";
import { list, matching, nullable, object, oneOf, ShapeError, tagged, type Shape } from "@/lib/shape";

const key = matching(/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/, "a key");

export type ResultPart = { part: "text"; unit: string } | { part: "differs"; differs: Differs };
export type ChoiceOption = { value: string; label: string; heading: string; parts: ResultPart[] };
export type FormulaChip = { formula: Rich; name: string; cid: number | null; source: string | null };
export type PanelLeaf =
  | { part: "text"; text: TextBlock }
  | { part: "formulas"; option: string | null; chips: FormulaChip[] }
  | { part: "same"; label: string; paragraphs: string[] }
  | { part: "chart"; title: string; chart: ComponentSlot; source: string }
  | { part: "stage"; drawing: SvgNode | KitScene; note: string | null; noteHook: string | null }
  | { part: "stepper"; hook: string; action: Rich; statusHook: string; status: string }
  | { part: "switch"; hook: string; label: Rich; description: string };
export type PanelPart = PanelLeaf | { part: "more"; parts: PanelLeaf[] };
export type ChoiceToggleSpec = {
  experiment: string;
  questionId: string;
  question: string;
  options: ChoiceOption[];
  textParts: PanelPart[];
  visualParts: PanelPart[];
};
export type ExperimentChoice = { key: string; label: string; toggle: ComponentSlot };
export type ExperimentLabSpec = { id: string; figure: string; number: string; pickerLabel: string; experiments: ExperimentChoice[] };

type Of<P extends PanelPart["part"]> = Extract<PanelPart, { part: P }>;

const chipShape: Shape<FormulaChip> = {
  expected: "a formula with its PubChem record or its source",
  parse(value, path) {
    const chip = object<FormulaChip>({ formula: richShape, name: label, cid: nullable(positive), source: nullable(label) }).parse(value, path);
    if ((chip.cid === null) === (chip.source === null)) throw new ShapeError(path, "a PubChem record or a source, one of them");
    return chip;
  }
};

const leaves: Record<PanelLeaf["part"], Shape<PanelLeaf>> = {
  text: object<Of<"text">>({ part: oneOf(["text"] as const), text: textBlockShape }),
  formulas: object<Of<"formulas">>({ part: oneOf(["formulas"] as const), option: nullable(key), chips: list(chipShape, 1) }),
  same: object<Of<"same">>({ part: oneOf(["same"] as const), label: unitRef, paragraphs: list(unitRef, 1) }),
  chart: object<Of<"chart">>({ part: oneOf(["chart"] as const), title: unitRef, chart: componentSlotShape, source: unitRef }),
  stage: object<Of<"stage">>({ part: oneOf(["stage"] as const), drawing: stillOr(svgNodeShape), note: nullable(unitRef), noteHook: nullable(key) }),
  stepper: object<Of<"stepper">>({ part: oneOf(["stepper"] as const), hook: key, action: richShape, statusHook: key, status: label }),
  switch: object<Of<"switch">>({ part: oneOf(["switch"] as const), hook: key, label: richShape, description: label })
};

const leafShape: Shape<PanelLeaf> = tagged<PanelLeaf>("part", leaves);
const panelPartShape: Shape<PanelPart> = tagged<PanelPart>("part", {
  ...leaves,
  more: object<Of<"more">>({ part: oneOf(["more"] as const), parts: list(leafShape, 1) })
});

const resultPartShape: Shape<ResultPart> = tagged<ResultPart>("part", {
  text: object<{ part: "text"; unit: string }>({ part: oneOf(["text"] as const), unit: unitRef }),
  differs: object<{ part: "differs"; differs: Differs }>({ part: oneOf(["differs"] as const), differs: differsShape })
});

export const choiceToggleShape: Shape<ChoiceToggleSpec> = object<ChoiceToggleSpec>({
  experiment: key,
  questionId: domId,
  question: unitRef,
  options: list(object<ChoiceOption>({ value: key, label, heading: unitRef, parts: list(resultPartShape, 1) }), 2),
  textParts: list(panelPartShape),
  visualParts: list(panelPartShape)
});

export const experimentLabShape: Shape<ExperimentLabSpec> = object<ExperimentLabSpec>({
  id: domId,
  figure: figureKey,
  number: unitRef,
  pickerLabel: label,
  experiments: list(object<ExperimentChoice>({ key, label, toggle: componentSlotShape }), 2)
});
