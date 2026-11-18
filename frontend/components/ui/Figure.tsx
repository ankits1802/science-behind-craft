import type { ReactNode } from "react";

import { figureKicker } from "@/lib/editorialText";
import { cn } from "@/lib/utils";

export type FigureProps = {
  number: number;
  kind?: "chart" | "diagram" | "map" | "table";
  title: ReactNode;
  dek?: ReactNode;
  source?: ReactNode;
  table?: ReactNode;
  valueCount?: number;
  id?: string;
  className?: string;
  children: ReactNode;
};

export function Figure({ number, kind = "chart", title, dek, source, table, valueCount, id, className, children }: FigureProps) {
  const kicker = figureKicker(kind === "table" ? "table" : "figure", number);
  const [word, digits] = kicker.split(" ");
  return (
    <figure id={id} className={cn("kv-figure", className)} data-kind={kind} data-testid="figure">
      <figcaption>
        <p className="kv-fig-no">
          {word} <b>{digits}</b>
        </p>
        <p className="font-reading text-h3 text-ink-1 [font-variant-numeric:lining-nums]">{title}</p>
        {dek ? <p className="mt-1.5 max-w-[76ch] font-ui text-ui font-normal text-ink-2">{dek}</p> : null}
      </figcaption>
      <div className="mt-3.5 min-w-0">{children}</div>
      {source ? <p className="mt-2.5 font-ui text-caption text-ink-3">{source}</p> : null}
      {table ? (
        <details className="mt-2">
          <summary className="kv-link inline-flex min-h-target cursor-pointer items-center font-ui text-ui">{valueCount === undefined ? "All values" : `All ${valueCount} values`}</summary>
          <div className="mt-2 overflow-x-auto">{table}</div>
        </details>
      ) : null}
    </figure>
  );
}
