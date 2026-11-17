import type { CraftLink } from "@/lib/answerShapes";
import type { ConceptCraft, ConceptNode } from "@/lib/explainerLearning";
import { listText } from "@/lib/format";

export const GRAPH_CRAFTS_MAX = 8;
export const LIST_CRAFTS_START = 6;

export type GraphPoint = { x: number; y: number };
export type GraphCraft = { entry: ConceptCraft; at: GraphPoint; focus: boolean };
export type ConceptGraphLayout = { crafts: GraphCraft[]; more: { count: number; at: GraphPoint } | null };

const CENTRE: GraphPoint = { x: 50, y: 50 };
const RADIUS_X = 34;
const RADIUS_Y = 36;

export function ringPoints(count: number): GraphPoint[] {
  return Array.from({ length: count }, (_, index) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / count;
    return { x: round(CENTRE.x + RADIUS_X * Math.cos(angle)), y: round(CENTRE.y + RADIUS_Y * Math.sin(angle)) };
  });
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}

export function graphLayout(node: ConceptNode, focus: CraftLink | null): ConceptGraphLayout {
  const overflow = node.crafts.length > GRAPH_CRAFTS_MAX;
  const drawn = overflow ? node.crafts.slice(0, GRAPH_CRAFTS_MAX - 1) : node.crafts;
  const points = ringPoints(drawn.length + (overflow ? 1 : 0));
  return {
    crafts: drawn.map((entry, index) => ({ entry, at: points[index], focus: entry.craft.slug === focus?.slug })),
    more: overflow ? { count: node.crafts.length - drawn.length, at: points[drawn.length] } : null
  };
}

export function graphSummary(node: ConceptNode): string {
  return `${node.label} is shared by ${listText(node.crafts.map((entry) => entry.craft.name))}`;
}

export function nodeChoiceLabel(node: ConceptNode): string {
  return `${node.label} · ${node.crafts.length}`;
}

export function shownCrafts(node: ConceptNode, all: boolean): ConceptCraft[] {
  return all ? node.crafts : node.crafts.slice(0, LIST_CRAFTS_START);
}

export function chosenNode(nodes: readonly ConceptNode[], termKey: string | null): ConceptNode {
  return nodes.find((node) => node.termKey === termKey) ?? nodes[0];
}
