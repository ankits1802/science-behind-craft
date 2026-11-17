import type { AskDepths } from "@/lib/askConfig";
import { DEPTHS, type Depth } from "@/lib/explainerContract";

export function isDepth(value: unknown): value is Depth {
  return typeof value === "string" && (DEPTHS as readonly string[]).includes(value);
}

export function depthParam(value: string | null | undefined): Depth | null {
  return isDepth(value) ? value : null;
}

export function askedDepth(picked: Depth | null, offered: AskDepths): Depth | null {
  if (picked !== null && (offered.depths.length === 0 || offered.depths.some((option) => option.depth === picked))) return picked;
  return offered.defaultDepth;
}

export function depthLabel(depth: Depth | null | undefined, offered: AskDepths): string | null {
  return offered.depths.find((option) => option.depth === depth)?.label ?? null;
}
