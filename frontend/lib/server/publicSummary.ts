import { cache } from "react";

import { PUBLIC_SUMMARY_PATH, parsePublicSummary, type PublicSummary } from "@/lib/publicSummaryContract";
import { publicFetch } from "@/lib/server/serverFetch";

export const PUBLIC_SUMMARY_TAG = "public-summary";

export const publicSummary = cache(async (): Promise<PublicSummary | null> => {
  const result = await publicFetch(PUBLIC_SUMMARY_PATH, { parse: parsePublicSummary, tags: [PUBLIC_SUMMARY_TAG] });
  return result.ok ? result.body : null;
});
