import type { StillFiles } from "@/components/map/mapStillCut";
import type { DatasetRow, MineralRow } from "@/lib/mapPhysical";
import shapes from "@/public/boundaries/district-shapes.json";
import neighbours from "@/public/boundaries/neighbours.json";
import minerals from "@/public/layers/minerals.json";
import relief from "@/public/layers/relief.json";
import rivers from "@/public/layers/rivers.json";

export const STILL_FILES: StillFiles = {
  relief: { bands: relief.bands, datasets: relief.datasets as DatasetRow[] },
  rivers: { ranks: rivers.ranks, lakes: rivers.lakes, datasets: rivers.datasets as DatasetRow[] },
  minerals: { classes: minerals.classes, statuses: minerals.statuses, sites: minerals.sites as MineralRow[] },
  shapes,
  neighbours
};
