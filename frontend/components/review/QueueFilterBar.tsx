"use client";

import { useEffect, useMemo, useState } from "react";

import { Field } from "@/components/FormControls";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { loadCraftCatalogue, searchCatalogue } from "@/lib/craftCatalogue";
import type { CraftCatalogue } from "@/lib/craftCatalogueContract";
import { REVIEW_ORIGINS, type ReviewFilters, type ReviewOrigin } from "@/lib/reviewQueueContract";
import { ORIGIN_LABELS } from "@/lib/reviewQueueView";

const CRAFTS_SHOWN = 50;
const ORIGIN_OPTIONS = REVIEW_ORIGINS.map((value) => ({ value, label: ORIGIN_LABELS[value] }));

export function QueueFilterBar({ filters, onChange }: { filters: ReviewFilters; onChange: (next: ReviewFilters) => void }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Field label="Arrived from">
        <SearchableSelect
          value={filters.origin ?? ""}
          onChange={(value) => onChange({ ...filters, origin: (value || null) as ReviewOrigin | null })}
          options={ORIGIN_OPTIONS}
          noneLabel="Everywhere"
          placeholder="Everywhere"
          searchable={false}
        />
      </Field>
      <Field label="Craft">
        <CraftFilter slug={filters.craft} onChange={(craft) => onChange({ ...filters, craft })} />
      </Field>
    </div>
  );
}

function CraftFilter({ slug, onChange }: { slug: string | null; onChange: (slug: string | null) => void }) {
  const [catalogue, setCatalogue] = useState<CraftCatalogue | null>(null);
  const [term, setTerm] = useState("");

  useEffect(() => {
    let cancelled = false;
    loadCraftCatalogue()
      .then((loaded) => {
        if (!cancelled) setCatalogue(loaded);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const options = useMemo(() => {
    const found = catalogue ? searchCatalogue(catalogue, term).crafts.slice(0, CRAFTS_SHOWN) : [];
    const shown = found.map((craft) => ({ value: craft.slug, label: craft.displayName }));
    return slug && !shown.some((option) => option.value === slug) ? [{ value: slug, label: slug }, ...shown] : shown;
  }, [catalogue, term, slug]);

  return (
    <SearchableSelect
      value={slug ?? ""}
      onChange={(value) => onChange(value || null)}
      options={options}
      noneLabel="Every craft"
      placeholder="Every craft"
      serverQuery={{ value: term, onChange: setTerm, pending: !catalogue }}
    />
  );
}
