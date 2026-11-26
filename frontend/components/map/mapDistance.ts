import type { MapBox } from "@/components/map/basemap";
import { project } from "@/components/map/projection";

export const KM_PER_DEGREE_LATITUDE = 110.574;
export const KM_PER_DEGREE_LONGITUDE = 111.32;
export const SCALE_SHARE = 0.22;
export const SCALE_STEPS = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000];

export type GroundPoint = { longitude: number; latitude: number };
export type ScaleBar = { km: number; length: number };
export type Radii = { rx: number; ry: number };

const radians = (degrees: number) => (degrees * Math.PI) / 180;

function longitudeDegrees(radiusKm: number, latitude: number): number {
  return radiusKm / (KM_PER_DEGREE_LONGITUDE * Math.cos(radians(latitude)));
}

export function ringCorners(centre: GroundPoint, radiusKm: number): GroundPoint[] {
  const across = longitudeDegrees(radiusKm, centre.latitude);
  const up = radiusKm / KM_PER_DEGREE_LATITUDE;
  return [
    { longitude: centre.longitude - across, latitude: centre.latitude },
    { longitude: centre.longitude + across, latitude: centre.latitude },
    { longitude: centre.longitude, latitude: centre.latitude - up },
    { longitude: centre.longitude, latitude: centre.latitude + up }
  ];
}

export function ringRadii(centre: GroundPoint, radiusKm: number): Radii {
  const at = project(centre.longitude, centre.latitude);
  const east = project(centre.longitude + longitudeDegrees(radiusKm, centre.latitude), centre.latitude);
  const north = project(centre.longitude, centre.latitude + radiusKm / KM_PER_DEGREE_LATITUDE);
  return { rx: east.x - at.x, ry: at.y - north.y };
}

function latitudeAt(y: number): number {
  const equator = project(0, 0).y;
  return (equator - y) / (equator - project(0, 1).y);
}

export function scaleBar(frame: MapBox): ScaleBar {
  const latitude = latitudeAt(frame.y + frame.height / 2);
  const unitsPerKm = (project(1, latitude).x - project(0, latitude).x) / (KM_PER_DEGREE_LONGITUDE * Math.cos(radians(latitude)));
  const wanted = (frame.width * SCALE_SHARE) / unitsPerKm;
  const km = [...SCALE_STEPS].reverse().find((step) => step <= wanted) ?? SCALE_STEPS[0];
  return { km, length: km * unitsPerKm };
}
