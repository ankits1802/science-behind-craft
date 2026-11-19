import { curatedClaimId } from "@/components/landing/curatedClaim";
import { Landing } from "@/components/landing/Landing";
import { LANDING_CRAFT_SLUG, landingContent } from "@/components/landing/landingContent";
import { publicSummary } from "@/lib/server/publicSummary";
import { serverCraftPage } from "@/lib/server/readingPages";

export default async function LandingPage() {
  const [summary, page] = await Promise.all([publicSummary(), serverCraftPage(LANDING_CRAFT_SLUG)]);
  const content = landingContent(page, (key) => curatedClaimId(LANDING_CRAFT_SLUG, key));
  return <Landing craftCount={summary?.counts.crafts ?? null} content={content} />;
}
