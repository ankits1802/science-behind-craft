"use client";

import { Suspense, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { MapPinned } from "lucide-react";

import { failureMessage, useRemote } from "@/components/hooks/useRemote";
import { DistrictPanel, useDistrict } from "@/components/map/DistrictPanel";
import type { MapPoint } from "@/components/map/layout";
import { LayerPicker } from "@/components/map/LayerPicker";
import { MapLayerView } from "@/components/map/MapLayerView";
import { PageHeader } from "@/components/PageHeader";
import { LoadingPanel, RetryPanel } from "@/components/RemotePanels";
import { fetchCraftMapPoints } from "@/lib/craftRegion";
import { DISTRICT_PARAM } from "@/lib/districtView";
import { chosenLayerId, fetchMapLayers, LAYER_PARAM } from "@/lib/mapLayers";
import { positiveParam } from "@/lib/searchParams";
import type { CraftMapPoint } from "@/lib/types";

function caption(point: CraftMapPoint): string | null {
  if (point.crafts.length === 0) return null;
  const names = point.crafts.slice(0, 3).map((craft) => craft.name);
  const more = point.crafts.length - names.length;
  return more > 0 ? `${names.join(", ")} and ${more} more` : names.join(", ");
}

function mapPoint(point: CraftMapPoint): MapPoint {
  return {
    key: point.key,
    name: point.name,
    latitude: point.latitude,
    longitude: point.longitude,
    total: point.total,
    caption: caption(point),
    href: point.crafts.length === 1 ? `/crafts/${encodeURIComponent(point.crafts[0].slug)}` : `/crafts?q=${encodeURIComponent(point.name)}`
  };
}

export default function MapPage() {
  return (
    <Suspense fallback={null}>
      <MapScreen />
    </Suspense>
  );
}

function MapScreen() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const places = useRemote(fetchCraftMapPoints);
  const layers = useRemote(fetchMapLayers);
  const layerId = chosenLayerId(layers.data, params.get(LAYER_PARAM));
  const districtLgd = positiveParam(params.get(DISTRICT_PARAM));
  const district = useDistrict(districtLgd);
  const points = places.data;

  const mapPoints = useMemo(
    () =>
      (points ?? [])
        .slice()
        .sort((a, b) => b.total - a.total || a.name.localeCompare(b.name))
        .map(mapPoint),
    [points]
  );
  const crafts = useMemo(() => new Set((points ?? []).flatMap((point) => point.crafts.map((craft) => craft.slug))).size, [points]);

  const choose = (param: string, value: string | null) => {
    const search = new URLSearchParams(params.toString());
    if (value) search.set(param, value);
    else search.delete(param);
    const query = search.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };
  const chooseLayer = (id: string | null) => choose(LAYER_PARAM, id);
  const pickDistrict = (lgd: number | null) => choose(DISTRICT_PARAM, lgd === null ? null : String(lgd));

  return (
    <>
      <PageHeader
        title="Map"
        description={points ? `${crafts} crafts across ${points.length} places` : undefined}
        icon={<MapPinned className="h-5 w-5" aria-hidden />}
        back={false}
      />
      {places.failure ? (
        <RetryPanel message={failureMessage(places.failure, "Couldn't load the map.")} onRetry={places.retry} />
      ) : points === null ? (
        <LoadingPanel />
      ) : (
        <section className="panel p-4 md:p-6">
          {layers.data && layers.data.layers.length > 0 ? <LayerPicker list={layers.data} value={layerId} onChange={chooseLayer} /> : null}
          <MapLayerView
            points={mapPoints}
            layerId={layerId}
            boundary={layers.data?.boundary ?? null}
            district={{
              lgd: districtLgd,
              name: district.data?.district.name ?? null,
              onPick: pickDistrict,
              panel: districtLgd !== null ? <DistrictPanel district={district} onClose={() => pickDistrict(null)} /> : null
            }}
          />
        </section>
      )}
    </>
  );
}
