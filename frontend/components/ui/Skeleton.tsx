import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type SkeletonShape = "masthead" | "lede" | "plateGrid" | "chart" | "legend";

function Block({ className }: { className: string }) {
  return <span aria-hidden className={cn("kv-sk motion-pulse block", className)} />;
}

function Lines({ widths }: { widths: string[] }) {
  return (
    <span aria-hidden className="block">
      {widths.map((width) => (
        <span key={width} className={cn("kv-sk kv-sk-line motion-pulse block", width)} />
      ))}
    </span>
  );
}

const SHAPES: Record<SkeletonShape, ReactNode> = {
  masthead: (
    <>
      <Block className="aspect-[4/3] w-full lg:aspect-[16/7.4]" />
      <Block className="mt-5 h-11 w-3/5" />
      <span className="mt-4 block">
        <Lines widths={["w-[94%]", "w-[88%]", "w-[72%]"]} />
      </span>
    </>
  ),
  lede: (
    <>
      <Block className="h-11 w-3/5" />
      <span className="mt-4 block">
        <Lines widths={["w-full", "w-[94%]", "w-[88%]", "w-[60%]"]} />
      </span>
    </>
  ),
  plateGrid: (
    <>
      <Block className="h-[1.125rem] w-[30%]" />
      <span className="mt-3.5 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
        {["a", "b", "c", "d", "e", "f"].map((key) => (
          <Block key={key} className="h-36" />
        ))}
      </span>
    </>
  ),
  chart: (
    <>
      <Block className="h-3 w-16" />
      <Block className="mt-2.5 h-6 w-4/5" />
      <Block className="mt-4 aspect-[16/7] w-full" />
    </>
  ),
  legend: (
    <>
      <Block className="h-3 w-1/3" />
      <Block className="mt-3 h-2.5 w-full max-w-sm" />
      <span className="mt-3 grid gap-x-4 gap-y-1.5 sm:grid-cols-2">
        {["a", "b", "c", "d", "e", "f"].map((key) => (
          <Block key={key} className="h-3 w-3/4" />
        ))}
      </span>
    </>
  )
};

export function Skeleton({ shape, label, className }: { shape: SkeletonShape; label: string; className?: string }) {
  return (
    <div aria-busy="true" role="status" className={cn("block", className)} data-skeleton={shape}>
      <span className="sr-only">{label}</span>
      {SHAPES[shape]}
    </div>
  );
}
