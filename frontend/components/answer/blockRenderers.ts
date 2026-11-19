import { createElement, type ComponentType, type ReactElement } from "react";

import { ComponentFigure } from "@/components/answer/ComponentFigure";
import { EXPERT_RENDERERS } from "@/components/answer/experts/expertRenderers";
import { ImageStrip } from "@/components/answer/ImageStrip";
import { INSIGHT_RENDERERS } from "@/components/answer/insight/insightRenderers";
import { JOURNEY_RENDERERS } from "@/components/answer/journey/journeyRenderers";
import { LEARNING_RENDERERS } from "@/components/answer/learning/learningRenderers";
import { MATTER_RENDERERS } from "@/components/answer/matter/matterRenderers";
import { PLACE_RENDERERS } from "@/components/answer/place/placeRenderers";
import { PLAY_RENDERERS } from "@/components/answer/play/playRenderers";
import { ProcessLadder } from "@/components/answer/ProcessLadder";
import { ProseBlockView } from "@/components/answer/ProseBlockView";
import type { BlockByKind, TypedBlockKind } from "@/lib/explainerContract";
import type { TypedBlock } from "@/lib/explainerView";

export type BlockRenderer<K extends TypedBlockKind> = ComponentType<{ block: BlockByKind[K] }>;

export const BLOCK_RENDERERS: { readonly [K in TypedBlockKind]?: BlockRenderer<K> } = {
  prose: ProseBlockView,
  process_ladder: ProcessLadder,
  images: ImageStrip,
  component: ComponentFigure,
  ...PLACE_RENDERERS,
  ...MATTER_RENDERERS,
  ...EXPERT_RENDERERS,
  ...PLAY_RENDERERS,
  ...JOURNEY_RENDERERS,
  ...LEARNING_RENDERERS,
  ...INSIGHT_RENDERERS
};

export function hasRenderer(block: TypedBlock): boolean {
  return BLOCK_RENDERERS[block.kind] !== undefined;
}

export function renderBlock(block: TypedBlock): ReactElement | null {
  const renderer = BLOCK_RENDERERS[block.kind] as ComponentType<{ block: TypedBlock }> | undefined;
  return renderer ? createElement(renderer, { block }) : null;
}
