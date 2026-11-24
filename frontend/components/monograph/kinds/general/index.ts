import { NearMapLayerView, NearTimelineMapView } from "@/components/monograph/kinds/nearViews";
import type { ComponentViews } from "@/lib/componentViewContract";

import { ChartView } from "./ChartView";
import { DrawingView } from "./DrawingView";
import { TableView } from "./TableView";
import { TimelineView } from "./TimelineView";

export const VIEWS: ComponentViews = {
  drawing: DrawingView
};

export const DECLARED_VIEWS: ComponentViews = {
  chart: ChartView,
  fact_table: TableView,
  timeline: TimelineView,
  map_layer: NearMapLayerView,
  timeline_map: NearTimelineMapView
};
