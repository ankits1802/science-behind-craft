"use client";

import { useEffect, useRef, useSyncExternalStore } from "react";

import { SegmentedChoice } from "@/components/ui/SegmentedChoice";

type PreviewKey = "theme" | "contrast" | "text" | "motion";
type Preview = Record<PreviewKey, string>;

const KEYS: PreviewKey[] = ["theme", "contrast", "text", "motion"];
const ATTRIBUTES: Record<PreviewKey, { name: string; values: Record<string, string> }> = {
  theme: { name: "data-theme", values: { light: "light", dark: "dark" } },
  contrast: { name: "data-high-contrast", values: { standard: "false", high: "true" } },
  text: { name: "data-larger-text", values: { standard: "false", larger: "true" } },
  motion: { name: "data-reduced-motion", values: { full: "false", reduced: "true" } }
};
const QUERIES = { dark: "(prefers-color-scheme: dark)", contrast: "(prefers-contrast: more)", reduced: "(prefers-reduced-motion: reduce)" };
const SERVER_SNAPSHOT = "light|standard|standard|full";

function matches(query: string): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(query).matches;
}

function currentSnapshot(): string {
  const root = document.documentElement;
  const read = (key: PreviewKey) => root.getAttribute(ATTRIBUTES[key].name);
  const theme = read("theme") === "dark" || (read("theme") === null && matches(QUERIES.dark)) ? "dark" : "light";
  const contrast = read("contrast") === "true" || (read("contrast") !== "false" && matches(QUERIES.contrast)) ? "high" : "standard";
  const text = read("text") === "true" ? "larger" : "standard";
  const motion = read("motion") === "true" || matches(QUERIES.reduced) ? "reduced" : "full";
  return [theme, contrast, text, motion].join("|");
}

function subscribe(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: KEYS.map((key) => ATTRIBUTES[key].name) });
  const media = typeof window.matchMedia === "function" ? Object.values(QUERIES).map((query) => window.matchMedia(query)) : [];
  for (const list of media) list.addEventListener("change", onChange);
  return () => {
    observer.disconnect();
    for (const list of media) list.removeEventListener("change", onChange);
  };
}

function parsePreview(snapshot: string): Preview {
  const [theme, contrast, text, motion] = snapshot.split("|");
  return { theme, contrast, text, motion };
}

export function AppearancePreview() {
  const shown = parsePreview(useSyncExternalStore(subscribe, currentSnapshot, () => SERVER_SNAPSHOT));
  const originals = useRef(new Map<string, string | null>());

  useEffect(() => {
    const saved = originals.current;
    return () => {
      const root = document.documentElement;
      for (const [name, value] of saved) {
        if (value === null) root.removeAttribute(name);
        else root.setAttribute(name, value);
      }
      saved.clear();
    };
  }, []);

  const choose = (key: PreviewKey, value: string) => {
    const root = document.documentElement;
    const { name, values } = ATTRIBUTES[key];
    if (!originals.current.has(name)) originals.current.set(name, root.getAttribute(name));
    root.setAttribute(name, values[value]);
  };

  return (
    <div className="grid gap-3 sm:grid-cols-2 rail:grid-cols-4" aria-label="Preview this page" role="group">
      <SegmentedChoice label="Theme" fill value={shown.theme} onChange={(value) => choose("theme", value)} options={[{ value: "light", label: "Light" }, { value: "dark", label: "Dark" }]} />
      <SegmentedChoice label="Contrast" fill value={shown.contrast} onChange={(value) => choose("contrast", value)} options={[{ value: "standard", label: "Standard" }, { value: "high", label: "High" }]} />
      <SegmentedChoice label="Text" fill value={shown.text} onChange={(value) => choose("text", value)} options={[{ value: "standard", label: "Standard" }, { value: "larger", label: "Larger" }]} />
      <SegmentedChoice label="Motion" fill value={shown.motion} onChange={(value) => choose("motion", value)} options={[{ value: "full", label: "Full" }, { value: "reduced", label: "Reduced" }]} />
    </div>
  );
}
