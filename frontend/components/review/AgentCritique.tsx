import { CRITIQUE_LEAD, CRITIQUE_TITLE, noteHeading, notesLine, type DesignCritique } from "@/lib/designCritique";

type HeadingLevel = "h2" | "h4";

const HEADING_LOOKS: Record<HeadingLevel, string> = {
  h2: "font-reading text-h3 text-ink-1",
  h4: "font-ui text-h4 text-ink-1"
};

export function AgentCritique({ critique, level = "h4" }: { critique: DesignCritique; level?: HeadingLevel }) {
  const Heading = level;
  return (
    <section className="grid max-w-measure gap-2" data-testid="agent-critique">
      <Heading className={HEADING_LOOKS[level]}>{CRITIQUE_TITLE}</Heading>
      <p className="font-ui text-label text-ink-3">{CRITIQUE_LEAD}</p>
      <p className="font-reading text-body-sm text-ink-1">{critique.verdict}</p>
      <p className="font-ui text-label text-ink-2">{notesLine(critique)}</p>
      {critique.notes.length ? (
        <ol className="grid gap-3">
          {critique.notes.map((note, index) => (
            <li key={`${note.chapter}-${index}`} className="grid gap-0.5">
              <p className="font-ui text-label font-semibold text-ink-1 [overflow-wrap:anywhere]">{noteHeading(note)}</p>
              <p className="font-ui text-label text-ink-2">{note.problem}</p>
              <p className="font-ui text-label text-ink-1">{note.fix}</p>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}
