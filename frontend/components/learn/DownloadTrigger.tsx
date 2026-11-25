"use client";

import type { Ref } from "react";
import { ChevronDown, Download } from "lucide-react";

import { buttonLook } from "@/components/ui/button";

type TriggerProps = { ref: Ref<HTMLButtonElement>; label: string; open: boolean; onToggle: () => void; testId?: string };

export function DownloadTrigger({ ref, label, open, onToggle, testId }: TriggerProps) {
  return (
    <button ref={ref} type="button" {...buttonLook({ variant: "quiet", size: "sm" })} aria-expanded={open} aria-haspopup="dialog" onClick={onToggle} data-testid={testId}>
      <Download aria-hidden />
      {label}
      <ChevronDown aria-hidden />
    </button>
  );
}
