import { ApiError } from "@/lib/api";
import type { AgentCall, AgentEvents } from "@/lib/elevenLabsAgent";
import { answerIdsOf, EMPTY_CONVERSATION, type VoiceConversation } from "@/lib/voiceConversation";
import type {
  ClientToolCall,
  VoiceNotice,
  VoiceSessionEnded,
  VoiceSessionRequest,
  VoiceSessionStarted,
  VoiceTranscript,
  VoiceTurn,
  VoiceTurnEvent
} from "@/lib/voiceContract";
import type { Recording, RecordingLimits } from "@/lib/voiceDevice";
import {
  EMPTY_LEDGER,
  isHeldToolCall,
  isMediaRefusal,
  prepayAction,
  toolCallOf,
  unappliedActions,
  voiceFailure,
  type ActionLedger,
  type HeldFacts
} from "@/lib/voiceRules";
import { VoiceConsentRequired } from "@/lib/voiceSession";

export type Activity = "connecting" | "ready" | "recording" | "thinking" | "speaking" | "listening";
export type VoicePhase = "idle" | "consent" | "starting" | "live" | "ending" | "ended" | "failed";
export type EndReason = "user" | "time" | "remote";

export type VoiceCallState = {
  phase: VoicePhase;
  activity: Activity | null;
  notice: VoiceNotice | null;
  busy: boolean;
  session: VoiceSessionStarted | null;
  startedAt: number | null;
  conversation: VoiceConversation;
  message: string | null;
  reveal: { answerId: string; nonce: number } | null;
};

export type VoiceApi = {
  notice: () => Promise<VoiceNotice>;
  accept: (version: string) => Promise<void>;
  start: (request: VoiceSessionRequest) => Promise<VoiceSessionStarted>;
  end: (voiceSessionId: string, keepalive: boolean) => Promise<VoiceSessionEnded>;
  transcript: (voiceSessionId: string) => Promise<VoiceTranscript>;
  turn: (voiceSessionId: string, recording: File, onEvent: (event: VoiceTurnEvent) => void, signal: AbortSignal) => Promise<void>;
};

export type VoiceCallDeps = {
  api: VoiceApi;
  connectAgent: (conversationToken: string, events: AgentEvents) => Promise<AgentCall>;
  record: (type: string, name: string, limits: RecordingLimits) => Promise<Recording>;
  play: (path: string, signal: AbortSignal) => Promise<void>;
  imageStages: (craftSlug: string) => Promise<ReadonlySet<string>>;
  recordingTypes: readonly string[];
  now: () => number;
  schedule: (ms: number, run: () => void) => () => void;
};

export type VoiceCallOptions = {
  request: () => VoiceSessionRequest;
  consentVersion: () => string | null;
  stageIds: () => ReadonlySet<string>;
  onAction: (call: ClientToolCall) => void;
  onHeard: (text: string) => void;
};

export type TransportHost = {
  readonly session: VoiceSessionStarted;
  readonly deps: VoiceCallDeps;
  readonly craftName: string | null;
  isCurrent: () => boolean;
  setActivity: (activity: Activity) => void;
  update: (change: (conversation: VoiceConversation) => VoiceConversation) => void;
  turns: () => readonly VoiceTurn[];
  heard: (text: string) => void;
  applyActions: (calls: readonly ClientToolCall[]) => Promise<void>;
  applyTranscriptActions: (turns: readonly VoiceTurn[]) => Promise<void>;
  toolCall: (raw: unknown) => Promise<boolean>;
  fail: (message: string, cause?: unknown) => void;
  finish: (reason: EndReason) => void;
};

export type VoiceTransport = {
  begin: () => void;
  talk: () => void;
  stop: () => Promise<void>;
  level: () => number;
};

export type TransportFactory = (host: TransportHost) => VoiceTransport;

const END_MESSAGE: Record<EndReason, string> = { user: "Call ended.", time: "Time's up for this call.", remote: "Call ended." };

export const IDLE_CALL: VoiceCallState = {
  phase: "idle",
  activity: null,
  notice: null,
  busy: false,
  session: null,
  startedAt: null,
  conversation: EMPTY_CONVERSATION,
  message: null,
  reveal: null
};

export function logUnexpected(error: unknown): void {
  if (!(error instanceof ApiError) && !isMediaRefusal(error)) console.error(error);
}

export class VoiceCall {
  private state: VoiceCallState = IDLE_CALL;
  private readonly listeners = new Set<() => void>();
  private generation = 0;
  private transport: VoiceTransport | null = null;
  private ledger: ActionLedger = EMPTY_LEDGER;
  private images: Promise<ReadonlySet<string>> | null = null;
  private cancelTimer: (() => void) | null = null;
  private pendingTeardown: (() => void) | null = null;
  private nonce = 0;
  private acceptedNotice: string | null = null;

  private configured: VoiceCallOptions | null = null;

  constructor(
    private readonly deps: VoiceCallDeps,
    private readonly transports: Record<VoiceSessionStarted["transport"], TransportFactory>
  ) {}

  configure(options: VoiceCallOptions): void {
    this.configured = options;
  }

  private get options(): VoiceCallOptions {
    if (!this.configured) throw new Error("VoiceCall used before configure()");
    return this.configured;
  }

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getState = (): VoiceCallState => this.state;

  level(): number {
    return this.transport?.level() ?? 0;
  }

  begin(): void {
    if (this.pendingTeardown) {
      this.pendingTeardown();
      this.pendingTeardown = null;
      if (this.state.phase !== "idle") return;
    }
    this.retry();
  }

  retry(): void {
    const version = this.options.consentVersion();
    if (version && version !== this.acceptedNotice) void this.askConsent();
    else void this.start();
  }

  talk(): void {
    if (this.state.phase === "live") this.transport?.talk();
  }

  async accept(): Promise<void> {
    const version = this.state.notice?.version;
    if (this.state.phase !== "consent" || !version || this.state.busy) return;
    const generation = this.generation;
    this.set({ busy: true, message: null });
    try {
      await this.deps.api.accept(version);
    } catch (error) {
      logUnexpected(error);
      if (generation === this.generation) this.set({ busy: false, message: voiceFailure(error, "Couldn't save that. Try again.") });
      return;
    }
    this.acceptedNotice = version;
    if (generation === this.generation) await this.start();
  }

  async end(reason: EndReason = "user"): Promise<void> {
    const session = this.state.session;
    if (this.state.phase !== "live" || !session) return;
    const generation = this.generation;
    this.set({ phase: "ending", activity: null });
    await this.shutdown();
    await this.close(session.voiceSessionId, false);
    if (generation === this.generation) this.set({ phase: "ended", message: END_MESSAGE[reason] });
  }

  abandon(): void {
    this.pendingTeardown?.();
    this.pendingTeardown = null;
    void this.teardown();
  }

  dispose(): void {
    this.pendingTeardown = this.deps.schedule(0, () => {
      this.pendingTeardown = null;
      void this.teardown();
    });
  }

  private set(change: Partial<VoiceCallState>): void {
    this.state = { ...this.state, ...change };
    for (const listener of [...this.listeners]) listener();
  }

  private async askConsent(): Promise<void> {
    const generation = ++this.generation;
    this.set({ ...IDLE_CALL, phase: "consent", busy: true });
    try {
      const notice = await this.deps.api.notice();
      if (generation === this.generation) this.set({ notice, busy: false });
    } catch (error) {
      logUnexpected(error);
      if (generation === this.generation) this.set({ phase: "failed", busy: false, message: voiceFailure(error, "Couldn't load the voice notice. Try again.") });
    }
  }

  private async start(): Promise<void> {
    const generation = ++this.generation;
    this.ledger = EMPTY_LEDGER;
    this.images = null;
    this.set({ ...IDLE_CALL, phase: "starting" });
    let session: VoiceSessionStarted;
    try {
      session = await this.deps.api.start(this.options.request());
    } catch (error) {
      if (generation !== this.generation) return;
      if (error instanceof VoiceConsentRequired) return void this.askConsent();
      logUnexpected(error);
      this.set({ phase: "failed", message: voiceFailure(error, "Couldn't start voice. Try again.") });
      return;
    }
    if (generation !== this.generation) return void this.close(session.voiceSessionId, true);
    this.set({ phase: "live", session, startedAt: this.deps.now(), activity: "connecting" });
    this.cancelTimer = this.deps.schedule(session.maxDurationSeconds * 1000, () => void this.end("time"));
    this.transport = this.transports[session.transport](this.host(session, generation));
    this.transport.begin();
  }

  private async shutdown(): Promise<void> {
    this.cancelTimer?.();
    this.cancelTimer = null;
    const transport = this.transport;
    this.transport = null;
    await transport?.stop();
  }

  private async close(voiceSessionId: string, keepalive: boolean): Promise<void> {
    try {
      await this.deps.api.end(voiceSessionId, keepalive);
    } catch (error) {
      logUnexpected(error);
    }
  }

  private async teardown(): Promise<void> {
    const session = this.state.session;
    const live = this.state.phase === "live" || this.state.phase === "starting";
    this.generation += 1;
    this.set(IDLE_CALL);
    await this.shutdown();
    if (live && session) await this.close(session.voiceSessionId, true);
  }

  private fail(generation: number, message: string, cause?: unknown): void {
    if (generation !== this.generation || this.state.phase !== "live") return;
    if (cause !== undefined) logUnexpected(cause);
    const session = this.state.session;
    this.set({ phase: "failed", activity: null, message });
    void this.shutdown().then(() => (session ? this.close(session.voiceSessionId, false) : undefined));
  }

  private facts(): HeldFacts {
    return {
      craftSlug: this.state.session?.craft?.slug ?? null,
      stageIds: this.options.stageIds(),
      answerIds: answerIdsOf(this.state.conversation.turns),
      imageStageIds: new Set()
    };
  }

  private async held(call: ClientToolCall): Promise<boolean> {
    const facts = this.facts();
    if (call.name === "offer_image" && facts.craftSlug && facts.stageIds.has(call.parameters.stageId)) {
      this.images ??= this.deps.imageStages(facts.craftSlug).catch((error: unknown) => {
        logUnexpected(error);
        return new Set<string>();
      });
      facts.imageStageIds = await this.images;
    }
    return isHeldToolCall(call, facts);
  }

  private async applicable(generation: number, call: ClientToolCall): Promise<boolean> {
    if (generation !== this.generation || this.state.phase !== "live") return false;
    return (await this.held(call)) && generation === this.generation && this.state.phase === "live";
  }

  private async applyHeld(generation: number, calls: readonly ClientToolCall[]): Promise<void> {
    for (const call of calls) if (await this.applicable(generation, call)) this.apply(call);
  }

  private apply(call: ClientToolCall): void {
    if (call.name === "show_sources") this.set({ reveal: { answerId: call.parameters.answerId, nonce: ++this.nonce } });
    this.options.onAction(call);
  }

  private host(session: VoiceSessionStarted, generation: number): TransportHost {
    const current = () => generation === this.generation;
    return {
      session,
      deps: this.deps,
      craftName: session.craft?.name ?? null,
      isCurrent: current,
      setActivity: (activity) => {
        if (current() && this.state.phase === "live") this.set({ activity });
      },
      update: (change) => {
        if (current()) this.set({ conversation: change(this.state.conversation) });
      },
      turns: () => this.state.conversation.turns,
      heard: (text) => this.options.onHeard(text),
      applyActions: (calls) => this.applyHeld(generation, calls),
      applyTranscriptActions: (turns) => {
        const { calls, ledger } = unappliedActions(turns, this.ledger);
        this.ledger = ledger;
        return this.applyHeld(generation, calls);
      },
      toolCall: async (raw) => {
        const call = toolCallOf(raw);
        if (!call || !(await this.applicable(generation, call))) return false;
        this.ledger = prepayAction(this.ledger, call);
        this.apply(call);
        return true;
      },
      fail: (message, cause) => this.fail(generation, message, cause),
      finish: (reason) => {
        if (current()) void this.end(reason);
      }
    };
  }
}
