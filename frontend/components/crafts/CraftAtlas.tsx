"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { BookOpen, RotateCw } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { FieldBlock } from "@/components/FormControls";
import { ConceptMatches } from "@/components/crafts/ConceptMatches";
import { PageHeader } from "@/components/PageHeader";
import { SearchInput } from "@/components/SearchInput";
import { Dropdown } from "@/components/ui/Dropdown";
import {
  catalogueCountLine,
  craftStatesLine,
  groupCrafts,
  readerCount,
  searchCatalogue,
  shownCountLine,
  useCraftCatalogue,
  withinCategory,
  type CatalogueSearch
} from "@/lib/craftCatalogue";
import type { CatalogueCraft, CraftCatalogue } from "@/lib/craftCatalogueContract";

const NOTHING_FOUND: CatalogueSearch = { concepts: [], crafts: [] };

export function CraftAtlasHeader({ line }: { line?: string }) {
  return <PageHeader title="Crafts" description={line} icon={<BookOpen className="h-5 w-5" aria-hidden />} back={false} />;
}

export function CraftAtlas({ initial }: { initial: CraftCatalogue | null }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { catalogue: loaded, error, loading, reload } = useCraftCatalogue();
  const catalogue = loaded ?? initial;
  const [query, setQuery] = useState(() => params.get("q") ?? "");
  const [category, setCategory] = useState(() => params.get("category") ?? "");
  const deferred = useDeferredValue(query);

  useEffect(() => {
    const search = new URLSearchParams();
    if (query.trim()) search.set("q", query.trim());
    if (category) search.set("category", category);
    const next = search.toString();
    const timer = setTimeout(() => router.replace(next ? `${pathname}?${next}` : pathname, { scroll: false }), 300);
    return () => clearTimeout(timer);
  }, [category, pathname, query, router]);

  const found = useMemo(() => withinCategory(catalogue ? searchCatalogue(catalogue, deferred) : NOTHING_FOUND, category), [catalogue, category, deferred]);
  const visible = found.crafts;

  const groups = useMemo(() => (catalogue ? groupCrafts(catalogue, visible) : []), [catalogue, visible]);
  const categoryOptions = useMemo(
    () => [
      { value: "", label: "Every category" },
      ...(catalogue?.categories ?? [])
        .slice()
        .sort((a, b) => a.sortOrder - b.sortOrder)
        .map((row) => ({ value: row.id, label: row.label ?? row.name }))
    ],
    [catalogue]
  );

  if (!catalogue) {
    return (
      <>
        <CraftAtlasHeader />
        {loading ? (
          <section className="panel p-6 text-sm text-ink-500">Loading…</section>
        ) : (
          <section role="alert" className="panel grid justify-items-center gap-3 p-6 text-center">
            <p className="text-sm text-ink-700">{error ?? "Couldn't load the craft list."}</p>
            <button type="button" className="field-button" onClick={reload}>
              <RotateCw className="h-4 w-4" aria-hidden />
              Try again
            </button>
          </section>
        )}
      </>
    );
  }

  const filtered = Boolean(deferred.trim() || category);

  return (
    <>
      <CraftAtlasHeader line={catalogueCountLine(catalogue)} />

      <section className="panel mb-5 grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_16rem] md:items-end">
        <SearchInput value={query} onChange={setQuery} placeholder="Search by name, place or family" ariaLabel="Search crafts" />
        <FieldBlock label="Category">
          <Dropdown value={category} onChange={setCategory} options={categoryOptions} searchable={false} advanceOnSelect={false} />
        </FieldBlock>
      </section>

      <p className="mb-3 text-sm text-ink-500" role="status" data-testid="craft-count">
        {filtered ? shownCountLine(catalogue, visible) : null}
      </p>

      <ConceptMatches matches={found.concepts} />

      {visible.length === 0 ? (
        <EmptyState title={deferred.trim() ? `No craft matches “${deferred.trim()}”.` : "No crafts in this category."} />
      ) : (
        <div className="grid gap-5">
          {groups.map((group) => (
            <section key={group.key} className="panel overflow-hidden" aria-labelledby={`group-${group.key}`}>
              <h2 id={`group-${group.key}`} className="flex items-center justify-between gap-3 border-b border-line-200 bg-surface-50 px-4 py-2.5 text-sm font-semibold text-ink-900">
                <span className="min-w-0 truncate">{group.heading}</span>
                <GroupCount count={readerCount(group.crafts)} />
              </h2>
              <ul className="divide-y divide-line-200">
                {group.crafts.map((craft) => (
                  <CraftRow key={craft.id} craft={craft} />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </>
  );
}

function GroupCount({ count }: { count: number }) {
  if (count === 0) return null;
  return <span className="shrink-0 text-xs font-medium tabular-nums text-ink-500">{count}</span>;
}

function CraftRow({ craft }: { craft: CatalogueCraft }) {
  const states = craftStatesLine(craft);
  return (
    <li>
      <Link
        href={`/crafts/${encodeURIComponent(craft.slug)}`}
        className="flex min-h-12 items-center gap-3 px-4 py-2.5 transition hover:bg-field-100"
        data-testid="craft-row"
      >
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-ink-900">
            {craft.displayName}
            {craft.localName && craft.localName !== craft.displayName ? <span className="ml-2 font-normal text-ink-500">{craft.localName}</span> : null}
          </span>
          {states ? <span className="block truncate text-xs text-ink-500">{states}</span> : null}
        </span>
        {craft.giStatus === "GI" ? (
          <span className="shrink-0 rounded-full border border-success-600/25 bg-success-100 px-2 py-0.5 text-[11px] font-semibold text-success-600">GI</span>
        ) : null}
      </Link>
    </li>
  );
}
