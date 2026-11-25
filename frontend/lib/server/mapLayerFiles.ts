import type { StillFiles } from "@/components/map/mapStillCut";
import type { MineralRow } from "@/lib/mapPhysical";
import shapes from "@/public/boundaries/district-shapes.json";
import minerals from "@/public/layers/minerals.json";
import relief from "@/public/layers/relief.json";
import rivers from "@/public/layers/rivers.json";

export const STILL_FILES: StillFiles = {
  relief,
  rivers,
  minerals: { classes: minerals.classes, statuses: minerals.statuses, sites: minerals.sites as MineralRow[] },
  shapes
};
