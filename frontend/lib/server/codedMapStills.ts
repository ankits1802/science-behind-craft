import type { MapBox } from "@/components/map/basemap";
import { codedBase } from "@/components/map/codedStillCut";
import type { HeldWaters, StillLayers } from "@/components/map/mapStillCut";
import { drawingViewBox, parsedSpec } from "@/lib/componentSpecsGeneral";
import { CODED_FIGURE_KIND, codedFigureShape, drawsOnBase, type CodedMap } from "@/lib/componentSpecsScienceCoded";
import type { MonographDocument } from "@/lib/monographDocument";

export const CODED_BASE = "base";

type Spec = Record<string, unknown>;
export type CodedMapFigure = { label: string; spec: Spec; box: MapBox; map: CodedMap };

function withoutBase(spec: Spec): Spec {
  return Object.fromEntries(Object.entries(spec).filter(([key]) => key !== CODED_BASE));
}

function codedLabels(document: MonographDocument): string[] {
  return document.content.components.filter((component) => component.kind === CODED_FIGURE_KIND && Object.hasOwn(document.specs, component.label)).map((component) => component.label);
}

export function codedMaps(document: MonographDocument): CodedMapFigure[] {
  return codedLabels(document).flatMap((label) => {
    const spec = withoutBase(document.specs[label]);
    const figure = parsedSpec(codedFigureShape, spec);
    const box = figure?.map && figure.still && drawsOnBase(figure.still) ? drawingViewBox(figure.still) : null;
    return figure?.map && box ? [{ label, spec, box, map: figure.map }] : [];
  });
}

export function codedBasedDocument(document: MonographDocument, figures: readonly CodedMapFigure[], layers: StillLayers | null, held: HeldWaters): MonographDocument {
  const labels = codedLabels(document);
  if (!labels.length) return document;
  const specs = { ...document.specs };
  for (const label of labels) specs[label] = withoutBase(specs[label]);
  for (const figure of figures) {
    if (layers) specs[figure.label] = { ...figure.spec, [CODED_BASE]: codedBase(layers, figure.box, figure.map, held) };
  }
  return { ...document, specs };
}
