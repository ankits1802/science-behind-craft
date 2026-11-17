import type { ComponentType } from "react";

import { lazyBlock } from "@/components/answer/lazyBlock";
import { MapPlaceholder } from "@/components/answer/place/MapPlaceholder";
import type { TimelineMapBlock, ZoomStoryBlock } from "@/lib/explainerPlay";

export const JOURNEY_RENDERERS: {
  zoom_story: ComponentType<{ block: ZoomStoryBlock }>;
  timeline_map: ComponentType<{ block: TimelineMapBlock }>;
} = {
  zoom_story: lazyBlock(() => import("@/components/answer/journey/ZoomStory").then((module) => module.ZoomStory), <MapPlaceholder />),
  timeline_map: lazyBlock(() => import("@/components/answer/journey/TimelineMap").then((module) => module.TimelineMap), <MapPlaceholder />)
};
