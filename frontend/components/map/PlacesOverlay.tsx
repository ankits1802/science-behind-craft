import type { MapBox } from "@/components/map/basemap";
import { DamMarks, LabelScale, MapLabelLayer, PhysicalLabels, PlacedLabels, type LabelFiles } from "@/components/map/MapLabelLayer";
import { damLabels, ringLabels, valueLabels, waterLabels } from "@/components/map/placesMapLabels";
import { PlacePins, type ValueMark } from "@/components/map/PlacesMapMarks";
import type { StillWaters } from "@/components/map/waterLayer";
import type { MapLayerSpec } from "@/lib/componentSpecsGeneral";
import type { ShownMarks } from "@/lib/componentSpecsMapLayer";

export type PlacesOverlayProps = {
  spec: MapLayerSpec;
  frame: MapBox;
  marks: ShownMarks;
  values: readonly ValueMark[];
  files: LabelFiles;
  waters: StillWaters | null;
  named: readonly string[];
  nameOf: (ref: string) => string;
};

export function PlacesOverlay({ spec, frame, marks, values, files, waters, named, nameOf }: PlacesOverlayProps) {
  return (
    <MapLabelLayer>
      <PhysicalLabels files={files} frame={frame} named={named} />
      <PlacedLabels frame={frame} labels={waterLabels(waters, frame)} testId="map-water-labels" />
      <DamMarks frame={frame} dams={damLabels(waters, frame)} />
      {marks.districts ? <PlacedLabels frame={frame} labels={valueLabels(values, frame)} testId="map-district-values" /> : null}
      <PlacedLabels frame={frame} labels={ringLabels(spec.rings ?? [], spec.places, marks, frame)} testId="map-ring-labels" />
      <LabelScale frame={frame} />
      <PlacePins places={spec.places} marks={marks} frame={frame} nameOf={nameOf} />
    </MapLabelLayer>
  );
}
