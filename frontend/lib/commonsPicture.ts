export const COMMONS_WIDTHS = [330, 500, 960, 1280, 1920] as const;

export type CommonsWidth = (typeof COMMONS_WIDTHS)[number];

export type PictureRole = "hero" | "masthead" | "lead" | "plate" | "margin";

export type FocalBox = readonly [x: number, y: number, w: number, h: number];

export const PICTURE_WIDTHS: Record<PictureRole, readonly CommonsWidth[]> = {
  hero: [960, 1280, 1920],
  masthead: [500, 960, 1280, 1920],
  lead: [330, 500, 960],
  plate: [330, 500, 960],
  margin: [330, 500]
};

export const PICTURE_SIZES: Record<PictureRole, string> = {
  hero: "100vw",
  masthead: "(min-width: 1280px) 1280px, 100vw",
  lead: "(min-width: 1024px) 33vw, 72vw",
  plate: "(min-width: 1024px) 16vw, (min-width: 640px) 25vw, 72vw",
  margin: "240px"
};

const UPLOAD = /^https:\/\/upload\.wikimedia\.org\/wikipedia\/commons\/(?:thumb\/)?([0-9a-f])\/([0-9a-f]{2})\/([^/?#]+)/;

export function standardWidth(requested: number): CommonsWidth {
  return COMMONS_WIDTHS.find((width) => width >= requested) ?? COMMONS_WIDTHS[COMMONS_WIDTHS.length - 1];
}

export function isCommonsFile(url: string): boolean {
  return UPLOAD.test(url);
}

function thumbName(file: string, width: CommonsWidth): string {
  if (/\.svg$/i.test(file)) return `${width}px-${file}.png`;
  if (/\.tiff?$/i.test(file)) return `lossy-page1-${width}px-${file}.jpg`;
  if (/\.pdf$/i.test(file)) return `page1-${width}px-${file}.jpg`;
  return `${width}px-${file}`;
}

export function commonsThumb(fileUrl: string, width: number): string {
  const found = UPLOAD.exec(fileUrl);
  if (!found) throw new Error(`Not a Wikimedia Commons file: ${fileUrl}`);
  const [, first, pair, file] = found;
  return `https://upload.wikimedia.org/wikipedia/commons/thumb/${first}/${pair}/${file}/${thumbName(file, standardWidth(width))}`;
}

export function commonsSrcSet(fileUrl: string, widths: readonly CommonsWidth[], originalWidth?: number): string {
  const usable = originalWidth ? widths.filter((width) => width < originalWidth) : widths;
  return (usable.length > 0 ? usable : widths.slice(0, 1)).map((width) => `${commonsThumb(fileUrl, width)} ${width}w`).join(", ");
}

export function focalPosition(box: FocalBox): string {
  const [x, y, w, h] = box;
  const percent = (value: number) => `${Math.round(Math.min(1, Math.max(0, value)) * 1000) / 10}%`;
  return `${percent(x + w / 2)} ${percent(y + h / 2)}`;
}

export function focalViewBox(box: FocalBox): string {
  const [x, y, w, h] = box;
  const percent = (value: number) => `${Math.round(Math.min(1, Math.max(0, value)) * 1000) / 10}%`;
  return `inset(${percent(y)} ${percent(1 - x - w)} ${percent(1 - y - h)} ${percent(x)})`;
}
