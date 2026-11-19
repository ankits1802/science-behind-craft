import type { ComponentViews } from "@/lib/componentViewContract";

import { ChartView } from "./ChartView";
import { CitationToolView } from "./CitationToolView";
import { ConceptAtlasView } from "./ConceptAtlasView";
import { FactTableView } from "./FactTableView";
import { MapLayerView } from "./MapLayerView";
import { MapSequenceView } from "./MapSequenceView";
import { RelatedCraftsView } from "./RelatedCraftsView";
import { SourceDisagreementsView } from "./SourceDisagreementsView";
import { SourceListView } from "./SourceListView";
import { StatTilesView } from "./StatTilesView";
import { TimelineMapView } from "./TimelineMapView";
import { TimelineView } from "./TimelineView";

export const VIEWS: ComponentViews = {
  chart: ChartView,
  stat_tiles: StatTilesView,
  fact_table: FactTableView,
  map_layer: MapLayerView,
  map_sequence: MapSequenceView,
  timeline: TimelineView,
  timeline_map: TimelineMapView,
  concept_atlas: ConceptAtlasView,
  related_crafts: RelatedCraftsView,
  source_list: SourceListView,
  source_disagreements: SourceDisagreementsView,
  citation_tool: CitationToolView
};
