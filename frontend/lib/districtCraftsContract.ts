import { craftLinkShape, sourceRefShape, type CraftLink } from "@/lib/answerShapes";
import { explainerBlockShape, type ExplainerBlock } from "@/lib/explainerContract";
import { districtShape, type DistrictRef } from "@/lib/explainerPlace";
import { datasetShape, placeBasisShape, regionFacetShape, type PlaceBasis, type RegionDataset, type RegionFacet } from "@/lib/regionContract";
import { list, nullable, object, oneOf, text, type Shape } from "@/lib/shape";
import type { SourceRef } from "@/lib/types";

export const PLACE_ROLES = ["PRACTISED", "ORIGIN", "HISTORIC_CENTRE", "MATERIAL_SOURCE", "MARKET", "MIGRATED_FROM", "MIGRATED_TO"] as const;
export const DISTRICT_CRAFTS_PATH = (districtLgd: number) => `/map/districts/${districtLgd}`;

export type DistrictCraft = { craft: CraftLink; roles: (typeof PLACE_ROLES)[number][]; basis: PlaceBasis };
export type LandStory = { blocks: ExplainerBlock[]; facets: RegionFacet[] };
export type DistrictCrafts = {
  schemaVersion: 1;
  district: DistrictRef;
  crafts: DistrictCraft[];
  land: LandStory | null;
  sources: SourceRef[];
  datasets: RegionDataset[];
  boundaryCaption: string;
};

export const districtCraftsShape: Shape<DistrictCrafts> = object<DistrictCrafts>({
  schemaVersion: oneOf([1] as const),
  district: districtShape,
  crafts: list(object<DistrictCraft>({ craft: craftLinkShape, roles: list(oneOf(PLACE_ROLES), 1), basis: placeBasisShape })),
  land: nullable(object<LandStory>({ blocks: list(explainerBlockShape), facets: list(regionFacetShape) })),
  sources: list(sourceRefShape),
  datasets: list(datasetShape, 1),
  boundaryCaption: text
});
