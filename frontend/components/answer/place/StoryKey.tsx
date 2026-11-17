"use client";

import type { ReactNode } from "react";

import { STORY_TONES, type StoryGeometry } from "@/components/answer/place/storyGeometry";
import type { StoryLayer } from "@/components/answer/place/useStoryLayer";
import { Swatch } from "@/components/map/ChoroplethLegend";
import type { RegionStoryBlock } from "@/lib/explainerPlace";
import { riverLabel } from "@/lib/regionStory";
import { cn } from "@/lib/utils";

type KeyItem = { key: string; label: string; mark: ReactNode };

function RiverMark() {
  return (
    <svg width={18} height={14} aria-hidden className="shrink-0">
      <path d="M1 10 C6 2 11 12 17 4" fill="none" strokeWidth={2.5} strokeLinecap="round" className="stroke-errand-600 dark:stroke-errand-400" />
    </svg>
  );
}

function keyItems(block: RegionStoryBlock, geometry: StoryGeometry, layered: boolean): KeyItem[] {
  const drawn = [...geometry.districts.keys()];
  const items: KeyItem[] = [];
  if (geometry.river) items.push({ key: "river", label: riverLabel(block), mark: <RiverMark /> });
  if (layered) return items;
  if (drawn.some((lgd) => geometry.entries.has(lgd))) items.push({ key: "reached", label: "Districts it reaches", mark: <Swatch className={STORY_TONES.reached} /> });
  if (drawn.some((lgd) => !geometry.entries.has(lgd))) items.push({ key: "story", label: "Other districts", mark: <Swatch className={STORY_TONES.story} /> });
  return items;
}

export function StoryKey({ block, geometry, layered }: { block: RegionStoryBlock; geometry: StoryGeometry; layered: boolean }) {
  const items = keyItems(block, geometry, layered);
  if (items.length < 2) return null;
  return (
    <ul className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-ink-700" data-testid="story-key">
      {items.map((item) => (
        <li key={item.key} className="inline-flex items-center gap-1.5">
          {item.mark}
          {item.label}
        </li>
      ))}
    </ul>
  );
}

export function StoryLayerPicker({ story, base }: { story: StoryLayer; base: string }) {
  if (story.offered.length === 0) return null;
  const options = [{ id: null, label: base }, ...story.offered.map((layer) => ({ id: layer.id, label: layer.title }))];
  return (
    <div role="group" aria-label="Map layer" className="flex min-w-0 flex-wrap gap-1.5" data-testid="story-layers">
      {options.map((option) => {
        const on = story.chosen === option.id;
        return (
          <button
            key={option.id ?? "story"}
            type="button"
            aria-pressed={on}
            onClick={() => story.choose(option.id)}
            className={cn(
              "min-h-9 rounded-full border px-3 text-xs font-semibold transition-colors pointer-coarse:min-h-11",
              on ? "border-purple-700 bg-purple-700 text-white" : "border-line-200 bg-card text-ink-700 hover:border-purple-300 hover:bg-purple-50 dark:hover:bg-purple-950/40"
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
