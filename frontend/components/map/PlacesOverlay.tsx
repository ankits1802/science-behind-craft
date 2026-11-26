import type { MapBox } from "@/components/map/basemap";
import { LabelScale, MapLabelLayer, PeakMarks, PlacedLabels } from "@/components/map/MapLabelLayer";
import { PEAK_SIZE } from "@/components/map/physical/ReliefLayer";
import { peakLabels, rangeLabels, riverLabels, ringLabels, valueLabels } from "@/components/map/placesMapLabels";
import { PlacePins, type ValueMark } from "@/components/map/PlacesMapMarks";
import type { Physical } from "@/components/map/TimelineMapLayers";
import type { MapLayerSpec } from "@/lib/componentSpecsGeneral";
import type { ShownMarks } from "@/lib/componentSpecsMapLayer";

export type PlacesOverlayProps = {
  spec: MapLayerSpec;
  frame: MapBox;
  marks: ShownMarks;
  values: readonly ValueMark[];
  files: Pick<Physical, "relief" | "rivers">;
  named: readonly string[];
  nameOf: (ref: string) => string;
};

export function PlacesOverlay({ spec, frame, marks, values, files, named, nameOf }: PlacesOverlayProps) {
  return (
    <MapLabelLayer>
      <PlacedLabels frame={frame} labels={rangeLabels(files.relief, frame)} testId="relief-ranges" />
      <PlacedLabels frame={frame} labels={riverLabels(files.rivers, frame, named)} testId="rivers-labels" />
      <PeakMarks frame={frame} peaks={peakLabels(files.relief, frame, PEAK_SIZE)} size={PEAK_SIZE} />
      {marks.districts ? <PlacedLabels frame={frame} labels={valueLabels(values, frame)} testId="map-district-values" /> : null}
      <PlacedLabels frame={frame} labels={ringLabels(spec.rings ?? [], spec.places, marks, frame)} testId="map-ring-labels" />
      <LabelScale frame={frame} />
      <PlacePins places={spec.places} marks={marks} frame={frame} nameOf={nameOf} />
    </MapLabelLayer>
  );
}
