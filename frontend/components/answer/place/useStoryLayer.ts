"use client";

import { useCallback, useMemo, useState } from "react";

import { useRemote, type Remote } from "@/components/hooks/useRemote";
import { fetchMapLayer, fetchMapLayers } from "@/lib/mapLayers";
import type { MapLayer, MapLayerSummary } from "@/lib/regionContract";

export type StoryLayer = {
  offered: MapLayerSummary[];
  chosen: string | null;
  choose: (id: string | null) => void;
  layer: Remote<MapLayer>;
};

export function useStoryLayer(ids: readonly string[]): StoryLayer {
  const list = useRemote(ids.length > 0 ? fetchMapLayers : null);
  const offered = useMemo(() => {
    const layers = list.data?.layers ?? [];
    return ids.flatMap((id) => layers.filter((layer) => layer.id === id));
  }, [list.data, ids]);
  const [chosen, choose] = useState<string | null>(null);
  const load = useCallback(() => fetchMapLayer(chosen as string), [chosen]);
  const layer = useRemote(chosen ? load : null);
  return { offered, chosen, choose, layer };
}
