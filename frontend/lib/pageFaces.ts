export type FaceFile = { path: string; weight: string; style: "normal" | "italic" };
export type FaceFallback = { family: string; local: string; ascent: string; descent: string; lineGap: string; sizeAdjust: string };
export type PageFace = { family: string; range: string; src: readonly FaceFile[]; fallback: FaceFallback | null };

export const FACE_TYPE = "font/woff2";
export const FACES_HREF = "kv-first-screen-faces";
export const FACES_PRECEDENCE = "kv-faces";

function fileRule(face: PageFace, file: FaceFile): string {
  return `@font-face{font-family:"${face.family}";src:url("${file.path}") format("woff2");font-weight:${file.weight};font-style:${file.style};font-display:swap;unicode-range:${face.range}}`;
}

function fallbackRule(fallback: FaceFallback): string {
  return `@font-face{font-family:"${fallback.family}";src:local("${fallback.local}");ascent-override:${fallback.ascent};descent-override:${fallback.descent};line-gap-override:${fallback.lineGap};size-adjust:${fallback.sizeAdjust}}`;
}

export function faceRules(faces: readonly PageFace[]): string {
  return faces.flatMap((face) => [...face.src.map((file) => fileRule(face, file)), ...(face.fallback ? [fallbackRule(face.fallback)] : [])]).join("\n");
}

export function faceFiles(faces: readonly PageFace[]): string[] {
  return [...new Set(faces.flatMap((face) => face.src.map((file) => file.path)))];
}
