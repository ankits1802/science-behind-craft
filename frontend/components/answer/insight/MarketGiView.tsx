"use client";

import Link from "next/link";
import { BadgeCheck, Clock, MinusCircle, TriangleAlert, type LucideIcon } from "lucide-react";

import { CitedText } from "@/components/answer/ProseBlockView";
import type { GiStatus, MarketGiBlock, PriceRange } from "@/lib/explainerInsight";
import { GI_STATUS_LABEL, giFacts, priceMeta } from "@/lib/insightView";
import { cn } from "@/lib/utils";

const SUBHEAD = "text-[11px] font-semibold uppercase tracking-wide text-ink-500";

const STATUS_LOOK: Record<GiStatus["status"], { Icon: LucideIcon; className: string }> = {
  REGISTERED: { Icon: BadgeCheck, className: "border-evidence-300 bg-evidence-100 text-evidence-800 dark:border-evidence-800 dark:bg-evidence-950 dark:text-evidence-200" },
  APPLIED: { Icon: Clock, className: "border-purple-300 bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300" },
  WITHDRAWN: { Icon: MinusCircle, className: "border-line-200 bg-surface-50 text-ink-500" }
};

function GiStatusBadge({ status }: { status: GiStatus["status"] }) {
  const look = STATUS_LOOK[status];
  return (
    <span className={cn("inline-flex w-fit items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold", look.className)} data-testid="gi-status" data-status={status}>
      <look.Icon className="h-3.5 w-3.5" aria-hidden />
      {GI_STATUS_LABEL[status]}
    </span>
  );
}

function GiRecord({ gi, id }: { gi: GiStatus; id: string }) {
  const facts = giFacts(gi);
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3" data-testid="gi-record">
      {facts.length > 0 ? (
        <dl className="grid min-w-0 grid-cols-[repeat(2,minmax(0,1fr))] gap-2 sm:grid-cols-[repeat(3,minmax(0,1fr))]">
          {facts.map((fact) => (
            <div key={fact.label} className="grid min-w-0 gap-0.5 rounded-md border border-line-200 bg-surface-50 p-2.5" data-testid="gi-fact">
              <dt className="text-[11px] font-semibold text-ink-500">{fact.label}</dt>
              <dd className="break-words text-sm font-semibold tabular-nums text-ink-900">{fact.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {gi.proprietors.length > 0 ? (
        <p className="min-w-0 break-words text-sm text-ink-700" data-testid="gi-proprietors">
          <span className="font-semibold text-ink-900">{gi.proprietors.length === 1 ? "Proprietor" : "Proprietors"}: </span>
          {gi.proprietors.join("; ")}
        </p>
      ) : null}
      <CitedText id={`${id}-gi`} sentences={gi.sentences} className="text-sm leading-7 text-ink-700" />
    </div>
  );
}

function Imitation({ block }: { block: MarketGiBlock }) {
  return (
    <div className="grid min-w-0 gap-1.5 rounded-md border border-amber-500/40 p-3" data-testid="gi-imitation">
      <span className="inline-flex w-fit items-center gap-1 rounded-full border border-amber-500/30 bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
        <TriangleAlert className="h-3 w-3" aria-hidden />
        Signs of imitation
      </span>
      <CitedText id={`${block.id}-imitation`} sentences={block.imitation} className="text-sm leading-7 text-ink-700" />
    </div>
  );
}

function Price({ price }: { price: PriceRange }) {
  return (
    <li className="grid min-w-0 gap-1 rounded-md border border-line-200 bg-card p-3" data-testid="price-range">
      <span className="break-words font-display text-base font-bold tabular-nums text-ink-900">{price.stated}</span>
      <span className="text-xs font-semibold text-ink-500" data-testid="price-meta">
        {priceMeta(price)}
      </span>
      <CitedText id={price.sentence.id} sentences={[price.sentence]} className="text-sm leading-7 text-ink-700" />
    </li>
  );
}

export function MarketGiView({ block }: { block: MarketGiBlock }) {
  if (!block.gi && block.imitation.length === 0 && block.prices.length === 0) return null;
  return (
    <article className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3 rounded-lg border border-line-200 bg-card p-4 sm:p-5" data-testid="market-gi">
      <header className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1.5">
        <h3 className="min-w-0 break-words font-display text-lg font-bold text-ink-900">
          <Link href={block.craft.path} className="underline-offset-2 hover:underline">
            {block.craft.name}
          </Link>
        </h3>
        {block.gi ? <GiStatusBadge status={block.gi.status} /> : null}
      </header>
      {block.gi ? <GiRecord gi={block.gi} id={block.id} /> : null}
      {block.imitation.length > 0 ? <Imitation block={block} /> : null}
      {block.prices.length > 0 ? (
        <div className="grid min-w-0 gap-2">
          <h4 className={SUBHEAD}>Prices</h4>
          <ul className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 sm:grid-cols-[repeat(2,minmax(0,1fr))]">
            {block.prices.map((price) => (
              <Price key={price.sentence.id} price={price} />
            ))}
          </ul>
        </div>
      ) : null}
    </article>
  );
}
