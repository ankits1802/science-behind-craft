"use client";

import { cn } from "@/lib/utils";

export type SegmentOption = { value: string; label: string; disabled?: boolean; reason?: string };

export function SegmentedChoice({
  label,
  value,
  options,
  onChange,
  disabled = false,
  fill = false
}: {
  label: string;
  value: string;
  options: SegmentOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
  fill?: boolean;
}) {
  return (
    <div role="group" aria-label={label} className={cn("kv-seg", fill ? "flex w-full" : "w-fit")}>
      {options.map((option) => {
        const on = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={on}
            disabled={disabled || option.disabled}
            title={option.disabled ? option.reason : undefined}
            className={fill ? "flex-1" : undefined}
            onClick={() => {
              if (!on) onChange(option.value);
            }}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
