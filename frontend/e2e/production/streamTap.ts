import type { Page } from "@playwright/test";

import { ANSWER_STREAM_PATH } from "@/lib/answerStream";

export const TAP_KEY = "__kalavigyanAnswerTaps";

export type TappedChunk = { at: number; text: string };

export type TappedStream = {
  url: string;
  body: string | null;
  requestedAt: number;
  respondedAt: number | null;
  status: number | null;
  chunks: TappedChunk[];
  endedAt: number | null;
  failure: string | null;
};

export type TapGlance = { now: number; streams: number; endedAt: number | null; lastActivity: number | null };

type TapOptions = { path: string; key: string };

export function tapAnswerStreams(options: TapOptions): void {
  const taps: TappedStream[] = [];
  Object.defineProperty(window, options.key, { value: taps });
  const original = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const href = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!new URL(href, window.location.href).pathname.endsWith(options.path)) return original(input, init);
    const record: TappedStream = {
      url: href,
      body: typeof init?.body === "string" ? init.body : null,
      requestedAt: Date.now(),
      respondedAt: null,
      status: null,
      chunks: [],
      endedAt: null,
      failure: null
    };
    taps.push(record);
    let response: Response;
    try {
      response = await original(input, init);
    } catch (error) {
      record.failure = String(error);
      record.endedAt = Date.now();
      throw error;
    }
    record.respondedAt = Date.now();
    record.status = response.status;
    if (!response.body) {
      record.endedAt = Date.now();
      return response;
    }
    const [mine, theirs] = response.body.tee();
    const read = async () => {
      const reader = mine.getReader();
      const decoder = new TextDecoder();
      try {
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          record.chunks.push({ at: Date.now(), text: decoder.decode(value, { stream: true }) });
        }
        const rest = decoder.decode();
        if (rest) record.chunks.push({ at: Date.now(), text: rest });
      } catch (error) {
        record.failure = String(error);
      } finally {
        record.endedAt = Date.now();
      }
    };
    void read();
    return new Response(theirs, { status: response.status, statusText: response.statusText, headers: response.headers });
  };
}

export async function installStreamTap(page: Page): Promise<void> {
  await page.addInitScript(tapAnswerStreams, { path: ANSWER_STREAM_PATH, key: TAP_KEY });
}

export async function pageNow(page: Page): Promise<number> {
  return page.evaluate(() => Date.now());
}

export async function glanceAtTaps(page: Page, since: number): Promise<TapGlance> {
  return page.evaluate(
    ({ key, since: from }) => {
      const taps = ((window as unknown as Record<string, TappedStream[] | undefined>)[key] ?? []).filter((tap) => tap.requestedAt >= from);
      const newest = taps.at(-1);
      const lastChunk = newest?.chunks.at(-1)?.at ?? 0;
      return {
        now: Date.now(),
        streams: taps.length,
        endedAt: newest?.endedAt ?? null,
        lastActivity: newest ? Math.max(newest.requestedAt, newest.respondedAt ?? 0, lastChunk) : null
      };
    },
    { key: TAP_KEY, since }
  );
}

export async function readTaps(page: Page, since: number): Promise<TappedStream[]> {
  return page.evaluate(
    ({ key, since: from }) =>
      ((window as unknown as Record<string, TappedStream[] | undefined>)[key] ?? []).filter((tap) => tap.requestedAt >= from),
    { key: TAP_KEY, since }
  );
}
