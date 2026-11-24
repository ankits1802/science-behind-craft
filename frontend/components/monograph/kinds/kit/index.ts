import type { ComponentViews } from "@/lib/componentViewContract";
import { KIT_KIND } from "@/lib/componentSpecsKit";

import { KitDiagramView } from "./KitDiagramView";

export const DECLARED_KIT_VIEWS: ComponentViews = {
  [KIT_KIND]: KitDiagramView
};
