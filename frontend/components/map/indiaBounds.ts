export const INDIA_BOUNDS = {
  minLongitude: 68.2060,
  maxLongitude: 97.3940,
  minLatitude: 6.7560,
  maxLatitude: 37.0820
} as const;

export type GeoBounds = typeof INDIA_BOUNDS;
