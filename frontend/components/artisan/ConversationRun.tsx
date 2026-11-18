"use client";

import { useEffect, useRef, useState } from "react";

import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { apiErrorMessage } from "@/lib/api";
import { endConversation, streamConversationTurn, type ConversationTurnEvent, type RelayConversationStarted } from "@/lib/conversationContract";
import { fileName } from "@/lib/naming";
import { detectVoiceSupport, pickRecordingType, playSpeech, startRecording, type Recording } from "@/lib/voiceDevice";

type Line = { speaker: "KALAVIGYAN" | "ARTISAN"; text: string };
type Phase = "ready" | "recording" | "sending" | "ended";

export function ConversationRun({ started, onEnded }: { started: RelayConversationStarted; onEnded: () => void }) {
  const [lines, setLines] = useState<Line[]>([{ speaker: "KALAVIGYAN", text: started.opening.text }]);
  const [phase, setPhase] = useState<Phase>("ready");
  const [error, setError] = useState<string | null>(null);
  const recording = useRef<Recording | null>(null);
  const speech = useRef(new AbortController());
  const type = pickRecordingType(started.audioTypes, detectVoiceSupport().relayTypes);

  useEffect(() => {
    const playing = speech.current;
    playSpeech(started.opening.speechPath, playing.signal).catch(() => undefined);
    return () => playing.abort();
  }, [started.opening.speechPath]);

  function heard(event: ConversationTurnEvent) {
    if (event.type === "heard") setLines((now) => [...now, { speaker: "ARTISAN", text: event.data.text }]);
    if (event.type === "reply" || event.type === "closing") {
      setLines((now) => [...now, { speaker: "KALAVIGYAN", text: event.data.text }]);
      playSpeech(event.data.speechPath, speech.current.signal).catch(() => undefined);
    }
    if (event.type === "error") setError(event.data.message);
    if (event.type === "done" && event.data.sessionEnded) setPhase("ended");
  }

  async function send(continued: boolean) {
    const current = recording.current;
    recording.current = null;
    if (!current) return;
    setPhase("sending");
    try {
      const file = await current.stop();
      await streamConversationTurn(started.conversationId, file, continued, heard);
      if (continued) await record();
      else setPhase((now) => (now === "ended" ? now : "ready"));
    } catch (cause) {
      setError(apiErrorMessage(cause, "Couldn't hear that. Try again."));
      setPhase("ready");
    }
  }

  async function record() {
    if (!type) return;
    setError(null);
    const name = fileName({ entity: "Artisan-Conversation", what: "Recording", ext: type.includes("mp4") ? "m4a" : type.split("/")[1], date: new Date(), time: true, craft: started.craft.name });
    recording.current = await startRecording(type, name, {
      bitsPerSecond: started.audioBitsPerSecond,
      maxBytes: started.maxAudioBytes,
      onFull: () => void send(true)
    });
    setPhase("recording");
  }

  async function end() {
    recording.current?.cancel();
    speech.current.abort();
    try {
      await endConversation(started.conversationId);
    } finally {
      setPhase("ended");
      onEnded();
    }
  }

  return (
    <div className="grid gap-4" data-testid="conversation-run">
      <ol className="grid gap-2" aria-live="polite">
        {lines.map((line, index) => (
          <li key={index} lang={line.speaker === "ARTISAN" ? started.language : undefined} className={line.speaker === "ARTISAN" ? "text-sm text-ink-900" : "text-sm text-ink-700"}>
            <span className="font-semibold">{line.speaker === "ARTISAN" ? "You" : "KalaVigyan"}: </span>
            {line.text}
          </li>
        ))}
      </ol>
      {!type ? <p className="text-sm text-error-600">This browser can&apos;t record sound.</p> : null}
      {error ? (
        <p role="alert" className="text-sm text-error-600">
          {error}
        </p>
      ) : null}
      <ActionGroup>
        {phase === "recording" ? (
          <Button type="button" onClick={() => void send(false)}>
            Send
          </Button>
        ) : (
          <Button type="button" disabled={phase !== "ready" || !type} onClick={() => void record()}>
            {phase === "sending" ? "Listening…" : "Speak"}
          </Button>
        )}
        <Button type="button" variant="outline" disabled={phase === "ended"} onClick={() => void end()}>
          End
        </Button>
      </ActionGroup>
    </div>
  );
}
