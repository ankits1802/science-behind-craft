import { indiaOutlinePath, project, VIEW_BOX } from "@/components/map/projection";
import { shapePath, type DistrictShape } from "@/components/map/shapeGeometry";
import { cn } from "@/lib/utils";

export type LocatorFrame = { x: number; y: number; width: number; height: number };

export const LOCATOR_MARK_RADIUS = 26;
export const LOCATOR_INSET = "pointer-events-none absolute right-2 top-2 w-[22%] min-w-16 max-w-28 rounded-md bg-card/90 p-1 shadow-sm ring-1 ring-line-200";

export function locatorLabel(places: readonly { name: string; stateName: string }[]): string {
  const named = places.map((place) => `${place.name}, ${place.stateName}`);
  return named.length > 0 ? `Where in India: ${named.join("; ")}` : "Where in India";
}

export function IndiaLocator({ marked, frame, label, className }: { marked: readonly DistrictShape[]; frame: LocatorFrame | null; label: string; className?: string }) {
  return (
    <svg viewBox={`0 0 ${VIEW_BOX.width} ${VIEW_BOX.height}`} role="img" aria-label={label} className={cn("h-auto w-full", className)} data-testid="india-locator">
      <path d={indiaOutlinePath()} fillRule="evenodd" className="fill-surface-50 stroke-purple-300 dark:stroke-purple-700" strokeWidth={1.2} vectorEffect="non-scaling-stroke" />
      {marked.map((shape) => (
        <path key={shape.lgd} d={shapePath(shape)} fillRule="evenodd" data-lgd={shape.lgd} className="fill-purple-700 dark:fill-purple-300" />
      ))}
      {marked.map((shape) => {
        const { x, y } = project(shape.centroid[0], shape.centroid[1]);
        return <circle key={`mark-${shape.lgd}`} cx={x} cy={y} r={LOCATOR_MARK_RADIUS} className="fill-purple-700 stroke-card dark:fill-purple-300" strokeWidth={8} data-testid="india-locator-mark" />;
      })}
      {frame ? (
        <rect x={frame.x} y={frame.y} width={frame.width} height={frame.height} className="fill-none stroke-ink-900" strokeWidth={1.5} vectorEffect="non-scaling-stroke" data-testid="india-locator-frame" />
      ) : null}
    </svg>
  );
}
