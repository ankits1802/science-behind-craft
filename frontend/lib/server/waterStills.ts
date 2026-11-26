import type { MapBox } from "@/components/map/basemap";
import { NO_WATERS, type HeldWaters } from "@/components/map/mapStillCut";
import { heldTile, showsWaters, tilesInFrame, type HeldTile } from "@/components/map/waterLayer";
import { layerCredits } from "@/lib/mapPhysical";
import type { WatersTile } from "@/lib/mapWaters";

const HELD = new Map<string, Promise<HeldTile>>();

function heldWaterTile(id: string, load: () => Promise<WatersTile>): Promise<HeldTile> {
  const held = HELD.get(id) ?? load().then(heldTile);
  HELD.set(id, held);
  held.catch(() => HELD.delete(id));
  return held;
}

export async function heldWaters(frames: readonly MapBox[]): Promise<HeldWaters> {
  if (!frames.some(showsWaters)) return NO_WATERS;
  const files = await import("@/lib/server/watersFiles");
  const ids = [...new Set(frames.flatMap((frame) => tilesInFrame(files.WATERS_INDEX, frame)))];
  const tiles = await Promise.all(
    ids.flatMap((id) => {
      const load = files.WATERS_TILES[id];
      return load ? [heldWaterTile(id, load)] : [];
    })
  );
  return { tiles, credits: layerCredits(files.WATERS_INDEX.datasets) };
}
