import type { Fetched, RawLoad, Sent, Shift } from "./phoneBudget";

export const ORIGIN = "http://localhost:3000";
export const HERO = `${ORIGIN}/_next/image?url=%2Fhero.jpg&w=960&q=80`;

export const sent = (path: string, type: string, kib: number): Sent => ({ url: `${ORIGIN}${path}`, type, bytes: kib * 1024 });
export const shift = (at: number, value: number, input = false, nodes: string[] = [`div.at-${at}`]): Shift => ({ at, value, input, nodes });

export function fetched(path: string, kind: string, times: [number, number, number], kib: number, blocking = false): Fetched {
  const [start, firstByte, end] = times;
  return { url: path.startsWith("http") ? path : `${ORIGIN}${path}`, kind, start, firstByte, end, bytes: kib * 1024, blocking };
}

export function rawLoad(extra: Sent[] = []): RawLoad {
  return {
    fcp: 1200,
    paints: [
      { at: 1300, node: "h1.kv-q", url: "" },
      { at: 2900, node: "img", url: HERO }
    ],
    shifts: [shift(3000, 0.01)],
    tasks: [
      { at: 1000, duration: 400 },
      { at: 2000, duration: 120 }
    ],
    scripts: [
      { url: `${ORIGIN}/monographs/kit/monograph.js`, duration: 180, at: 3200 },
      { url: `${ORIGIN}/_next/static/chunks/a.js`, duration: 90, at: 1010 },
      { url: `${ORIGIN}/monographs/kit/monograph.js`, duration: 60, at: 4000 }
    ],
    firstScreen: [HERO],
    sent: [
      sent("/crafts/Kutch-Ajrakh", "Document", 40),
      sent("/_next/static/chunks/a.js", "Script", 200),
      sent("/monographs/kit/monograph.js", "Script", 44),
      sent("/monographs/kit/monograph.css", "Stylesheet", 70),
      sent("/_next/image?url=%2Fhero.jpg&w=960&q=80", "Image", 120),
      sent("/_next/image?url=%2Flater.jpg&w=500&q=80", "Image", 30),
      sent("/_next/static/media/newsreader.woff2", "Font", 25),
      ...extra
    ],
    fetched: [
      fetched("/monographs/kit/monograph.css", "link", [620, 1180, 1500], 70, true),
      fetched("/_next/static/media/newsreader.woff2", "link", [610, 1170, 1900], 25),
      fetched("/_next/static/chunks/a.js", "script", [640, 1200, 2400], 200),
      fetched(HERO, "img", [700, 1260, 2800], 120),
      fetched("/monographs/kit/monograph.js", "script", [3000, 3560, 3800], 44),
      fetched("/_next/image?url=%2Flater.jpg&w=500&q=80", "img", [2800, 3360, 3600], 30)
    ],
    navigation: { firstByte: 562.4, end: 790.6 },
    priorities: { [HERO]: "High", [`${ORIGIN}/_next/static/chunks/a.js`]: "Low", [`${ORIGIN}/monographs/kit/monograph.css`]: "VeryHigh" },
    reading: [shift(9000, 0.02, false, ["figure.mol"])]
  };
}
