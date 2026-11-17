import type { DistrictCrafts } from "@/lib/districtCraftsContract";
import { byCount } from "@/lib/format";

export function districtTitle(district: DistrictCrafts["district"]): string {
  return `${district.name}, ${district.stateName}`;
}

export function craftsHeading(count: number): string {
  return `${byCount(count, "Craft", "Crafts")} practised here · ${count}`;
}

export const DISTRICT_PARAM = "district";
