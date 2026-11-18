import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Section({ id, title, lede, children }: { id: string; title: string; lede?: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="kv-chapter border-t border-ink-1 py-section">
      <h2 id={`${id}-title`} className="font-headline text-h2 text-ink-1">
        {title}
      </h2>
      {lede ? <p className="mt-3 max-w-measure font-reading text-lede text-ink-2">{lede}</p> : null}
      <div className="mt-8 grid gap-6">{children}</div>
    </section>
  );
}

export function Demo({ caption, raised = false, className, children }: { caption: string; raised?: boolean; className?: string; children: ReactNode }) {
  return (
    <div className={cn("min-w-0 rounded-plate border border-rule p-5 sm:p-6", raised ? "bg-raised" : "bg-ground", className)}>
      <p className="kicker mb-4">{caption}</p>
      {children}
    </div>
  );
}

export function States({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("flex flex-wrap items-start gap-x-5 gap-y-6", className)}>{children}</div>;
}

export function State({ label, children }: { label: string; children: ReactNode }) {
  return (
    <figure className="grid justify-items-start gap-2">
      {children}
      <figcaption className="font-ui text-caption text-ink-3">{label}</figcaption>
    </figure>
  );
}

export function Grid({ columns = 2, children }: { columns?: 2 | 3; children: ReactNode }) {
  return <div className={cn("grid gap-6", columns === 2 ? "lg:grid-cols-2" : "md:grid-cols-2 lg:grid-cols-3")}>{children}</div>;
}

export const FORCED_FOCUS = "outline-2 outline-offset-3 outline-indigo outline-solid";
