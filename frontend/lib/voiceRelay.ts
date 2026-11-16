import { ApiError, apiErrorMessage } from "@/lib/api";
import { logUnexpected, type TransportHost, type VoiceTransport } from "@/lib/voiceCall";
import { reduceRelayEvent } from "@/lib/voiceConversation";
import type { RelaySessionStarted, VoiceTurnDone } from "@/lib/voiceContract";
import { pickRecordingType, recordingFileName, type Recording } from "@/lib/voiceDevice";
import { sessionGone, voiceFailure } from "@/lib/voiceRules";

type TurnResult = { done: VoiceTurnDone | null; speechPath: string | null };

const NO_ANSWER = "Couldn't get an answer. Try again.";

export class RelayTransport implements VoiceTransport {
  private recording: Recording | null = null;
  private turn: AbortController | null = null;
  private playback: AbortController | null = null;
  private cancelLimit: (() => void) | null = null;
  private stopped = false;
  private listenNext = false;

  constructor(private readonly host: TransportHost) {}

  private get session(): RelaySessionStarted {
    if (this.host.session.transport !== "RELAY") throw new TypeError("relay transport needs a relay session");
    return this.host.session;
  }

  begin(): void {
    void this.listen();
  }

  talk(): void {
    if (this.recording) void this.send();
    else if (this.playback) {
      this.listenNext = true;
      this.playback.abort();
    } else if (!this.turn) void this.listen();
  }

  level(): number {
    return this.recording?.level() ?? 0;
  }

  async stop(): Promise<void> {
    this.stopped = true;
    this.cancelLimit?.();
    this.recording?.cancel();
    this.recording = null;
    this.turn?.abort();
    this.playback?.abort();
  }

  private async listen(): Promise<void> {
    const type = pickRecordingType(this.session.audioTypes, this.host.deps.recordingTypes);
    if (!type) return this.host.fail("This browser can't record for voice.");
    let recording: Recording;
    try {
      const limits = { bitsPerSecond: this.session.audioBitsPerSecond, maxBytes: this.session.maxAudioBytes, onFull: () => void this.send() };
      recording = await this.host.deps.record(type, recordingFileName(type, new Date(this.host.deps.now()), this.host.craftName), limits);
    } catch (error) {
      return this.host.fail(voiceFailure(error, "Couldn't open the microphone."), error);
    }
    if (this.stopped || !this.host.isCurrent()) return recording.cancel();
    this.recording = recording;
    this.host.setActivity("recording");
    this.cancelLimit = this.host.deps.schedule(this.session.maxTurnSeconds * 1000, () => void this.send());
  }

  private async send(): Promise<void> {
    const recording = this.recording;
    if (!recording) return;
    this.recording = null;
    this.cancelLimit?.();
    this.host.setActivity("thinking");
    const file = await recording.stop();
    if (this.stopped) return;
    if (file.size === 0) return this.host.setActivity("ready");
    if (file.size > this.session.maxAudioBytes) {
      this.host.update((conversation) => ({ ...conversation, problem: "That was too long. Ask a shorter question." }));
      return this.host.setActivity("ready");
    }
    const result = await this.post(file);
    if (result && !this.stopped) await this.settle(result);
  }

  private async post(file: File): Promise<TurnResult | null> {
    const controller = new AbortController();
    this.turn = controller;
    const result: TurnResult = { done: null, speechPath: null };
    try {
      await this.host.deps.api.turn(
        this.session.voiceSessionId,
        file,
        (event) => {
          if (controller.signal.aborted) return;
          this.host.update((conversation) => reduceRelayEvent(conversation, event));
          if (event.type === "heard") this.host.heard(event.data.text);
          if (event.type === "spoken") result.speechPath = event.data.speechPath;
          if (event.type === "done") result.done = event.data;
        },
        controller.signal
      );
      return result;
    } catch (error) {
      if (controller.signal.aborted) return null;
      if (sessionGone(error)) {
        this.host.finish("remote");
        return null;
      }
      logUnexpected(error);
      const problem = error instanceof ApiError ? apiErrorMessage(error, NO_ANSWER) : NO_ANSWER;
      this.host.update((conversation) => ({ ...conversation, draft: null, status: null, problem }));
      this.host.setActivity("ready");
      return null;
    } finally {
      if (this.turn === controller) this.turn = null;
    }
  }

  private async settle({ done, speechPath }: TurnResult): Promise<void> {
    const turn = done ? this.host.turns().find((candidate) => candidate.turnId === done.turnId) : undefined;
    if (turn) await this.host.applyActions(turn.actions);
    if (speechPath) await this.speak(speechPath);
    if (this.stopped) return;
    const over = done?.sessionEnded === true || this.host.turns().length >= this.session.maxTurns;
    if (over) return this.host.finish("remote");
    if (!this.listenNext) return this.host.setActivity("ready");
    this.listenNext = false;
    await this.listen();
  }

  private async speak(path: string): Promise<void> {
    const controller = new AbortController();
    this.playback = controller;
    this.host.setActivity("speaking");
    try {
      await this.host.deps.play(path, controller.signal);
    } catch (error) {
      if (!controller.signal.aborted) logUnexpected(error);
    } finally {
      if (this.playback === controller) this.playback = null;
    }
  }
}
