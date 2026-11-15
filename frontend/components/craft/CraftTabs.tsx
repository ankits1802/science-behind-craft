"use client";

import { useRef } from "react";
import { motion } from "framer-motion";

import { springy } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { CRAFT_TABS, CRAFT_TAB_LABEL, type CraftTab } from "@/lib/craftProfile";
import { cn } from "@/lib/utils";

export function craftTabId(tab: CraftTab) {
  return `craft-tab-${tab}`;
}

export function craftPanelId(tab: CraftTab) {
  return `craft-panel-${tab}`;
}

export function CraftTabs({ value, onChange }: { value: CraftTab; onChange: (tab: CraftTab) => void }) {
  const reduce = useAppReducedMotion();
  const refs = useRef(new Map<CraftTab, HTMLButtonElement | null>());

  function focusTab(index: number) {
    const tab = CRAFT_TABS[(index + CRAFT_TABS.length) % CRAFT_TABS.length];
    onChange(tab);
    refs.current.get(tab)?.focus();
  }

  return (
    <div role="tablist" aria-label="Craft sections" className="-mx-4 flex gap-1 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0">
      {CRAFT_TABS.map((tab, index) => {
        const active = tab === value;
        return (
          <button
            key={tab}
            ref={(node) => {
              refs.current.set(tab, node);
            }}
            id={craftTabId(tab)}
            role="tab"
            type="button"
            aria-selected={active}
            aria-controls={craftPanelId(tab)}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(tab)}
            onKeyDown={(event) => {
              if (event.key === "ArrowRight") {
                event.preventDefault();
                focusTab(index + 1);
              } else if (event.key === "ArrowLeft") {
                event.preventDefault();
                focusTab(index - 1);
              } else if (event.key === "Home") {
                event.preventDefault();
                focusTab(0);
              } else if (event.key === "End") {
                event.preventDefault();
                focusTab(CRAFT_TABS.length - 1);
              }
            }}
            className={cn(
              "relative min-h-10 shrink-0 rounded-full px-4 text-sm font-medium transition",
              active ? "text-purple-700 dark:text-purple-200" : "text-ink-500 hover:text-ink-900"
            )}
          >
            {active ? (
              <motion.span
                layoutId="craft-tab-pill"
                transition={springy(reduce)}
                className="absolute inset-0 rounded-full border border-purple-300 bg-purple-50 dark:bg-purple-950/50"
                aria-hidden
              />
            ) : null}
            <span className="relative">{CRAFT_TAB_LABEL[tab]}</span>
          </button>
        );
      })}
    </div>
  );
}
