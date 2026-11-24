import { citationShape } from "@/lib/answerShapes";
import { envelope, type BlockEnvelope } from "@/lib/explainerBlockBase";
import { unitRef } from "@/lib/componentSpecsPlates";
import { kitDiagramShape, type KitDiagramSpec } from "@/lib/componentSpecsKit";
import { list, object, optional, ShapeError, text, type Shape } from "@/lib/shape";
import type { Citation } from "@/lib/types";

export const KIT_FIGURE_KIND = "kit_figure";

export type KitLabel = { ref: string; text: string; citations?: Citation[] };
export type KitFigureBlock = BlockEnvelope<"kit_figure"> & { diagram: KitDiagramSpec; labels: KitLabel[] };

const KIT_FIGURE_EXPECTED = "a composed figure naming each label its diagram draws, once";

const kitFigureFieldsShape: Shape<KitFigureBlock> = object<KitFigureBlock>({
  ...envelope(KIT_FIGURE_KIND),
  diagram: kitDiagramShape,
  labels: list(object<KitLabel>({ ref: unitRef, text, citations: optional(list(citationShape, 1)) }), 1)
});

export function diagramRefs(diagram: KitDiagramSpec): string[] {
  const refs = [diagram.head.title, diagram.head.caption, diagram.alt];
  for (const panel of diagram.panels) {
    refs.push(panel.label, panel.text, panel.via);
    for (const part of panel.parts) {
      refs.push(part.label);
      if (part.part === "section") refs.push(...part.layers.map((layer) => layer.label));
    }
  }
  return [...new Set(refs.filter((ref): ref is string => typeof ref === "string"))];
}

export const kitFigureBlockShape: Shape<KitFigureBlock> = {
  expected: KIT_FIGURE_EXPECTED,
  parse(value, path) {
    const block = kitFigureFieldsShape.parse(value, path);
    const named = block.labels.map((label) => label.ref);
    const drawn = diagramRefs(block.diagram);
    if (new Set(named).size !== named.length || named.length !== drawn.length || drawn.some((ref) => !named.includes(ref))) {
      throw new ShapeError(path, KIT_FIGURE_EXPECTED);
    }
    return block;
  }
};

export function kitLabelOf(block: Pick<KitFigureBlock, "labels">, ref: string): KitLabel | null {
  return block.labels.find((label) => label.ref === ref) ?? null;
}
