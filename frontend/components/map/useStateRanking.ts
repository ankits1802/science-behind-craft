"use client";

import { useMemo } from "react";

import { useRemote, type Remote } from "@/components/hooks/useRemote";
import { placedCircles, type PlacedCircle } from "@/components/map/StateCircles";
import { stateCounts, searchHref, type StateCounts } from "@/lib/atlasIndex";
import { useCraftCatalogue } from "@/lib/craftCatalogue";
import type { CraftCatalogue } from "@/lib/craftCatalogueContract";
import { fetchCraftMapPoints } from "@/lib/craftRegion";
import { stateMarks } from "@/lib/mapStates";
import type { CraftMapPoint } from "@/lib/types";
import type { RankedRow } from "@/components/map/RankedList";

export type StateRanking = {
  catalogue: CraftCatalogue | null;
  points: Remote<CraftMapPoint[]>;
  counts: StateCounts | null;
  circles: PlacedCircle[];
  rows: RankedRow[];
  catalogueError: string | null;
  reloadCatalogue: () => void;
};

export function rankedStateRows(counts: StateCounts): RankedRow[] {
  return counts.states.map((state) => ({ key: state.name, name: state.name, value: state.count, href: searchHref(state.name) }));
}

export function useStateRanking(): StateRanking {
  const { catalogue, error, reload } = useCraftCatalogue();
  const points = useRemote(fetchCraftMapPoints);
  const counts = useMemo(() => (catalogue ? stateCounts(catalogue) : null), [catalogue]);
  const circles = useMemo(() => (counts && points.data ? placedCircles(stateMarks(counts.states, points.data)) : []), [counts, points.data]);
  const rows = useMemo(() => (counts ? rankedStateRows(counts) : []), [counts]);
  return { catalogue, points, counts, circles, rows, catalogueError: error, reloadCatalogue: reload };
}
