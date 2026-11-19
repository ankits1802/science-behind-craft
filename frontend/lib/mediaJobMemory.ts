import { UUID_PATTERN } from "@/lib/answerShapes";
import { parseSlotKey, type MediaJobMemory } from "@/lib/craftMedia";

export const MEDIA_JOBS_STORAGE_PREFIX = "kalavigyan_media_jobs:";

export function rememberedJobs(raw: string | null): Record<string, string> {
  if (!raw) return {};
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return {};
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter((entry): entry is [string, string] => parseSlotKey(entry[0]) !== null && typeof entry[1] === "string" && UUID_PATTERN.test(entry[1]))
  );
}

export const sessionJobMemory: MediaJobMemory = {
  read(craftSlug) {
    try {
      return rememberedJobs(window.sessionStorage.getItem(MEDIA_JOBS_STORAGE_PREFIX + craftSlug));
    } catch {
      return {};
    }
  },
  write(craftSlug, jobs) {
    try {
      const key = MEDIA_JOBS_STORAGE_PREFIX + craftSlug;
      if (Object.keys(jobs).length === 0) window.sessionStorage.removeItem(key);
      else window.sessionStorage.setItem(key, JSON.stringify(jobs));
    } catch {
      return;
    }
  }
};
