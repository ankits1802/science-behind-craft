"use client";

import Link from "next/link";
import { useId, useState } from "react";

import { TextLink } from "@/components/ui/TextLink";
import { RANKED_SHOWN } from "@/lib/mapStates";
import { cn } from "@/lib/utils";

export type RankedRow = { key: string; name: string; value: number; display?: string; href?: string; onPick?: () => void };
export type RankedAll = { href: string; label: string } | { label: string };

function RowName({ row, emph }: { row: RankedRow; emph: boolean }) {
  const look = cn("min-w-0 break-words", emph ? "font-semibold text-ink-1" : "text-ink-1");
  if (row.href) {
    return (
      <Link href={row.href} className={cn(look, "underline-offset-3 hover:text-indigo-hover hover:underline")}>
        {row.name}
      </Link>
    );
  }
  if (row.onPick) {
    return (
      <button type="button" onClick={row.onPick} className={cn(look, "text-start underline-offset-3 hover:text-indigo-hover hover:underline")}>
        {row.name}
      </button>
    );
  }
  return <span className={look}>{row.name}</span>;
}

function Row({ row, largest, emph, series }: { row: RankedRow; largest: number; emph: boolean; series: string }) {
  const share = largest > 0 ? Math.max(0, row.value / largest) : 0;
  return (
    <li className="grid grid-cols-[minmax(6rem,10rem)_minmax(0,1fr)_auto] items-center gap-3 border-t border-rule py-[7px]" data-emph={emph || undefined} data-testid="ranked-row">
      <RowName row={row} emph={emph} />
      <span className="relative h-2 bg-rule" aria-hidden>
        <i className="absolute inset-y-0 start-0" style={{ width: `${(share * 100).toFixed(1)}%`, backgroundColor: emph ? "var(--chart-emph)" : series }} />
      </span>
      <b className={cn("text-end [font-variant-numeric:lining-nums_tabular-nums]", emph ? "font-semibold text-ink-1" : "font-medium text-ink-2")}>{row.display ?? row.value.toLocaleString("en-IN")}</b>
    </li>
  );
}

export function RankedList({ rows, label, all, emphKey, series = "var(--series-count)", className }: { rows: readonly RankedRow[]; label: string; all?: RankedAll; emphKey?: string | null; series?: string; className?: string }) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  const largest = rows.reduce((most, row) => Math.max(most, row.value), 0);
  const shown = open ? rows : rows.slice(0, RANKED_SHOWN);
  const more = rows.length > RANKED_SHOWN;
  return (
    <div className={cn("grid gap-3.5 font-ui text-ui font-normal", className)}>
      <ol id={listId} aria-label={label} className="grid border-b border-rule" data-testid="ranked-list">
        {shown.map((row) => (
          <Row key={row.key} row={row} largest={largest} emph={row.key === emphKey} series={series} />
        ))}
      </ol>
      {all && "href" in all ? (
        <p>
          <TextLink href={all.href} standalone>
            {all.label}
          </TextLink>
        </p>
      ) : all && more ? (
        <p>
          <TextLink onClick={() => setOpen((value) => !value)} expanded={open} controls={listId} standalone>
            {open ? "Show the first ten" : all.label}
          </TextLink>
        </p>
      ) : null}
    </div>
  );
}
