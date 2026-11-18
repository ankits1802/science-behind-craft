"use client";

import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";

import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { isReaderCraft, loadCraftCatalogue, searchCatalogue } from "@/lib/craftCatalogue";
import type { CatalogueCraft, CraftCatalogue } from "@/lib/craftCatalogueContract";
import { ARTISAN_CRAFTS_MAX } from "@/lib/profileContract";

export type PickedCraft = { slug: string; displayName: string };

const OPTIONS_SHOWN = 50;

function craftHint(craft: CatalogueCraft): string {
  return [craft.localName, craft.familyLabel, craft.kindLabel].filter(Boolean).join(" · ");
}

export function CraftPicker({ picked, onChange }: { picked: PickedCraft[]; onChange: (next: PickedCraft[]) => void }) {
  const [catalogue, setCatalogue] = useState<CraftCatalogue | null>(null);
  const [failed, setFailed] = useState(false);
  const [term, setTerm] = useState("");

  useEffect(() => {
    let cancelled = false;
    loadCraftCatalogue()
      .then((loaded) => {
        if (!cancelled) setCatalogue(loaded);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const chosen = useMemo(() => new Set(picked.map((craft) => craft.slug)), [picked]);
  const found = useMemo(() => {
    if (!catalogue) return [];
    return searchCatalogue(catalogue, term).crafts.filter((craft) => isReaderCraft(craft) || craft.isCatchAll);
  }, [catalogue, term]);
  const options = found
    .filter((craft) => !chosen.has(craft.slug))
    .slice(0, OPTIONS_SHOWN)
    .map((craft) => ({ value: craft.slug, label: craft.displayName, hint: craftHint(craft) }));
  const full = picked.length >= ARTISAN_CRAFTS_MAX;

  function add(slug: string) {
    const craft = found.find((each) => each.slug === slug);
    if (!craft || full) return;
    onChange([...picked, { slug: craft.slug, displayName: craft.displayName }]);
    setTerm("");
  }

  if (failed) return <p className="text-sm text-error-600">Couldn&apos;t load the crafts. Reload the page.</p>;

  return (
    <div className="grid gap-2" data-testid="craft-picker">
      <SearchableSelect
        value=""
        onChange={add}
        options={options}
        ariaLabel="Which crafts do you practise?"
        placeholder={full ? `Up to ${ARTISAN_CRAFTS_MAX} crafts` : "Search crafts"}
        disabled={!catalogue || full}
        serverQuery={{ value: term, onChange: setTerm, pending: !catalogue, truncated: found.length - chosen.size > OPTIONS_SHOWN }}
      />
      {picked.length ? (
        <ul className="flex flex-wrap gap-2" aria-label="Your crafts">
          {picked.map((craft) => (
            <li key={craft.slug} className="inline-flex items-center gap-1 rounded-full border border-line-200 bg-surface-50 py-1 pl-3 pr-1 text-sm text-ink-900">
              {craft.displayName}
              <button
                type="button"
                aria-label={`Remove ${craft.displayName}`}
                onClick={() => onChange(picked.filter((each) => each.slug !== craft.slug))}
                className="grid h-7 w-7 place-items-center rounded-full text-ink-500 hover:bg-card"
              >
                <X className="h-3.5 w-3.5" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
