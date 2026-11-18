import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type ChipProps = {
  children: ReactNode;
  pressed?: boolean;
  count?: number;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
};

export function Chip({ children, pressed, count, onClick, disabled, className }: ChipProps) {
  return (
    <button type="button" className={cn("kv-chip", className)} aria-pressed={pressed} onClick={onClick} disabled={disabled}>
      {children}
      {count === undefined ? null : <span className="kv-chip-count">{count}</span>}
    </button>
  );
}
