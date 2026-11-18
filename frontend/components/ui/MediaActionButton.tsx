"use client";

import type { ReactNode } from "react";

import { buttonLook } from "@/components/ui/button";


export function MediaActionButton({
  label,
  icon,
  onClick,
  disabled = false,
  accessibleLabel
}: {
  label: string;
  icon: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  accessibleLabel?: string;
}) {
  return (
    <button type="button" disabled={disabled} onClick={onClick} aria-label={accessibleLabel} {...buttonLook({ variant: "quiet", size: "sm", className: "shrink-0" })}>
      {icon}
      {label}
    </button>
  );
}
