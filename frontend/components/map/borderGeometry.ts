import { object, oneOf, parseShape, text, type Shape } from "@/lib/shape";

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
const VALUES = new Map<string, number>([...ALPHABET].map((character, index) => [character, index]));

const SCALE = 1000;

export type BorderLine = Array<[number, number]>;

export type BorderLevel = "state" | "district";
export type BordersFile = { schemaVersion: 1; lines: string };

export const BORDERS_ASSET: Record<BorderLevel, string> = {
  state: "/boundaries/state-borders.json",
  district: "/boundaries/district-borders.json"
};

export const bordersFileShape: Shape<BordersFile> = object<BordersFile>({ schemaVersion: oneOf([1]), lines: text });

export function decodeBorders(payload: string): BorderLine[] {
  const lines: BorderLine[] = [];
  let index = 0;
  let x = 0;
  let y = 0;

  const readInt = (): number => {
    let shift = 0;
    let result = 0;
    for (;;) {
      const value = VALUES.get(payload[index++]) ?? 0;
      result |= (value & 0x1f) << shift;
      shift += 5;
      if (value < 0x20) break;
    }
    return result & 1 ? ~(result >> 1) : result >> 1;
  };

  while (index < payload.length) {
    const count = readInt();
    if (count <= 0) break;
    const line: BorderLine = [];
    for (let n = 0; n < count; n += 1) {
      x += readInt();
      y += readInt();
      line.push([x / SCALE, y / SCALE]);
    }
    lines.push(line);
  }
  return lines;
}

const pending = new Map<BorderLevel, Promise<BorderLine[]>>();

export function loadBorders(level: BorderLevel): Promise<BorderLine[]> {
  const existing = pending.get(level);
  if (existing) return existing;
  const request = fetch(BORDERS_ASSET[level], { cache: "force-cache" })
    .then((response) => {
      if (!response.ok) throw new Error(`${BORDERS_ASSET[level]} returned ${response.status}`);
      return response.json();
    })
    .then((body: unknown) => decodeBorders(parseShape(bordersFileShape, body).lines))
    .catch((cause: unknown) => {
      pending.delete(level);
      throw cause;
    });
  pending.set(level, request);
  return request;
}
