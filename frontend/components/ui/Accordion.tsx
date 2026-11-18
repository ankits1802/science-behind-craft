"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

export function Accordion({
  title,
  subtitle,
  defaultOpen = false,
  onOpenChange,
  headerRight,
  children
}: {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  headerRight?: React.ReactNode;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  function toggle() {
    const next = !open;
    setOpen(next);
    onOpenChange?.(next);
  }

  return (
    <section className="mb-5 border-t border-ink-1">
      <div className="flex items-center gap-3 py-4">
        <button
          type="button"
          onClick={toggle}
          aria-expanded={open}
          className="flex min-h-target min-w-0 flex-1 items-start gap-3 text-start"
        >
          <ChevronDown
            className={`mt-0.5 h-5 w-5 shrink-0 text-ink-3 ${open ? "rotate-180" : ""}`}
            aria-hidden
          />
          <span className="min-w-0">
            <span className="block font-reading text-h3 text-ink-1">{title}</span>
            {subtitle ? <span className="mt-1 block font-ui text-ui font-normal text-ink-3">{subtitle}</span> : null}
          </span>
        </button>
        {headerRight}
      </div>
      {open ? <div className="border-t border-rule py-4">{children}</div> : null}
    </section>
  );
}
