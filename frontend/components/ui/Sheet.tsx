"use client";

import { forwardRef, useEffect, useId, useRef, useState, type KeyboardEventHandler, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";

import { useModalFocus } from "@/components/hooks/useModalFocus";
import { cn } from "@/lib/utils";

export type SheetPanelProps = {
  label?: string;
  labelledBy?: string;
  panelId?: string;
  className?: string;
  stacked?: boolean;
  onKeyDown?: KeyboardEventHandler<HTMLDivElement>;
  children: ReactNode;
};

export const SheetPanel = forwardRef<HTMLDivElement, SheetPanelProps>(({ label, labelledBy, panelId, className, stacked = false, onKeyDown, children }, ref) => (
  <div
    ref={ref}
    id={panelId}
    role="dialog"
    aria-modal="true"
    aria-label={labelledBy ? undefined : label}
    aria-labelledby={labelledBy}
    tabIndex={-1}
    data-modal-layer=""
    data-stacked={stacked ? "" : undefined}
    data-testid="sheet"
    onKeyDown={onKeyDown}
    className={cn("kv-sheet motion-rise outline-hidden", className)}
  >
    {children}
  </div>
));
SheetPanel.displayName = "SheetPanel";

export type SheetProps = Omit<SheetPanelProps, "onKeyDown"> & {
  open: boolean;
  onClose: () => void;
  initialFocusRef?: RefObject<HTMLElement | null>;
};

export function Sheet({ open, onClose, initialFocusRef, ...panel }: SheetProps) {
  const id = useId();
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const onKeyDown = useModalFocus({ id, open, panelRef, onEscape: onClose, initialFocusRef });

  if (!mounted || !open) return null;

  return createPortal(
    <>
      <div className="kv-scrim" aria-hidden onMouseDown={onClose} data-stacked={panel.stacked ? "" : undefined} data-testid="sheet-scrim" />
      <SheetPanel ref={panelRef} onKeyDown={onKeyDown} {...panel} />
    </>,
    document.body
  );
}
