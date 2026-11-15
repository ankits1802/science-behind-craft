export const SURVEY_OF_INDIA_CAPTION = "External boundaries of India as depicted by Survey of India.";
export const DISTRICTS_INDICATIVE = "District boundaries are indicative.";
export const BOUNDARY_ATTRIBUTION = "Boundary data: DataMeet, © OpenStreetMap contributors.";

export function MapAttribution({ districtsIndicative = true }: { districtsIndicative?: boolean }) {
  return (
    <figcaption className="mt-3 grid gap-0.5 text-[11px] leading-4 text-ink-500" data-testid="map-attribution">
      <span>
        {SURVEY_OF_INDIA_CAPTION}
        {districtsIndicative ? ` ${DISTRICTS_INDICATIVE}` : ""}
      </span>
      <span>{BOUNDARY_ATTRIBUTION}</span>
    </figcaption>
  );
}
