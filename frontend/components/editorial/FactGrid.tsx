import type { ReactNode } from "react";

export type Fact = { label: string; value: ReactNode };

export function FactGrid({ facts, columns = 4, className }: { facts: readonly Fact[]; columns?: 2 | 4; className?: string }) {
  if (facts.length === 0) return null;
  return (
    <dl className={className ? `kv-glance ${className}` : "kv-glance"} data-columns={columns} data-testid="fact-grid">
      {facts.map((fact) => (
        <div key={fact.label}>
          <dt className="font-ui text-label text-ink-3">{fact.label}</dt>
          <dd className="mt-1 font-reading text-body-sm leading-[1.45] text-ink-1">{fact.value}</dd>
        </div>
      ))}
    </dl>
  );
}
