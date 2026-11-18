import Link from "next/link";

import type { FieldTranscript, TranscriptLine, TranscriptSpeaker } from "@/lib/fieldVoicesContract";

const MACHINE_LABEL = "Machine translation";
const UNKNOWN_SPEAKER = "Speaker";

function speakerLabel(speakers: Map<string, TranscriptSpeaker>, line: TranscriptLine): string {
  return line.speakerKey ? (speakers.get(line.speakerKey)?.label ?? UNKNOWN_SPEAKER) : UNKNOWN_SPEAKER;
}

function TranscriptRow({ line, speaker }: { line: TranscriptLine; speaker: string }) {
  return (
    <li className="grid gap-1 border-t border-line-200 py-3 first:border-t-0">
      <p className="text-xs text-ink-500">
        <span className="font-medium text-ink-700">{speaker}</span> · <span>{line.locator}</span>
      </p>
      <p lang={line.language} dir="auto" className="text-sm text-ink-900">
        {line.text}
      </p>
      {line.english && line.english !== line.text ? (
        <p lang="en" className="text-sm text-ink-700">
          {line.english}
          {line.englishSource === "MACHINE" ? <span className="ml-2 text-xs text-ink-500">({MACHINE_LABEL})</span> : null}
        </p>
      ) : null}
    </li>
  );
}

export function FieldTranscriptView({ transcript }: { transcript: FieldTranscript }) {
  const speakers = new Map(transcript.speakers.map((speaker) => [speaker.key, speaker]));
  return (
    <article className="grid gap-4">
      <section className="panel grid gap-2 p-5">
        <p className="text-sm text-ink-700">{transcript.citation}</p>
        {transcript.workshop ? <p className="text-sm text-ink-500">{transcript.workshop}</p> : null}
        {transcript.stage ? <p className="text-sm text-ink-500">{transcript.stage.label}</p> : null}
        {transcript.context.map((line) => (
          <p key={line} className="text-sm text-ink-500">
            {line}
          </p>
        ))}
        {transcript.crafts.length ? (
          <p className="flex flex-wrap gap-2 text-sm">
            {transcript.crafts.map((craft) => (
              <Link key={craft.slug} href={craft.path} className="underline underline-offset-2">
                {craft.name}
              </Link>
            ))}
          </p>
        ) : null}
      </section>
      <section className="panel p-5" aria-label="Transcript">
        <ol className="grid">
          {transcript.lines.map((line) => (
            <TranscriptRow key={line.id} line={line} speaker={speakerLabel(speakers, line)} />
          ))}
        </ol>
      </section>
      {transcript.english ? (
        <section className="panel grid gap-2 p-5" aria-label="English">
          <p lang="en" className="whitespace-pre-line text-sm text-ink-700">
            {transcript.english}
          </p>
          {transcript.englishSource === "MACHINE" ? <p className="text-xs text-ink-500">{MACHINE_LABEL}</p> : null}
        </section>
      ) : null}
    </article>
  );
}
