import type { PlateMaterial } from "@/components/editorial/TypographicPlate";

export const KICKER_SEPARATOR = " · ";

const FAMILY_MATERIALS: Readonly<Record<string, PlateMaterial>> = {
  Textiles: "textile",
  Metal: "metal",
  Stone: "stone",
  Wood: "wood",
  Leather: "leather",
  "Natural fibre and grass": "fibre",
  Clay: "clay",
  Paper: "paper",
  "More crafts": "misc"
};

const KIND_MATERIALS: Readonly<Record<string, PlateMaterial>> = {
  "Folk painting": "paint",
  "Musical instruments": "instr",
  "Figurines and toys": "toys"
};

export function plateMaterial(family: string | null, kind: string | null): PlateMaterial {
  if (kind && Object.hasOwn(KIND_MATERIALS, kind)) return KIND_MATERIALS[kind];
  if (family && Object.hasOwn(FAMILY_MATERIALS, family)) return FAMILY_MATERIALS[family];
  return "misc";
}

export function familyLine(family: string | null, kind: string | null): string | undefined {
  const parts = [family, kind].filter((part): part is string => Boolean(part && part.trim()));
  return parts.length ? parts.join(KICKER_SEPARATOR) : undefined;
}

export function familyParts(line: string): { family: string | null; kind: string | null } {
  const [family = null, kind = null] = line.split(KICKER_SEPARATOR).map((part) => part.trim()).filter(Boolean);
  return { family, kind };
}
