import { safeOutboundUrl } from "@/lib/citations";
import type { BoundaryNote } from "@/lib/regionContract";

export const SURVEY_OF_INDIA_CAPTION = "External boundaries of India as depicted by Survey of India.";
export const DISTRICTS_INDICATIVE = "District boundaries are indicative.";
export const OSM_CREDIT = "© OpenStreetMap contributors";
export const OSM_COPYRIGHT_URL = "https://www.openstreetmap.org/copyright";
export const BOUNDARY_ATTRIBUTION = "Boundary data: DataMeet.";
export const MAP_CREDITS_LABEL = "Map credits";

const LINK = "underline-offset-3 hover:text-indigo-hover hover:underline";

export function MapAttribution({ districtsIndicative = true, boundary = null }: { districtsIndicative?: boolean; boundary?: BoundaryNote | null }) {
  const caption = boundary ? boundary.caption : `${SURVEY_OF_INDIA_CAPTION}${districtsIndicative ? ` ${DISTRICTS_INDICATIVE}` : ""}`;
  const shapes = boundary?.dataset ?? null;
  const shapesHref = shapes ? safeOutboundUrl(shapes.url) : null;
  return (
    <figcaption className="mt-3 grid gap-1 font-ui text-caption text-ink-3" data-testid="map-attribution">
      <span>
        {caption}{" "}
        <a href={OSM_COPYRIGHT_URL} target="_blank" rel="noopener noreferrer" className={LINK}>
          {OSM_CREDIT}
        </a>
      </span>
      <details className="w-fit max-w-full" data-testid="map-credits">
        <summary className={`w-fit cursor-pointer rounded-control font-medium text-ink-2 pointer-coarse:py-2 ${LINK}`}>{MAP_CREDITS_LABEL}</summary>
        <span className="mt-1 grid gap-0.5">
          <span>{BOUNDARY_ATTRIBUTION}</span>
          {shapes ? (
            <span>
              {shapesHref ? (
                <a href={shapesHref} target="_blank" rel="noopener noreferrer" className={LINK}>
                  {shapes.title}
                </a>
              ) : (
                shapes.title
              )}
              {shapes.publisher ? ` · ${shapes.publisher}` : null}
            </span>
          ) : null}
        </span>
      </details>
    </figcaption>
  );
}
