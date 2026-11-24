import { COMPONENT_VIEWS } from "@/components/monograph/componentViews";
import { TimelineMapDeclaredView } from "@/components/monograph/kinds/general/TimelineMapDeclaredView";
import type { ComponentViews } from "@/lib/componentViewContract";

export const HEAVY_IMPORT_FIXTURE: ComponentViews = { ...COMPONENT_VIEWS, timeline_map: TimelineMapDeclaredView };
