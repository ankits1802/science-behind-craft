"use client";

import { useEffect, useMemo, useState } from "react";
import { MapPinned, RotateCw } from "lucide-react";

import { IndiaMapStage } from "@/components/map/IndiaMapStage";
import type { MapPoint } from "@/components/map/layout";
import { PageHeader } from "@/components/PageHeader";
import { fetchCraftMapPoints } from "@/lib/craftProfile";
import type { CraftMapPoint } from "@/lib/types";

function caption(point: CraftMapPoint): string | null {
  if (point.crafts.length === 0) return null;
  const names = point.crafts.slice(0, 3).map((craft) => craft.name);
  const more = point.crafts.length - names.length;
  return more > 0 ? `${names.join(", ")} and ${more} more` : names.join(", ");
}

export default function MapPage() {
  const [points, setPoints] = useState<CraftMapPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [round, setRound] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    fetchCraftMapPoints()
      .then((next) => {
        if (!cancelled) setPoints(next);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Couldn't load the map.");
      });
    return () => {
      cancelled = true;
    };
  }, [round]);

  const mapPoints: MapPoint[] = useMemo(
    () =>
      (points ?? [])
        .slice()
        .sort((a, b) => b.total - a.total || a.name.localeCompare(b.name))
        .map((point) => ({
          key: point.key,
          name: point.name,
          latitude: point.latitude,
          longitude: point.longitude,
          total: point.total,
          caption: caption(point),
          href: point.crafts.length === 1 ? `/crafts/${encodeURIComponent(point.crafts[0].slug)}` : `/crafts?q=${encodeURIComponent(point.name)}`
        })),
    [points]
  );

  const crafts = useMemo(() => new Set((points ?? []).flatMap((point) => point.crafts.map((craft) => craft.slug))).size, [points]);

  return (
    <>
      <PageHeader
        title="Map"
        description={points ? `${crafts} crafts across ${points.length} places` : undefined}
        icon={<MapPinned className="h-5 w-5" aria-hidden />}
        back={false}
      />
      {error ? (
        <section role="alert" className="panel grid justify-items-center gap-3 p-6 text-center">
          <p className="text-sm text-ink-700">{error}</p>
          <button type="button" className="field-button" onClick={() => setRound((value) => value + 1)}>
            <RotateCw className="h-4 w-4" aria-hidden />
            Try again
          </button>
        </section>
      ) : points === null ? (
        <section className="panel p-6 text-sm text-ink-500">Loading…</section>
      ) : (
        <section className="panel p-4 md:p-6">
          <IndiaMapStage points={mapPoints} listLabel="Places" />
        </section>
      )}
    </>
  );
}
