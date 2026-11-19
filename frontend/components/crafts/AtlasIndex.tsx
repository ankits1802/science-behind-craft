"use client";

import Link from "next/link";
import { useId, useState, type ReactNode } from "react";

import { FamilySwatch } from "@/components/crafts/FamilySwatch";
import { TextLink } from "@/components/ui/TextLink";
import { categoryHref, familyMaterial, familyName, indexSubLine, sortedFamilies, subFamilyCounts } from "@/lib/atlasCollection";
import { ALL_INDIA, allPlacesLabel, PLACES_SHOWN, searchHref, shownIdeas, type StateCounts } from "@/lib/atlasIndex";
import type { CraftCatalogue } from "@/lib/craftCatalogueContract";

const ROW = "group flex items-baseline gap-3 border-b border-rule py-[9px]";
const NAME = "font-reading text-body-sm font-medium text-ink-1 group-hover:text-indigo group-hover:underline group-hover:underline-offset-3";
const COUNT = "ms-auto font-ui text-ui font-medium text-ink-2 [font-variant-numeric:tabular-nums]";

function Column({ title, className, children }: { title: string; className?: string; children: ReactNode }) {
  return (
    <div className={className}>
      <h3 className="kicker border-b border-rule pb-2">{title}</h3>
      {children}
    </div>
  );
}

function Families({ catalogue }: { catalogue: CraftCatalogue }) {
  return (
    <ol>
      {sortedFamilies(catalogue).map((category) => (
        <li key={category.id}>
          <Link href={categoryHref(category)} className={`${ROW} items-center`} data-testid="index-family">
            <FamilySwatch material={familyMaterial(category)} className="h-[42px] w-[34px]" />
            <span className="grid min-w-0 gap-0.5">
              <span className={NAME}>{familyName(category)}</span>
              <span className="font-ui text-label font-normal text-ink-3">{indexSubLine(subFamilyCounts(category))}</span>
            </span>
            <b className={COUNT}>{category.readerCount}</b>
          </Link>
        </li>
      ))}
    </ol>
  );
}

function PlaceRow({ name, count }: { name: string; count: number }) {
  return (
    <li>
      <Link href={searchHref(name)} className={ROW} data-testid="index-place">
        <span className={NAME}>{name}</span>
        <b className={COUNT}>{count}</b>
      </Link>
    </li>
  );
}

function Places({ counts }: { counts: StateCounts }) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  const shown = open ? counts.states : counts.states.slice(0, PLACES_SHOWN);
  const more = counts.states.length > PLACES_SHOWN || counts.allIndia > 0;
  return (
    <>
      <ol id={listId}>
        {shown.map((state) => (
          <PlaceRow key={state.name} name={state.name} count={state.count} />
        ))}
        {open && counts.allIndia > 0 ? <PlaceRow name={ALL_INDIA} count={counts.allIndia} /> : null}
      </ol>
      {more ? (
        <p className="mt-3">
          <TextLink onClick={() => setOpen((value) => !value)} expanded={open} controls={listId} standalone>
            {open ? "Show the first twelve" : allPlacesLabel(counts)}
          </TextLink>
        </p>
      ) : null}
    </>
  );
}

function Ideas({ catalogue }: { catalogue: CraftCatalogue }) {
  return (
    <ol>
      {shownIdeas(catalogue).map((concept) => (
        <li key={concept.key}>
          <Link href={searchHref(concept.label)} className={ROW} data-testid="index-idea">
            <span className={NAME}>{concept.label}</span>
            <b className={COUNT}>{concept.craftSlugs.length}</b>
          </Link>
        </li>
      ))}
    </ol>
  );
}

export function AtlasIndex({ catalogue, counts }: { catalogue: CraftCatalogue; counts: StateCounts }) {
  return (
    <section className="mt-14 border-t border-ink-1 pt-[22px]" aria-labelledby="atlas-index" data-testid="atlas-index">
      <h2 id="atlas-index" className="font-reading text-h3 text-ink-1">
        Index
      </h2>
      <div className="mt-[18px] grid grid-cols-1 gap-8 md:grid-cols-2 rail:grid-cols-[minmax(0,6fr)_minmax(0,3fr)_minmax(0,3fr)] rail:gap-12">
        <Column title="Families" className="md:col-span-2 rail:col-span-1">
          <Families catalogue={catalogue} />
        </Column>
        <Column title="Places">
          <Places counts={counts} />
        </Column>
        {catalogue.concepts.length ? (
          <Column title="Ideas">
            <Ideas catalogue={catalogue} />
          </Column>
        ) : null}
      </div>
    </section>
  );
}
