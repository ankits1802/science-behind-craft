import { safeOutboundUrl } from "@/lib/citations";
import type { BoundaryNote } from "@/lib/regionContract";

export const SURVEY_OF_INDIA_CAPTION = "External boundaries of India as depicted by Survey of India.";
export const DISTRICTS_INDICATIVE = "District boundaries are indicative.";
export const BOUNDARY_ATTRIBUTION = "Boundary data: DataMeet, © OpenStreetMap contributors.";

export function MapAttribution({ districtsIndicative = true, boundary = null }: { districtsIndicative?: boolean; boundary?: BoundaryNote | null }) {
  const caption = boundary ? boundary.caption : `${SURVEY_OF_INDIA_CAPTION}${districtsIndicative ? ` ${DISTRICTS_INDICATIVE}` : ""}`;
  const shapesHref = boundary ? safeOutboundUrl(boundary.dataset.url) : null;
  return (
    <figcaption className="mt-3 grid gap-0.5 text-[11px] leading-4 text-ink-500" data-testid="map-attribution">
      <span>{caption}</span>
      <span>{BOUNDARY_ATTRIBUTION}</span>
      {boundary ? (
        <span>
          District shapes:{" "}
          {shapesHref ? (
            <a href={shapesHref} target="_blank" rel="noopener noreferrer" className="underline-offset-2 hover:text-purple-700 hover:underline">
              {boundary.dataset.publisher ?? boundary.dataset.title}
            </a>
          ) : (
            (boundary.dataset.publisher ?? boundary.dataset.title)
          )}
          {` · ${boundary.dataset.period}`}
        </span>
      ) : null}
    </figcaption>
  );
}
