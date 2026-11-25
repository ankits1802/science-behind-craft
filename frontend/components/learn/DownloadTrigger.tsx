"use client";

import type { Ref } from "react";
import { ChevronDown, Download } from "lucide-react";

import { Button } from "@/components/ui/button";

type TriggerProps = { ref: Ref<HTMLButtonElement>; label: string; open: boolean; onToggle: () => void; testId?: string; busy?: boolean; busyLabel?: string };

export function DownloadTrigger({ ref, label, open, onToggle, testId, busy = false, busyLabel }: TriggerProps) {
  return (
    <Button ref={ref} variant="quiet" size="sm" busy={busy} busyLabel={busyLabel} aria-expanded={open} aria-haspopup="dialog" onClick={onToggle} data-testid={testId}>
      <Download aria-hidden />
      {label}
      <ChevronDown aria-hidden />
    </Button>
  );
}
