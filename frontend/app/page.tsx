import { LandingHero } from "@/components/landing/LandingHero";
import { publicSummary } from "@/lib/server/publicSummary";

export default async function LandingPage() {
  const summary = await publicSummary();
  return <LandingHero craftCount={summary?.counts.crafts ?? null} />;
}
