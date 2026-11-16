import type { AgentCall, AgentEvents } from "@/lib/elevenLabsAgent";
import { logUnexpected, type TransportHost, type VoiceTransport } from "@/lib/voiceCall";
import { withTranscript } from "@/lib/voiceConversation";
import { voiceFailure } from "@/lib/voiceRules";

export class AgentTransport implements VoiceTransport {
  private call: AgentCall | null = null;
  private stopped = false;
  private reading: Promise<void> | null = null;
  private readAgain = false;

  constructor(private readonly host: TransportHost) {}

  begin(): void {
    void this.connect();
  }

  talk(): void {}

  level(): number {
    return this.call?.level() ?? 0;
  }

  async stop(): Promise<void> {
    this.stopped = true;
    const call = this.call;
    this.call = null;
    if (call) await call.end().catch(logUnexpected);
    await this.readTranscript();
  }

  private async connect(): Promise<void> {
    const session = this.host.session;
    if (session.transport !== "AGENT") throw new TypeError("agent transport needs an agent session");
    try {
      const call = await this.host.deps.connectAgent(session.conversationToken, this.events());
      if (this.stopped || !this.host.isCurrent()) {
        await call.end().catch(logUnexpected);
        return;
      }
      this.call = call;
    } catch (error) {
      this.host.fail(voiceFailure(error, "Couldn't connect. Try again."), error);
    }
  }

  private events(): AgentEvents {
    return {
      onConnected: () => this.host.setActivity("listening"),
      onSpeaking: (speaking) => this.host.setActivity(speaking ? "speaking" : "listening"),
      onUserSpeech: (text) => {
        this.host.update((conversation) => ({ ...conversation, heardLive: text }));
        this.host.heard(text);
        this.host.setActivity("thinking");
      },
      onAgentReply: () => void this.readTranscript(),
      onToolCall: (raw) => this.host.toolCall(raw),
      onEnd: (end) => {
        if (this.stopped) return;
        if (end.by === "error") this.host.fail("The call dropped.", end.message ? new Error(end.message) : undefined);
        else this.host.finish("remote");
      }
    };
  }

  private readTranscript(): Promise<void> {
    if (this.reading) {
      this.readAgain = true;
      return this.reading;
    }
    this.reading = this.readOnce().finally(() => {
      this.reading = null;
      if (this.readAgain) {
        this.readAgain = false;
        void this.readTranscript();
      }
    });
    return this.reading;
  }

  private async readOnce(): Promise<void> {
    try {
      const transcript = await this.host.deps.api.transcript(this.host.session.voiceSessionId);
      this.host.update((conversation) => withTranscript(conversation, transcript));
      await this.host.applyTranscriptActions(transcript.turns);
    } catch (error) {
      logUnexpected(error);
    }
  }
}
