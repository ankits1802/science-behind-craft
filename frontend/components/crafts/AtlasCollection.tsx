"use client";

import { useMemo, useState } from "react";

import { CollectionShelf } from "@/components/crafts/CollectionShelf";
import { NamesWall } from "@/components/crafts/NamesWall";
import { SegmentedChoice } from "@/components/ui/SegmentedChoice";
import { categoryHref, type AtlasShelf } from "@/lib/atlasCollection";
import { offersNamesWall, type NamedCraft } from "@/lib/atlasNames";
import type { NativeName } from "@/lib/editorialText";

export const COLLECTION_DEK =
  "Every craft has a plate on the ground of its material. Its name is set in its own script where a source records one, and in English until then; the strip under each plate always carries the English name.";

const VIEWS = [
  { value: "plates", label: "Plates" },
  { value: "names", label: "Names" }
];

export function AtlasCollection({ shelves, names }: { shelves: readonly AtlasShelf[]; names: readonly NamedCraft[] }) {
  const [view, setView] = useState("plates");
  const named = useMemo(() => new Map<string, NativeName>(names.map((entry) => [entry.slug, entry.nativeName])), [names]);
  const offered = offersNamesWall(names);
  const showNames = offered && view === "names";
  return (
    <section className="mt-[72px] border-t border-ink-1 pt-[22px]" aria-labelledby="atlas-collection" data-testid="atlas-collection">
      <div className="mb-9 grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end lg:gap-16">
        <div className="min-w-0">
          <h2 id="atlas-collection" className="font-headline text-h2 text-ink-1">
            The collection
          </h2>
          <p className="mt-3 max-w-[58ch] font-reading text-body-sm text-ink-2">{COLLECTION_DEK}</p>
        </div>
        {offered ? (
          <div className="grid justify-items-start gap-1.5">
            <span className="font-ui text-label text-ink-3">Show</span>
            <SegmentedChoice label="Show the collection as" value={view} options={VIEWS} onChange={setView} />
          </div>
        ) : null}
      </div>
      {showNames ? (
        <NamesWall names={names} />
      ) : (
        <div className="grid gap-14">
          {shelves.map((shelf, at) => (
            <CollectionShelf key={shelf.id} shelf={shelf} all={{ href: categoryHref(shelf) }} names={named} priority={at === 0} />
          ))}
        </div>
      )}
      <p className="mt-7 font-ui text-caption text-ink-3">
        {names.length ? "Names in their own scripts come from the sources of each craft’s monograph. " : null}Photographs carry their credit on the plate.
      </p>
    </section>
  );
}
