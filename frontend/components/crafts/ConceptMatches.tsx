import Link from "next/link";

import type { ConceptHit } from "@/lib/craftCatalogue";

const SHOWN_CRAFTS = 3;

function craftsLine(hit: ConceptHit): string {
  const count = hit.crafts.length;
  return `${count} ${count === 1 ? "craft" : "crafts"}`;
}

export function ConceptMatches({ matches }: { matches: readonly ConceptHit[] }) {
  if (matches.length === 0) return null;
  return (
    <section className="panel mb-5 p-4" aria-labelledby="concept-matches" data-testid="concept-matches">
      <h2 id="concept-matches" className="text-sm font-semibold text-ink-900">
        Materials and science
      </h2>
      <ul className="mt-3 grid gap-3 sm:grid-cols-2">
        {matches.map((hit) => (
          <li key={hit.concept.key} className="min-w-0" data-testid="concept-match">
            <p className="text-sm font-medium text-ink-900">
              {hit.concept.label} <span className="font-normal text-ink-500">· {craftsLine(hit)}</span>
            </p>
            <p className="mt-0.5 text-xs leading-5 text-ink-500">
              {hit.crafts.slice(0, SHOWN_CRAFTS).map((craft, index) => (
                <span key={craft.id}>
                  {index > 0 ? ", " : null}
                  <Link href={`/crafts/${encodeURIComponent(craft.slug)}`} className="underline-offset-2 hover:text-ink-900 hover:underline">
                    {craft.displayName}
                  </Link>
                </span>
              ))}
              {hit.crafts.length > SHOWN_CRAFTS ? ` and ${hit.crafts.length - SHOWN_CRAFTS} more below` : null}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
