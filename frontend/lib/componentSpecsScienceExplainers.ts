import {
  colourToken,
  componentSlotShape,
  domId,
  either,
  figureHeadShape,
  label,
  positive,
  richShape,
  styleName,
  svgNodeShape,
  unitRef,
  type ComponentSlot,
  type FigureHead,
  type Rich,
  type SvgNode
} from "@/lib/componentSpecsScienceParts";
import { integer, list, matching, nullable, object, oneOf, ShapeError, type Shape } from "@/lib/shape";

export const REPLAY_GRADES = ["A", "B", "C", "D"] as const;

export type MaterialCard = {
  swatch: string;
  role: string;
  name: string;
  local: string;
  botanical: string | null;
  chemistry: string;
  facts: string[];
};
export type MaterialCardsSpec = { id: string; headingId: string; heading: string; intro: string; cards: MaterialCard[]; after: ComponentSlot[] };
export type ExplainerStill = { width: "wide" | "narrow"; heading: string; lede: string; drawing: SvgNode; phase: string; numbers: string };
export type ExplainerControls = { play: string; playIcon: SvgNode; sliderLabel: string; sliderMax: number; sliderAt: number; ticks: string[] };
export type ExplainerKeyItem = { style: string | null; icon: SvgNode; label: string };
export type ModelDocument = { title: string; height: number; stylesheet: string; document: string; sandbox: "allow-scripts" };
export type ModelExplainerSpec = {
  head: FigureHead;
  badge: string;
  badgeNote: string;
  stills: ExplainerStill[];
  controls: ExplainerControls;
  key: ExplainerKeyItem[];
  model: ModelDocument;
};
export type ReplayStage = { label: string; detail: string; startMs: number; endMs: number };
export type ReplaySource = { title: string; grade: (typeof REPLAY_GRADES)[number] };
export type ReplaySection = { title: string; made: Rich };
export type ProcessReplaySpec = {
  play: string;
  understood: string;
  angles: string;
  stages: ReplayStage[];
  sourcesKicker: string;
  sources: ReplaySource[];
  sectionsKicker: string;
  sections: ReplaySection[];
  ready: string;
};

export const materialCardsShape: Shape<MaterialCardsSpec> = object<MaterialCardsSpec>({
  id: domId,
  headingId: domId,
  heading: label,
  intro: unitRef,
  cards: list(
    object<MaterialCard>({
      swatch: either(colourToken, oneOf(["crystal"] as const)),
      role: unitRef,
      name: unitRef,
      local: unitRef,
      botanical: nullable(unitRef),
      chemistry: unitRef,
      facts: list(unitRef, 1)
    }),
    1
  ),
  after: list(componentSlotShape)
});

const controlsShape: Shape<ExplainerControls> = {
  expected: "explainer controls resting within their range",
  parse(value, path) {
    const controls = object<ExplainerControls>({
      play: label,
      playIcon: svgNodeShape,
      sliderLabel: label,
      sliderMax: positive,
      sliderAt: integer,
      ticks: list(label, 2)
    }).parse(value, path);
    if (controls.sliderAt < 0 || controls.sliderAt > controls.sliderMax) throw new ShapeError(`${path}.sliderAt`, "a resting point within the slider");
    return controls;
  }
};

export const modelExplainerShape: Shape<ModelExplainerSpec> = object<ModelExplainerSpec>({
  head: figureHeadShape,
  badge: label,
  badgeNote: label,
  stills: list(
    object<ExplainerStill>({
      width: oneOf(["wide", "narrow"] as const),
      heading: unitRef,
      lede: unitRef,
      drawing: svgNodeShape,
      phase: unitRef,
      numbers: unitRef
    }),
    1
  ),
  controls: controlsShape,
  key: list(object<ExplainerKeyItem>({ style: nullable(styleName), icon: svgNodeShape, label }), 1),
  model: object<ModelDocument>({
    title: label,
    height: positive,
    stylesheet: matching(/^[^<]+$/, "a stylesheet with no markup"),
    document: label,
    sandbox: oneOf(["allow-scripts"] as const)
  })
});

export const processReplayShape: Shape<ProcessReplaySpec> = {
  expected: "a process replay whose stages end after they start",
  parse(value, path) {
    const replay = object<ProcessReplaySpec>({
      play: label,
      understood: unitRef,
      angles: unitRef,
      stages: list(object<ReplayStage>({ label, detail: label, startMs: integer, endMs: positive }), 1),
      sourcesKicker: unitRef,
      sources: list(object<ReplaySource>({ title: label, grade: oneOf(REPLAY_GRADES) }), 1),
      sectionsKicker: unitRef,
      sections: list(object<ReplaySection>({ title: label, made: richShape }), 1),
      ready: unitRef
    }).parse(value, path);
    const backwards = replay.stages.findIndex((stage) => stage.startMs < 0 || stage.endMs <= stage.startMs);
    if (backwards >= 0) throw new ShapeError(`${path}.stages[${backwards}]`, "a stage that ends after it starts");
    return replay;
  }
};
