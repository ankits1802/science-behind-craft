import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { ApiError } from "@/lib/api";
import { CraftMedia, slotKey, type CraftMediaDeps, type MediaApi, type MediaSlot } from "@/lib/craftMedia";
import { checkedMediaJob, checkedMediaOptions, mediaJobShape, mediaOptionsShape, type MediaAsset, type MediaJob, type MediaJobRequest } from "@/lib/mediaContract";
import { MEDIA_BROKEN, MEDIA_LOST } from "@/lib/mediaView";
import { parseShape } from "@/lib/shape";

const SHARED = join(__dirname, "..", "..", "shared");
const golden = (name: string): Record<string, unknown> => JSON.parse(readFileSync(join(SHARED, name), "utf8"));
const CRAFT = "Kutch-Ajrakh";
const PA = "575d3427-7a90-568d-87d5-bb0f1c602591";
const RANG = "eb895bd5-83a3-511a-9e64-ba7e452afea8";
const JOB_ID = "9af1da3c-f6c8-547b-b0e8-ca47cd798604";
const KEY = slotKey(PA, "IMAGE");
const START = Date.UTC(2026, 10, 16, 9, 0, 5);
const OPTIONS = checkedMediaOptions(parseShape(mediaOptionsShape, golden("media.options.golden.json")), CRAFT);

function jobAt(status: MediaJob["status"], change: Record<string, unknown> = {}): MediaJob {
  const base = golden("media.job.golden.json");
  const open = status === "QUEUED" || status === "RUNNING";
  const ended = status === "FAILED" || status === "BLOCKED";
  const body = {
    ...base,
    status,
    asset: status === "SUCCEEDED" ? base.asset : null,
    pollAfterSeconds: open ? 3 : null,
    attempts: status === "QUEUED" ? 0 : 1,
    refunded: ended,
    failure: ended ? { reason: status, message: "The model refused this stage." } : null,
    ...change
  };
  return checkedMediaJob(parseShape(mediaJobShape, body));
}

type Timer = { ms: number; run: () => void; live: boolean };
type Reply<T> = T | Error;

function harness(remembered: Record<string, string> = {}) {
  const timers: Timer[] = [];
  const created: MediaJobRequest[] = [];
  const polled: string[] = [];
  const createReplies: Reply<MediaJob>[] = [];
  const jobReplies: Reply<MediaJob>[] = [];
  const optionReplies: Reply<typeof OPTIONS>[] = [];
  const memory = new Map<string, Record<string, string>>([[CRAFT, { ...remembered }]]);
  let now = START;
  let keys = 0;
  let optionCalls = 0;
  const answer = <T,>(queue: Reply<T>[], fallback: () => Reply<T>): Promise<T> => {
    const reply = queue.length ? queue.shift()! : fallback();
    return reply instanceof Error ? Promise.reject(reply) : Promise.resolve(reply);
  };
  const api: MediaApi = {
    options: () => {
      optionCalls += 1;
      return answer(optionReplies, () => OPTIONS);
    },
    create: (request) => {
      created.push(request);
      return answer(createReplies, () => jobAt("QUEUED"));
    },
    job: (id) => {
      polled.push(id);
      return answer(jobReplies, () => jobAt("RUNNING"));
    },
    share: async (asset: MediaAsset, _kind, action) => ({
      ...asset,
      visibility: action === "SHARE" ? "CRAFT_SHARED" : "PRIVATE",
      sharing: { actions: [action === "SHARE" ? "UNSHARE" : "SHARE"], awaitingSecondProfessor: false }
    })
  };
  const deps: CraftMediaDeps = {
    api,
    memory: { read: (slug) => ({ ...(memory.get(slug) ?? {}) }), write: (slug, jobs) => void memory.set(slug, { ...jobs }) },
    newKey: () => `media:key-${String(++keys).padStart(12, "0")}`,
    now: () => now,
    schedule: (ms, run) => {
      const timer = { ms, run, live: true };
      timers.push(timer);
      return () => {
        timer.live = false;
      };
    }
  };
  const media = new CraftMedia(deps, CRAFT);
  return {
    media,
    created,
    polled,
    createReplies,
    jobReplies,
    optionReplies,
    timers,
    memory: () => memory.get(CRAFT) ?? {},
    optionCalls: () => optionCalls,
    slot: (key = KEY): MediaSlot | undefined => media.getState().slots[key],
    advance: (ms: number) => {
      now += ms;
    },
    live: () => timers.filter((timer) => timer.live),
    async tick() {
      const due = timers.filter((timer) => timer.live);
      for (const timer of due) {
        timer.live = false;
        timer.run();
      }
      await settle();
      return due.map((timer) => timer.ms);
    }
  };
}

async function settle() {
  for (let round = 0; round < 5; round += 1) await new Promise((resolve) => setTimeout(resolve, 0));
}

async function started(remembered?: Record<string, string>) {
  const run = harness(remembered);
  run.media.start();
  await settle();
  return run;
}

async function quietly<T>(work: () => Promise<T>): Promise<{ result: T; logged: unknown[] }> {
  const logged: unknown[] = [];
  const original = console.error;
  console.error = (error: unknown) => void logged.push(error);
  try {
    return { result: await work(), logged };
  } finally {
    console.error = original;
  }
}

test("an Image press makes one job with a fresh key, polls every 3 s and settles on the labelled asset", async () => {
  const run = await started();
  expect(run.optionCalls()).toBe(1);
  run.media.request(PA, "IMAGE");
  expect(run.slot()?.phase).toBe("creating");
  run.media.request(PA, "IMAGE");
  await settle();
  expect(run.created).toEqual([{ kind: "IMAGE", stageId: PA, idempotencyKey: "media:key-000000000001", styleHint: null }]);
  expect(run.slot()?.phase).toBe("open");
  expect(run.memory()).toEqual({ [KEY]: JOB_ID });
  run.jobReplies.push(jobAt("RUNNING"), jobAt("SUCCEEDED"));
  expect(await run.tick()).toEqual([3000]);
  expect(run.slot()).toMatchObject({ phase: "open", job: { status: "RUNNING" } });
  expect(await run.tick()).toEqual([3000]);
  const slot = run.slot();
  expect(slot?.phase === "ready" && slot.asset.label).toEqual({ text: "AI illustration", model: "gemini-3.1-flash-image", generatedOn: "2026-11-16" });
  expect(run.polled).toEqual([JOB_ID, JOB_ID]);
  expect(run.live()).toEqual([]);
  expect(run.optionCalls()).toBe(2);
});

test("a kind or stage the options do not list cannot be requested", async () => {
  const run = await started();
  run.media.request(PA, "VIDEO");
  run.media.request("5ced8309-b0f4-571a-8482-4223d1d4fccc", "IMAGE");
  await settle();
  expect(run.created).toEqual([]);
});

test("without options nothing is offered", async () => {
  const run = harness();
  run.optionReplies.push(new ApiError(404, "Not Found", { detail: "Not Found" }));
  run.media.start();
  await settle();
  expect(run.media.getState().options).toBeNull();
  run.media.request(PA, "IMAGE");
  expect(run.created).toEqual([]);
});

test("a refused press shows the server's sentence, and the next press uses a new key", async () => {
  const run = await started();
  run.createReplies.push(new ApiError(429, "No images left today.", { detail: "No images left today." }));
  run.media.request(PA, "IMAGE");
  await settle();
  expect(run.slot()).toEqual({ phase: "refused", message: "No images left today." });
  expect(run.optionCalls()).toBe(2);
  run.media.request(PA, "IMAGE");
  await settle();
  expect(run.created.map((request) => request.idempotencyKey)).toEqual(["media:key-000000000001", "media:key-000000000002"]);
});

test("a press that got no answer is sent again with the same key", async () => {
  const run = await started();
  run.createReplies.push(new TypeError("Failed to fetch"));
  run.media.request(PA, "IMAGE");
  await settle();
  expect(run.slot()).toMatchObject({ phase: "lost", message: MEDIA_LOST, job: null });
  run.media.request(PA, "IMAGE");
  run.media.retry(PA, "IMAGE");
  await settle();
  expect(run.created.map((request) => request.idempotencyKey)).toEqual(["media:key-000000000001", "media:key-000000000001"]);
  expect(run.slot()?.phase).toBe("open");
});

test("a failed or blocked job shows its reason and is forgotten", async () => {
  const run = await started();
  run.createReplies.push(jobAt("QUEUED"));
  run.jobReplies.push(jobAt("BLOCKED"));
  run.media.request(PA, "IMAGE");
  await settle();
  await run.tick();
  expect(run.slot()).toMatchObject({ phase: "ended", message: "The model refused this stage.", job: { refunded: true } });
  expect(run.memory()).toEqual({});
  run.media.request(PA, "IMAGE");
  await settle();
  expect(run.created).toHaveLength(2);
});

test("polling rides out two missed answers and stops at the third until asked", async () => {
  const run = await started();
  run.media.request(PA, "IMAGE");
  await settle();
  run.jobReplies.push(new TypeError("Failed to fetch"), new ApiError(502, "Bad Gateway", "Bad Gateway"), new TypeError("Failed to fetch"));
  expect(await run.tick()).toEqual([3000]);
  expect(await run.tick()).toEqual([3000]);
  expect(run.slot()?.phase).toBe("open");
  await run.tick();
  expect(run.slot()).toMatchObject({ phase: "lost", message: MEDIA_LOST, job: { id: JOB_ID } });
  expect(run.live()).toEqual([]);
  run.jobReplies.push(jobAt("SUCCEEDED"));
  run.media.retry(PA, "IMAGE");
  await settle();
  expect(run.slot()?.phase).toBe("ready");
  expect(run.created).toHaveLength(1);
});

test("a job the server no longer answers for is dropped with its sentence", async () => {
  const run = await started();
  run.media.request(PA, "IMAGE");
  await settle();
  run.jobReplies.push(new ApiError(404, "That job isn't yours.", { detail: "That job isn't yours." }));
  await run.tick();
  expect(run.slot()).toEqual({ phase: "refused", message: "That job isn't yours." });
  expect(run.memory()).toEqual({});
});

test("a job still open after 15 minutes stops polling until checked again", async () => {
  const run = await started();
  run.media.request(PA, "IMAGE");
  await settle();
  run.advance(899_000);
  await run.tick();
  expect(run.slot()?.phase).toBe("open");
  run.advance(1_000);
  await run.tick();
  expect(run.slot()?.phase).toBe("stalled");
  expect(run.live()).toEqual([]);
  run.jobReplies.push(jobAt("SUCCEEDED"));
  run.media.retry(PA, "IMAGE");
  await settle();
  expect(run.slot()?.phase).toBe("ready");
});

test("a job that answers for another stage is refused loudly", async () => {
  const { logged, result: run } = await quietly(async () => {
    const run = await started();
    run.media.request(RANG, "IMAGE");
    await settle();
    return run;
  });
  expect(run.slot(slotKey(RANG, "IMAGE"))).toEqual({ phase: "refused", message: MEDIA_BROKEN });
  expect(logged).toHaveLength(1);
});

test("a reader coming back sees the job they started, without a new one", async () => {
  const run = harness({ [KEY]: JOB_ID, [slotKey(RANG, "IMAGE")]: "0f0e0d0c-0b0a-4909-8807-060504030201" });
  run.jobReplies.push(jobAt("SUCCEEDED"), new ApiError(404, "Not Found", { detail: "Not Found" }));
  run.media.start();
  await settle();
  expect(run.slot()?.phase).toBe("ready");
  expect(run.slot(slotKey(RANG, "IMAGE"))).toBeUndefined();
  expect(run.memory()).toEqual({ [KEY]: JOB_ID });
  expect(run.created).toEqual([]);
  expect(run.optionCalls()).toBe(1);
});

test("an expiring link is renewed before a download, a fresh one is used as it is", async () => {
  const run = harness({ [KEY]: JOB_ID });
  run.jobReplies.push(jobAt("SUCCEEDED"));
  run.media.start();
  await settle();
  run.advance(60_000);
  expect((await run.media.freshAsset(PA, "IMAGE")).urlExpiresAt).toBe("2026-11-16T09:15:41Z");
  expect(run.polled).toHaveLength(1);
  run.advance(15 * 60_000);
  const renewed = jobAt("SUCCEEDED", { asset: { ...(golden("media.job.golden.json").asset as object), urlExpiresAt: "2026-11-16T09:31:41Z" } });
  run.jobReplies.push(renewed);
  expect((await run.media.freshAsset(PA, "IMAGE")).urlExpiresAt).toBe("2026-11-16T09:31:41Z");
  expect(run.polled).toHaveLength(2);
  const slot = run.slot();
  expect(slot?.phase === "ready" && slot.asset.urlExpiresAt).toBe("2026-11-16T09:31:41Z");
});

test("sharing replaces the asset with the server's answer", async () => {
  const run = harness({ [KEY]: JOB_ID });
  run.jobReplies.push(jobAt("SUCCEEDED"));
  run.media.start();
  await settle();
  await run.media.share(PA, "IMAGE", "SHARE");
  const slot = run.slot();
  expect(slot?.phase === "ready" && [slot.asset.visibility, slot.job.asset?.visibility]).toEqual(["CRAFT_SHARED", "CRAFT_SHARED"]);
});

test("a remount keeps the jobs; leaving stops the polling", async () => {
  const run = await started();
  run.media.request(PA, "IMAGE");
  await settle();
  const poll = run.live()[0];
  run.media.dispose();
  run.media.start();
  expect(poll.live).toBe(true);
  expect(run.optionCalls()).toBe(1);
  run.media.dispose();
  const teardown = run.live().find((timer) => timer.ms === 0)!;
  teardown.live = false;
  teardown.run();
  expect(poll.live).toBe(false);
  poll.run();
  await settle();
  expect(run.polled).toEqual([]);
});
