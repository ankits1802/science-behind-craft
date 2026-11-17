"use client";

import { ClaimChips } from "@/components/craft/CraftClaims";
import type { StageItem } from "@/lib/craftPageContract";
import { materialRoleText } from "@/lib/processView";

export function StageMaterials({ items, testId }: { items: readonly StageItem[]; testId: string }) {
  return (
    <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {items.map((item) => (
        <li key={item.id} className="min-w-0 rounded-md border border-line-200 bg-surface-50 px-3 py-2.5" data-testid={testId}>
          <span className="block text-sm font-semibold text-ink-900 [overflow-wrap:anywhere]">
            {item.name}
            <ClaimChips ids={item.claimIds} />
          </span>
          {item.localNames.length > 0 ? <span className="block text-xs italic text-ink-700 [overflow-wrap:anywhere]">{item.localNames.join(", ")}</span> : null}
          <span className="block text-xs text-ink-500">{materialRoleText(item.role, item.kind)}</span>
        </li>
      ))}
    </ul>
  );
}
