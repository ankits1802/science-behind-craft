import { linkEnd, type ClipLink, type ClipLinkReader, type HeldClips } from "@/lib/codedClips";
import { filmsMessage, type FilmsMessage } from "@/lib/codedFigureFrame";
import { clipFilms, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";

export const RENEW_AHEAD_MS = 60_000;
export const RENEW_RETRY_MS = 15_000;

export type RenewalClock = { now: () => number; later: (run: () => void, ms: number) => unknown; cancel: (timer: unknown) => void };
export type RenewalDeps = { read: ClipLinkReader; post: (message: FilmsMessage) => void; clock: RenewalClock };
export type ClipRenewal = { ask: (key: string) => void; stop: () => void };

export function renewalDelay(link: ClipLink, now: number): number {
  return Math.max(0, linkEnd(link) - RENEW_AHEAD_MS - now);
}

export function clipRenewal(figure: Pick<CodedFigureSpec, "films">, held: HeldClips, deps: RenewalDeps): ClipRenewal {
  const clips = new Map(clipFilms(figure).filter((film) => Object.hasOwn(held, film.key)).map((film) => [film.key, film.clip] as const));
  const links = new Map(Object.entries(held));
  const timers = new Map<string, unknown>();
  const asking = new Set<string>();
  let stopped = false;

  const unplan = (key: string) => {
    if (timers.has(key)) deps.clock.cancel(timers.get(key));
    timers.delete(key);
  };
  const plan = (key: string, ms: number) => {
    unplan(key);
    timers.set(key, deps.clock.later(() => renew(key), ms));
  };
  const failed = (key: string) => {
    const link = links.get(key);
    if (link && linkEnd(link) > deps.clock.now()) plan(key, RENEW_RETRY_MS);
  };
  const renew = (key: string) => {
    const clip = clips.get(key);
    if (stopped || clip === undefined || asking.has(key)) return;
    unplan(key);
    asking.add(key);
    deps.read(clip).then(
      (link) => {
        asking.delete(key);
        if (stopped) return;
        links.set(key, link);
        deps.post(filmsMessage(key, link.url, linkEnd(link)));
        plan(key, renewalDelay(link, deps.clock.now()));
      },
      () => {
        asking.delete(key);
        if (!stopped) failed(key);
      }
    );
  };

  for (const [key, link] of links) if (clips.has(key)) plan(key, renewalDelay(link, deps.clock.now()));
  return {
    ask: renew,
    stop: () => {
      stopped = true;
      for (const timer of timers.values()) deps.clock.cancel(timer);
      timers.clear();
    }
  };
}
