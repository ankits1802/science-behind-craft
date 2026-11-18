"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";

export type TabItem = { value: string; label: string; panel: ReactNode };

export function nextTabIndex(key: string, index: number, count: number): number | null {
  if (key === "ArrowRight") return (index + 1) % count;
  if (key === "ArrowLeft") return (index - 1 + count) % count;
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  return null;
}

export function Tabs({ label, items, value, onChange }: { label: string; items: TabItem[]; value: string; onChange: (value: string) => void }) {
  const base = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const current = Math.max(0, items.findIndex((item) => item.value === value));

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const rtl = getComputedStyle(event.currentTarget).direction === "rtl";
    const key = rtl && event.key === "ArrowRight" ? "ArrowLeft" : rtl && event.key === "ArrowLeft" ? "ArrowRight" : event.key;
    const next = nextTabIndex(key, current, items.length);
    if (next === null) return;
    event.preventDefault();
    onChange(items[next].value);
    refs.current[next]?.focus();
  }

  return (
    <div>
      <div role="tablist" aria-label={label} className="kv-tabs" onKeyDown={onKeyDown}>
        {items.map((item, index) => (
          <button
            key={item.value}
            ref={(node) => {
              refs.current[index] = node;
            }}
            type="button"
            role="tab"
            id={`${base}-tab-${index}`}
            aria-selected={index === current}
            aria-controls={`${base}-panel-${index}`}
            tabIndex={index === current ? 0 : -1}
            onClick={() => onChange(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${base}-panel-${current}`} aria-labelledby={`${base}-tab-${current}`} tabIndex={0} className="py-4">
        {items[current]?.panel}
      </div>
    </div>
  );
}
