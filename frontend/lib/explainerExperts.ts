import { envelope, explainerSentenceShape, type BlockEnvelope, type ExplainerSentence } from "@/lib/explainerBlockBase";
import { list, object, oneOf, type Shape } from "@/lib/shape";

export const EXPERT_SEATS = [
  "CHEMIST",
  "PHYSICIST",
  "MATERIALS_SCIENTIST",
  "TECHNOLOGIST",
  "GEOLOGIST",
  "HYDROLOGIST",
  "SOIL_SCIENTIST",
  "CLIMATOLOGIST",
  "ECOLOGIST",
  "BOTANIST",
  "TOXICOLOGIST",
  "HISTORIAN",
  "ANTHROPOLOGIST",
  "ECONOMIST",
  "DESIGN_HISTORIAN",
  "CONSERVATOR",
  "POLICY_EXPERT",
  "ARTISAN"
] as const;

export type ExpertSeat = (typeof EXPERT_SEATS)[number];

export const EXPERT_SEAT_LABELS: Record<ExpertSeat, string> = {
  CHEMIST: "Chemist",
  PHYSICIST: "Physicist",
  MATERIALS_SCIENTIST: "Materials scientist",
  TECHNOLOGIST: "Textile or ceramic technologist",
  GEOLOGIST: "Geologist",
  HYDROLOGIST: "Hydrologist",
  SOIL_SCIENTIST: "Soil scientist",
  CLIMATOLOGIST: "Climatologist",
  ECOLOGIST: "Ecologist",
  BOTANIST: "Botanist",
  TOXICOLOGIST: "Toxicologist",
  HISTORIAN: "Historian",
  ANTHROPOLOGIST: "Anthropologist",
  ECONOMIST: "Economist",
  DESIGN_HISTORIAN: "Design and art historian",
  CONSERVATOR: "Conservator",
  POLICY_EXPERT: "GI and policy expert",
  ARTISAN: "Artisan's voice"
};

export type ExpertDifference = { seat: ExpertSeat; thisView: ExplainerSentence; otherView: ExplainerSentence };
export type ExpertViewBlock = BlockEnvelope<"expert_view"> & {
  seat: ExpertSeat;
  take: ExplainerSentence[];
  agreesWith: ExpertSeat[];
  differs: ExpertDifference[];
};
export type ExpertsDiffer = { seats: [ExpertSeat, ExpertSeat]; views: [ExplainerSentence, ExplainerSentence] };

const seatShape = oneOf(EXPERT_SEATS);

export const expertViewBlockShape: Shape<ExpertViewBlock> = object<ExpertViewBlock>({
  ...envelope("expert_view"),
  seat: seatShape,
  take: list(explainerSentenceShape, 1),
  agreesWith: list(seatShape),
  differs: list(object<ExpertDifference>({ seat: seatShape, thisView: explainerSentenceShape, otherView: explainerSentenceShape }))
});

function claimsOf(sentence: ExplainerSentence): string {
  return [...new Set(sentence.citations.map((citation) => citation.claimId))].sort().join(" ");
}

function mirrored(one: ExpertDifference, other: ExpertDifference): boolean {
  return claimsOf(one.thisView) === claimsOf(other.otherView) && claimsOf(one.otherView) === claimsOf(other.thisView);
}

export function expertsDiffer(views: readonly ExpertViewBlock[]): ExpertsDiffer[] {
  const bySeat = new Map(views.map((view) => [view.seat, view]));
  const found: ExpertsDiffer[] = [];
  const paired = new Set<string>();
  for (const view of views) {
    for (const difference of view.differs) {
      const key = [view.seat, difference.seat].sort().join("+");
      const mirror = bySeat.get(difference.seat)?.differs.find((other) => other.seat === view.seat);
      if (paired.has(key) || !mirror || !mirrored(difference, mirror)) continue;
      paired.add(key);
      found.push({ seats: [view.seat, difference.seat], views: [difference.thisView, difference.otherView] });
    }
  }
  return found;
}
