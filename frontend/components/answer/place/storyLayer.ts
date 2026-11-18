import type { StoryGeometry } from "@/components/answer/place/storyGeometry";
import { choroplethTone } from "@/components/map/ChoroplethLegend";
import { NO_DATA_TONE, type DistrictFill } from "@/components/map/DistrictLayer";
import type { DistrictShape } from "@/components/map/shapeGeometry";
import { layerInView } from "@/lib/layerClasses";
import type { MapLayer } from "@/lib/regionContract";
import { layerFills } from "@/lib/regionView";

export function storyLayerInView(geometry: StoryGeometry, layer: MapLayer): MapLayer | null {
  return layerInView(
    layer,
    geometry.context.map((shape) => shape.lgd)
  );
}

export function shownLayerFill(shown: MapLayer): DistrictFill {
  const fills = layerFills(shown);
  return (shape: DistrictShape) => {
    const index = fills.get(shape.lgd);
    return index === undefined ? NO_DATA_TONE : choroplethTone(index, shown.classes.length);
  };
}

export function storyLayerFill(geometry: StoryGeometry, layer: MapLayer): DistrictFill {
  const shown = storyLayerInView(geometry, layer);
  return shown ? shownLayerFill(shown) : () => NO_DATA_TONE;
}
