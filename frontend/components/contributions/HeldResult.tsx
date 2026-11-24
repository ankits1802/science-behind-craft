import { TextLink } from "@/components/ui/TextLink";
import { partLine, type PageHoldView } from "@/lib/pageHoldContract";

export function HeldResult({ view }: { view: PageHoldView }) {
  const result = view.result;
  return (
    <section className="grid gap-3" aria-labelledby="held-result-h">
      <h2 id="held-result-h" className="font-reading text-h3 text-ink-1">
        What happened
      </h2>
      {result ? <p className="max-w-measure font-reading text-body-sm text-ink-1">{result.message}</p> : null}
      {result?.parts.length ? (
        <ul className="grid gap-3" data-testid="held-result">
          {result.parts.map((part) => (
            <li key={`${part.part}-${part.index}`} className="grid gap-0.5 border-t border-rule pt-3" data-outcome={part.outcome}>
              <p className="font-ui text-ui text-ink-1">{partLine(part)}</p>
              <p className="max-w-measure font-ui text-label text-ink-2">{part.message}</p>
            </li>
          ))}
        </ul>
      ) : null}
      <p className="font-ui text-ui">
        <TextLink href="/contributions/components">Back to your components</TextLink>
      </p>
    </section>
  );
}
