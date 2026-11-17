import type { ComponentType } from "react";

import { lazyBlock } from "@/components/answer/lazyBlock";
import { MapPlaceholder } from "@/components/answer/place/MapPlaceholder";
import { SeasonsStrip } from "@/components/answer/place/SeasonsStrip";
import { SupplyMapView } from "@/components/answer/place/SupplyMapView";
import type { MapLayerBlock, RegionStoryBlock, SeasonsBlock, SupplyMapBlock } from "@/lib/explainerPlace";

export const PLACE_RENDERERS: {
  region_story: ComponentType<{ block: RegionStoryBlock }>;
  map_layer: ComponentType<{ block: MapLayerBlock }>;
  seasons: ComponentType<{ block: SeasonsBlock }>;
  supply_map: ComponentType<{ block: SupplyMapBlock }>;
} = {
  region_story: lazyBlock(() => import("@/components/answer/place/RegionStory").then((module) => module.RegionStory), <MapPlaceholder />),
  map_layer: lazyBlock(() => import("@/components/answer/place/MapLayerBlockView").then((module) => module.MapLayerBlockView), <MapPlaceholder />),
  seasons: SeasonsStrip,
  supply_map: SupplyMapView
};
