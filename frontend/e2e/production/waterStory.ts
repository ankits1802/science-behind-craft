import type { ExplainerBlock } from "@/lib/explainerContract";

export type RegionStoryRecord = { blocks: number; withRiver: number; steps: number; citedSteps: number };
export type CheckOutcome = { problems: string[]; notes: string[] };

export const NO_REGION_STORY: RegionStoryRecord = { blocks: 0, withRiver: 0, steps: 0, citedSteps: 0 };
export const RIVERS_NOT_LOADED_NOTE = "No region story arrived. The river lines are not loaded yet, so its absence is recorded and not failed.";

export function withRegionStory(record: RegionStoryRecord, block: ExplainerBlock): RegionStoryRecord {
  if (block.kind !== "region_story") return record;
  const traced = block.river !== null && block.river.reachIds.length > 0;
  return {
    blocks: record.blocks + 1,
    withRiver: record.withRiver + (traced ? 1 : 0),
    steps: record.steps + block.steps.length,
    citedSteps: record.citedSteps + block.steps.filter((step) => step.sentence.citations.length > 0).length
  };
}

export function waterStoryFound(story: RegionStoryRecord): boolean {
  return story.blocks > 0 && story.withRiver === story.blocks && story.steps > 0 && story.citedSteps === story.steps;
}

export function waterStoryOutcome(story: RegionStoryRecord, riversLoaded: boolean): CheckOutcome {
  if (story.blocks === 0) {
    return riversLoaded ? { problems: ["no region story arrived although the river lines are loaded"], notes: [] } : { problems: [], notes: [RIVERS_NOT_LOADED_NOTE] };
  }
  const problems: string[] = [];
  if (story.withRiver < story.blocks) problems.push(`${story.blocks - story.withRiver} region stories arrived without a river path`);
  if (story.steps === 0) problems.push("the region story arrived without a step");
  if (story.citedSteps < story.steps) problems.push(`${story.steps - story.citedSteps} region story steps arrived without a citation`);
  return { problems, notes: [] };
}
