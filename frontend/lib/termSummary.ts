import { ApiError, apiFetch, buildQuery } from "@/lib/api";
import { termShape, type Term } from "@/lib/explainerContract";
import { parseShape } from "@/lib/shape";

export function termPath(key: string, language: string): string {
  return `/terms/${encodeURIComponent(key)}${buildQuery({ language })}`;
}

export async function fetchTerm(key: string, language: string): Promise<Term | null> {
  try {
    return parseShape(termShape, await apiFetch<unknown>(termPath(key, language)));
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
