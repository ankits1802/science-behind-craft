import { UUID_PATTERN } from "@/lib/answerShapes";
import {
  MEDIA_KINDS,
  offeredKinds,
  type MediaAsset,
  type MediaJob,
  type MediaJobRequest,
  type MediaKind,
  type MediaKindOffer,
  type MediaOptions,
  type MediaShareAction
} from "@/lib/mediaContract";
import { isUnexpected, mayRequest, mediaFailure, MEDIA_POLL_MISSES, MEDIA_WAIT_LIMIT_SECONDS, urlIsFresh } from "@/lib/mediaView";
import { ShapeError } from "@/lib/shape";

export type MediaSlot =
  | { phase: "creating"; request: MediaJobRequest }
  | { phase: "open"; job: MediaJob }
  | { phase: "ready"; job: MediaJob; asset: MediaAsset }
  | { phase: "ended"; job: MediaJob; message: string }
  | { phase: "refused"; message: string }
  | { phase: "lost"; request: MediaJobRequest | null; job: MediaJob | null; message: string }
  | { phase: "stalled"; job: MediaJob };

export type CraftMediaState = { options: MediaOptions | null; slots: Readonly<Partial<Record<string, MediaSlot>>> };

export type MediaApi = {
  options: (craftSlug: string) => Promise<MediaOptions>;
  create: (request: MediaJobRequest) => Promise<MediaJob>;
  job: (jobId: string) => Promise<MediaJob>;
  share: (asset: MediaAsset, kind: MediaKind, action: MediaShareAction) => Promise<MediaAsset>;
};

export type MediaJobMemory = {
  read: (craftSlug: string) => Record<string, string>;
  write: (craftSlug: string, jobs: Record<string, string>) => void;
};

export type CraftMediaDeps = {
  api: MediaApi;
  memory: MediaJobMemory;
  newKey: () => string;
  now: () => number;
  schedule: (ms: number, run: () => void) => () => void;
};

export const EMPTY_MEDIA: CraftMediaState = { options: null, slots: {} };

export function slotKey(stageId: string, kind: MediaKind): string {
  return `${stageId}:${kind}`;
}

export function parseSlotKey(key: string): { stageId: string; kind: MediaKind } | null {
  const [stageId, kind, ...rest] = key.split(":");
  if (rest.length || !UUID_PATTERN.test(stageId ?? "") || !MEDIA_KINDS.includes(kind as MediaKind)) return null;
  return { stageId, kind: kind as MediaKind };
}

export class CraftMedia {
  private state: CraftMediaState = EMPTY_MEDIA;
  private readonly listeners = new Set<() => void>();
  private readonly tokens = new Map<string, number>();
  private readonly timers = new Map<string, () => void>();
  private readonly since = new Map<string, number>();
  private readonly misses = new Map<string, number>();
  private generation = 0;
  private optionsRound = 0;
  private pendingTeardown: (() => void) | null = null;

  constructor(
    private readonly deps: CraftMediaDeps,
    readonly craftSlug: string
  ) {}

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getState = (): CraftMediaState => this.state;

  start(): void {
    if (this.pendingTeardown) {
      this.pendingTeardown();
      this.pendingTeardown = null;
      return;
    }
    this.generation += 1;
    void this.loadOptions();
    this.resume();
  }

  dispose(): void {
    this.pendingTeardown = this.deps.schedule(0, () => {
      this.pendingTeardown = null;
      this.teardown();
    });
  }

  request(stageId: string, kind: MediaKind): void {
    const key = slotKey(stageId, kind);
    if (!mayRequest(this.state.slots[key]) || !this.offers(stageId).some((offer) => offer.kind === kind)) return;
    void this.create(key, { kind, stageId, idempotencyKey: this.deps.newKey(), styleHint: null });
  }

  retry(stageId: string, kind: MediaKind): void {
    const key = slotKey(stageId, kind);
    const slot = this.state.slots[key];
    if (slot?.phase === "lost" && slot.request) void this.create(key, slot.request);
    else if (slot?.phase === "lost" && slot.job) this.watch(key, slot.job);
    else if (slot?.phase === "stalled") this.watch(key, slot.job);
  }

  async refresh(stageId: string, kind: MediaKind): Promise<MediaAsset> {
    const key = slotKey(stageId, kind);
    const slot = this.readySlot(key);
    const job = this.expect(await this.deps.api.job(slot.job.id), key, slot.job.id);
    if (!job.asset) throw new ShapeError(`job ${job.id}.asset`, "the asset of a job that succeeded");
    if (this.holdsJob(key, job.id)) this.put(key, { phase: "ready", job, asset: job.asset });
    return job.asset;
  }

  async freshAsset(stageId: string, kind: MediaKind): Promise<MediaAsset> {
    const slot = this.readySlot(slotKey(stageId, kind));
    return urlIsFresh(slot.asset, this.deps.now()) ? slot.asset : this.refresh(stageId, kind);
  }

  async share(stageId: string, kind: MediaKind, action: MediaShareAction): Promise<void> {
    const key = slotKey(stageId, kind);
    const slot = this.readySlot(key);
    const asset = await this.deps.api.share(slot.asset, kind, action);
    if (this.holdsJob(key, slot.job.id)) this.put(key, { phase: "ready", job: { ...slot.job, asset }, asset });
  }

  private offers(stageId: string): MediaKindOffer[] {
    return this.state.options ? offeredKinds(this.state.options, stageId) : [];
  }

  private async create(key: string, request: MediaJobRequest): Promise<void> {
    const token = this.claim(key);
    const generation = this.generation;
    this.put(key, { phase: "creating", request });
    let job: MediaJob;
    try {
      job = this.expect(await this.deps.api.create(request), key);
    } catch (error) {
      if (!this.holds(key, token, generation)) return;
      this.report(error);
      const failure = mediaFailure(error);
      this.put(key, failure.retry ? { phase: "lost", request, job: null, message: failure.message } : { phase: "refused", message: failure.message });
      if (!failure.retry) void this.loadOptions();
      return;
    }
    this.remember(key, job.id);
    if (!this.holds(key, token, generation)) return;
    this.restartClock(key);
    if (this.advance(key, token, job)) void this.loadOptions();
  }

  private watch(key: string, job: MediaJob): void {
    const token = this.claim(key);
    this.restartClock(key);
    this.put(key, { phase: "open", job });
    void this.poll(key, token, job);
  }

  private async poll(key: string, token: number, last: MediaJob): Promise<void> {
    const generation = this.generation;
    let job: MediaJob;
    try {
      job = this.expect(await this.deps.api.job(last.id), key, last.id);
    } catch (error) {
      if (!this.holds(key, token, generation)) return;
      this.report(error);
      this.missed(key, token, last, error);
      return;
    }
    if (!this.holds(key, token, generation)) return;
    this.misses.set(key, 0);
    if (this.advance(key, token, job)) void this.loadOptions();
  }

  private missed(key: string, token: number, last: MediaJob, error: unknown): void {
    const failure = mediaFailure(error);
    if (!failure.retry) {
      this.forget(key);
      this.put(key, { phase: "refused", message: failure.message });
      return;
    }
    const misses = (this.misses.get(key) ?? 0) + 1;
    this.misses.set(key, misses);
    if (misses < MEDIA_POLL_MISSES) this.schedulePoll(key, token, last);
    else this.put(key, { phase: "lost", request: null, job: last, message: failure.message });
  }

  private advance(key: string, token: number, job: MediaJob): boolean {
    if (job.asset) {
      this.put(key, { phase: "ready", job, asset: job.asset });
      return true;
    }
    if (job.failure) {
      this.forget(key);
      this.put(key, { phase: "ended", job, message: job.failure.message });
      return true;
    }
    this.put(key, { phase: "open", job });
    this.schedulePoll(key, token, job);
    return false;
  }

  private schedulePoll(key: string, token: number, job: MediaJob): void {
    const generation = this.generation;
    const waited = this.deps.now() - (this.since.get(key) ?? this.deps.now());
    if (waited >= MEDIA_WAIT_LIMIT_SECONDS * 1000) {
      this.put(key, { phase: "stalled", job });
      return;
    }
    const cancel = this.deps.schedule((job.pollAfterSeconds ?? 0) * 1000, () => {
      this.timers.delete(key);
      if (this.holds(key, token, generation)) void this.poll(key, token, job);
    });
    this.timers.set(key, cancel);
  }

  private resume(): void {
    const generation = this.generation;
    for (const [key, jobId] of Object.entries(this.deps.memory.read(this.craftSlug))) {
      if (!parseSlotKey(key) || this.state.slots[key]) continue;
      const token = this.claim(key);
      this.deps.api
        .job(jobId)
        .then((raw) => {
          const job = this.expect(raw, key, jobId);
          if (!this.holds(key, token, generation)) return;
          if (job.failure) return this.forget(key);
          this.restartClock(key);
          this.advance(key, token, job);
        })
        .catch((error: unknown) => {
          this.report(error);
          if (!mediaFailure(error).retry) this.forget(key);
        });
    }
  }

  private async loadOptions(): Promise<void> {
    const round = ++this.optionsRound;
    const generation = this.generation;
    let options: MediaOptions | null = null;
    try {
      options = await this.deps.api.options(this.craftSlug);
    } catch (error) {
      this.report(error);
    }
    if (round === this.optionsRound && generation === this.generation) this.set({ options });
  }

  private expect(job: MediaJob, key: string, jobId?: string): MediaJob {
    const slot = parseSlotKey(key);
    const matches = slot && job.craft.slug === this.craftSlug && job.stage.id === slot.stageId && job.kind === slot.kind;
    if (!matches || (jobId !== undefined && job.id !== jobId)) throw new ShapeError(`job ${job.id}`, `the job held for ${key}`);
    return job;
  }

  private readySlot(key: string): Extract<MediaSlot, { phase: "ready" }> {
    const slot = this.state.slots[key];
    if (slot?.phase !== "ready") throw new Error(`no illustration is ready for ${key}`);
    return slot;
  }

  private holdsJob(key: string, jobId: string): boolean {
    const slot = this.state.slots[key];
    return slot?.phase === "ready" && slot.job.id === jobId;
  }

  private claim(key: string): number {
    const token = (this.tokens.get(key) ?? 0) + 1;
    this.tokens.set(key, token);
    this.timers.get(key)?.();
    this.timers.delete(key);
    return token;
  }

  private holds(key: string, token: number, generation: number): boolean {
    return generation === this.generation && this.tokens.get(key) === token;
  }

  private restartClock(key: string): void {
    this.since.set(key, this.deps.now());
    this.misses.set(key, 0);
  }

  private remember(key: string, jobId: string): void {
    this.deps.memory.write(this.craftSlug, { ...this.deps.memory.read(this.craftSlug), [key]: jobId });
  }

  private forget(key: string): void {
    const { [key]: _gone, ...rest } = this.deps.memory.read(this.craftSlug);
    if (_gone !== undefined) this.deps.memory.write(this.craftSlug, rest);
  }

  private report(error: unknown): void {
    if (isUnexpected(error)) console.error(error);
  }

  private put(key: string, slot: MediaSlot): void {
    this.set({ slots: { ...this.state.slots, [key]: slot } });
  }

  private set(change: Partial<CraftMediaState>): void {
    this.state = { ...this.state, ...change };
    for (const listener of [...this.listeners]) listener();
  }

  private teardown(): void {
    this.generation += 1;
    for (const cancel of this.timers.values()) cancel();
    this.timers.clear();
  }
}
