import { NearWhyHereView } from "@/components/monograph/kinds/nearViews";
import type { ComponentViews } from "@/lib/componentViewContract";
import { WHY_HERE_KIND } from "@/lib/placeGround";

export const VIEWS: ComponentViews = {
  [WHY_HERE_KIND]: NearWhyHereView
};
