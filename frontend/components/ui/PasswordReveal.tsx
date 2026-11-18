"use client";

import { Eye, EyeOff } from "lucide-react";

import { cn } from "@/lib/utils";

export function PasswordRevealButton({
  revealed,
  onToggle,
  className,
  size = 22,
  noun = "password"
}: {
  revealed: boolean;
  onToggle: () => void;
  className?: string;
  size?: number;
  noun?: string;
}) {
  return (
    <button
      type="button"
      aria-label={revealed ? `Hide ${noun}` : `Show ${noun}`}
      aria-pressed={revealed}
      onClick={onToggle}
      className={cn(
        "absolute end-1 top-1/2 grid h-target w-target -translate-y-1/2 place-items-center rounded-full text-ink-3 transition-colors hover:bg-sunk hover:text-ink-1",
        className
      )}
    >
      {revealed ? <EyeOff size={size} aria-hidden /> : <Eye size={size} aria-hidden />}
    </button>
  );
}
