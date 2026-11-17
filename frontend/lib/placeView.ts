import { ApiError } from "@/lib/api";
import { BOUNDARY_DATASET_CODE, type BoundaryNote, type RegionDataset } from "@/lib/regionContract";

const GONE = 404;

export function datasetRow(datasets: readonly RegionDataset[], code: string): RegionDataset | null {
  return datasets.find((dataset) => dataset.code === code) ?? null;
}

export function boundaryNote(caption: string, datasets: readonly RegionDataset[]): BoundaryNote | null {
  const dataset = datasetRow(datasets, BOUNDARY_DATASET_CODE);
  return dataset ? { caption, dataset } : null;
}

export function isGone(failure: { cause: unknown } | null): boolean {
  return failure !== null && failure.cause instanceof ApiError && failure.cause.status === GONE;
}
