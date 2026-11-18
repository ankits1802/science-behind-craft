"use client";

import { Info } from "lucide-react";

import { infoToggleAria } from "@/components/ui/infoToggleAria";

export function InfoToggle({
  fieldLabel,
  expanded,
  panelId,
  onToggle
}: {
  fieldLabel: string;
  expanded: boolean;
  panelId: string;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      {...infoToggleAria(fieldLabel, expanded, panelId)}
      data-info-toggle=""
      onClick={onToggle}
      className={
        expanded
          ? "relative inline-grid h-5 w-5 shrink-0 place-items-center rounded-full bg-indigo-wash text-indigo-hover transition-colors after:absolute after:-inset-3 after:content-['']"
          : "relative inline-grid h-5 w-5 shrink-0 place-items-center rounded-full text-ink-3 transition-colors hover:bg-sunk hover:text-ink-1 after:absolute after:-inset-3 after:content-['']"
      }
    >
      <Info className="h-4 w-4" aria-hidden />
    </button>
  );
}

export function InfoPanel({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <p
      id={id}
      data-info-panel=""
      className="rounded-control bg-sunk px-3 py-2 font-ui text-label font-normal text-ink-2"
    >
      {children}
    </p>
  );
}
