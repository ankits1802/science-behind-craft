import { blockingScripts, kilobytes, shortUrl, type Arrival, type Fetched, type FrameScript, type RawLoad } from "./phoneBudget";

export type PathRequest = { url: string; kind: string; priority: string; start: number; firstByte: number; end: number; bytes: number };
export type PaintPath = {
  largestAt: number;
  firstPaint: number;
  largest: string;
  navigation: Arrival;
  picture: PathRequest | null;
  requests: PathRequest[];
  blocking: PathRequest[];
  fonts: PathRequest[];
  sharing: PathRequest[];
  sharedCount: number;
  sharedBytes: number;
  tasksBefore: number;
  scriptsBefore: FrameScript[];
};

const UNKNOWN_PRIORITY = "unknown";
const SHARING_NAMED = 8;
const FONT = /\.(?:woff2?|ttf|otf)(?:$|\?)/i;

function timed(fetched: Fetched, priorities: Readonly<Record<string, string>>): PathRequest {
  const at = (value: number) => Math.round(value);
  return { url: shortUrl(fetched.url), kind: fetched.kind, priority: priorities[fetched.url] ?? UNKNOWN_PRIORITY, start: at(fetched.start), firstByte: at(fetched.firstByte), end: at(fetched.end), bytes: fetched.bytes };
}

function overlaps(request: Fetched, from: number, to: number): boolean {
  return request.start < to && request.end > from;
}

function heavier(left: PathRequest, right: PathRequest): number {
  return right.bytes - left.bytes;
}

export function paintPath(raw: RawLoad): PaintPath {
  const largest = raw.paints[raw.paints.length - 1];
  if (!largest) throw new Error("The page painted no largest element, so its critical path cannot be traced");
  const before = raw.fetched.filter((request) => request.start < largest.at);
  const own = largest.url ? (raw.fetched.find((request) => request.url === largest.url) ?? null) : null;
  const rivals = own ? raw.fetched.filter((request) => request !== own && overlaps(request, own.start, own.end)) : [];
  const shown = (requests: readonly Fetched[]) => requests.map((request) => timed(request, raw.priorities));
  return {
    largestAt: Math.round(largest.at),
    firstPaint: Math.round(raw.fcp),
    largest: largest.url ? `${largest.node} (${shortUrl(largest.url)})` : largest.node,
    navigation: { firstByte: Math.round(raw.navigation.firstByte), end: Math.round(raw.navigation.end) },
    picture: own ? timed(own, raw.priorities) : null,
    requests: shown([...before].sort((left, right) => left.start - right.start)),
    blocking: shown(before.filter((request) => request.blocking)),
    fonts: shown(before.filter((request) => FONT.test(request.url))),
    sharing: shown(rivals).sort(heavier).slice(0, SHARING_NAMED),
    sharedCount: rivals.length,
    sharedBytes: bytesOf(rivals),
    tasksBefore: Math.round(raw.tasks.filter((task) => task.at < largest.at).reduce((sum, task) => sum + Math.min(task.duration, largest.at - task.at), 0)),
    scriptsBefore: blockingScripts(raw.scripts.filter((script) => script.at < largest.at))
  };
}

function bytesOf(requests: readonly { bytes: number }[]): number {
  return requests.reduce((sum, request) => sum + request.bytes, 0);
}

function lastEnd(requests: readonly PathRequest[]): number {
  return requests.reduce((latest, request) => Math.max(latest, request.end), 0);
}

function pictureLine(picture: PathRequest | null): string {
  if (!picture) return "it waits on no request of its own";
  return `its picture ${picture.url} (${picture.priority}) requested at ${picture.start}, first byte at ${picture.firstByte}, done at ${picture.end}`;
}

export function pathLine(path: PaintPath): string {
  const parts = [
    `document first byte at ${path.navigation.firstByte}, done at ${path.navigation.end}`,
    `render-blocking requests ${path.blocking.length} (${kilobytes(bytesOf(path.blocking))}) done at ${lastEnd(path.blocking)}`,
    `fonts ${path.fonts.length} (${kilobytes(bytesOf(path.fonts))}) done at ${lastEnd(path.fonts)}`,
    `first paint at ${path.firstPaint}`,
    pictureLine(path.picture),
    `requests sharing the network with it ${path.sharedCount} (${kilobytes(path.sharedBytes)})`,
    `long tasks before it ${path.tasksBefore} ms (${path.scriptsBefore.map((script) => `${shortUrl(script.url)} ${script.duration} ms`).join(", ") || "none named"})`
  ];
  return `largest element ${path.largest} at ${path.largestAt} ms: ${parts.join("; ")}`;
}
