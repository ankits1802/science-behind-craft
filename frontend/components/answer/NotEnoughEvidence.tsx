import { SearchX } from "lucide-react";

import { ActionGroup } from "@/components/ui/ActionGroup";

export function NotEnoughEvidence({ message, onResearch }: { message: string; onResearch?: () => void }) {
  return (
    <section className="panel grid gap-3 p-5 md:p-6" aria-labelledby="not-enough-heading" data-testid="not-enough-evidence">
      <h2 id="not-enough-heading" className="flex items-center gap-2 font-display text-lg font-bold text-ink-900">
        <SearchX className="h-5 w-5 text-ink-500" aria-hidden />
        Not enough cited evidence yet
      </h2>
      <p className="text-sm leading-7 text-ink-700">{message}</p>
      {onResearch ? (
        <ActionGroup align="start">
          <button type="button" className="field-button" onClick={onResearch}>
            Research it live
          </button>
        </ActionGroup>
      ) : null}
    </section>
  );
}
