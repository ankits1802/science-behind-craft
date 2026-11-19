import { apiFetch } from "@/lib/api";
import { object, oneOf, parseShape, type Shape } from "@/lib/shape";

export const REVIEW_SWITCH_PATH = "/knowledge/review-switch";

export const PROPOSAL_ORIGINS = ["research", "contribution", "agent"] as const;
export const SWITCH_MODES = ["AUTO", "APPROVAL"] as const;

export type ProposalOrigin = (typeof PROPOSAL_ORIGINS)[number];
export type SwitchMode = (typeof SWITCH_MODES)[number];
export type ReviewSwitch = Record<ProposalOrigin, SwitchMode>;
export type ReviewSwitchView = { current: ReviewSwitch; defaults: ReviewSwitch };

export const ORIGIN_COPY: Record<ProposalOrigin, { label: string; covers: string }> = {
  research: { label: "Our research", covers: "Facts found while answering readers' questions." },
  contribution: { label: "Contributors", covers: "Facts people propose on the site or through the Knowledge API." },
  agent: { label: "Outside agents", covers: "Facts proposed through the MCP server." }
};

export const MODE_LABELS: Record<SwitchMode, string> = {
  AUTO: "Publish, review after",
  APPROVAL: "Approve first"
};

const mode = oneOf(SWITCH_MODES);

export const reviewSwitchShape: Shape<ReviewSwitch> = object<ReviewSwitch>({ research: mode, contribution: mode, agent: mode });

export const reviewSwitchViewShape: Shape<ReviewSwitchView> = object<ReviewSwitchView>({
  current: reviewSwitchShape,
  defaults: reviewSwitchShape
});

export function isDefault(view: ReviewSwitchView): boolean {
  return PROPOSAL_ORIGINS.every((origin) => view.current[origin] === view.defaults[origin]);
}

export function defaultHint(view: ReviewSwitchView, origin: ProposalOrigin): string {
  return `Default: ${MODE_LABELS[view.defaults[origin]].toLowerCase()}`;
}

export async function fetchReviewSwitch(): Promise<ReviewSwitchView> {
  return parseShape(reviewSwitchViewShape, await apiFetch<unknown>(REVIEW_SWITCH_PATH));
}

export async function setReviewSwitch(change: Partial<ReviewSwitch>): Promise<ReviewSwitchView> {
  const body = await apiFetch<unknown>(REVIEW_SWITCH_PATH, { method: "PUT", body: JSON.stringify(change) });
  return parseShape(reviewSwitchViewShape, body);
}
