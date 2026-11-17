import { createElement, type ComponentType, type ReactElement } from "react";

import { EXPERT_RENDERERS } from "@/components/answer/experts/expertRenderers";
import { ImageStrip } from "@/components/answer/ImageStrip";
import { MATTER_RENDERERS } from "@/components/answer/matter/matterRenderers";
import { PLACE_RENDERERS } from "@/components/answer/place/placeRenderers";
import { ProcessLadder } from "@/components/answer/ProcessLadder";
import { ProseBlockView } from "@/components/answer/ProseBlockView";
import type { BlockByKind, TypedBlockKind } from "@/lib/explainerContract";
import type { TypedBlock } from "@/lib/explainerView";

export type BlockRenderer<K extends TypedBlockKind> = ComponentType<{ block: BlockByKind[K] }>;

export const BLOCK_RENDERERS: { readonly [K in TypedBlockKind]?: BlockRenderer<K> } = {
  prose: ProseBlockView,
  process_ladder: ProcessLadder,
  images: ImageStrip,
  ...PLACE_RENDERERS,
  ...MATTER_RENDERERS,
  ...EXPERT_RENDERERS
};

export function hasRenderer(block: TypedBlock): boolean {
  return BLOCK_RENDERERS[block.kind] !== undefined;
}

export function renderBlock(block: TypedBlock): ReactElement | null {
  const renderer = BLOCK_RENDERERS[block.kind] as ComponentType<{ block: TypedBlock }> | undefined;
  return renderer ? createElement(renderer, { block }) : null;
}
