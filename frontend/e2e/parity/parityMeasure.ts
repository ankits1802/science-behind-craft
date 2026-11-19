import sharp from "sharp";

export type LineDiff = { approvedLines: number; renderedLines: number; onlyApproved: string[]; onlyRendered: string[] };
export type PixelDifference = { ratio: number; approved: [number, number]; rendered: [number, number] };

const CHANNEL_TOLERANCE = 24;

export function lineDiff(approved: string[], rendered: string[]): LineDiff {
  const counts = new Map<string, number>();
  for (const line of approved) counts.set(line, (counts.get(line) ?? 0) + 1);
  const onlyRendered: string[] = [];
  for (const line of rendered) {
    const left = counts.get(line) ?? 0;
    if (left > 0) counts.set(line, left - 1);
    else onlyRendered.push(line);
  }
  const onlyApproved = [...counts.entries()].flatMap(([line, left]) => Array.from({ length: left }, () => line));
  return { approvedLines: approved.length, renderedLines: rendered.length, onlyApproved, onlyRendered };
}

export function chapterIds(ids: string[]): string[] {
  return [...new Set(ids)].filter((id) => /^(ch-|chap|bx-|fig)/.test(id) || id.endsWith("-h"));
}

export async function pixelDifference(before: Buffer, after: Buffer): Promise<PixelDifference> {
  const [a, b] = await Promise.all([raw(before), raw(after)]);
  const width = Math.min(a.width, b.width);
  const height = Math.min(a.height, b.height);
  let differing = Math.abs(a.width * a.height - b.width * b.height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const i = (y * a.width + x) * 4;
      const j = (y * b.width + x) * 4;
      if ([0, 1, 2].some((c) => Math.abs(a.data[i + c] - b.data[j + c]) > CHANNEL_TOLERANCE)) differing += 1;
    }
  }
  return { ratio: differing / Math.max(a.width * a.height, b.width * b.height, 1), approved: [a.width, a.height], rendered: [b.width, b.height] };
}

async function raw(png: Buffer): Promise<{ data: Buffer; width: number; height: number }> {
  const { data, info } = await sharp(png).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, width: info.width, height: info.height };
}
