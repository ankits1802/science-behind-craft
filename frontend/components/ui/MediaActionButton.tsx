"use client";

import type { ReactNode } from "react";

export const MEDIA_ACTION_CLASS =
  "inline-flex min-h-11 shrink-0 items-center justify-center gap-1.5 rounded-md border border-purple-600 bg-purple-50 px-3 text-sm font-semibold text-purple-800 transition enabled:hover:border-purple-700 enabled:hover:bg-purple-100 disabled:cursor-not-allowed disabled:border-ink-300 disabled:bg-surface-50 disabled:text-ink-500 sm:min-h-9 pointer-coarse:min-h-11 dark:border-purple-500 dark:bg-purple-950 dark:text-purple-200 dark:enabled:hover:border-purple-400 dark:enabled:hover:bg-purple-900";

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
    <button type="button" disabled={disabled} onClick={onClick} aria-label={accessibleLabel} className={MEDIA_ACTION_CLASS}>
      {icon}
      {label}
    </button>
  );
}
