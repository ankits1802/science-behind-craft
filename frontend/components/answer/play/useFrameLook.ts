"use client";

import { useMemo, useSyncExternalStore } from "react";

import { motionAllowedNow } from "@/components/motion/useMotionAllowed";
import { REDUCED_MOTION_QUERY } from "@/lib/motion";
import { frameTokenNames, readFrameLook, type FrameLook } from "@/lib/sandboxFrame";

const WATCHED = ["data-theme", "data-high-contrast", "data-reduced-motion"];
const QUERIES = [REDUCED_MOTION_QUERY, "(prefers-color-scheme: dark)", "(prefers-contrast: more)"];

function subscribe(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: WATCHED });
  const media = QUERIES.map((query) => window.matchMedia(query));
  for (const list of media) list.addEventListener("change", onChange);
  return () => {
    observer.disconnect();
    for (const list of media) list.removeEventListener("change", onChange);
  };
}

function lookNow(names: readonly string[]): string {
  const style = getComputedStyle(document.documentElement);
  return JSON.stringify(readFrameLook(names, (name) => style.getPropertyValue(name), !motionAllowedNow()));
}

export function useFrameLook(html: string): FrameLook | null {
  const names = useMemo(() => frameTokenNames(html), [html]);
  const look = useSyncExternalStore(
    subscribe,
    () => lookNow(names),
    () => null
  );
  return useMemo(() => (look === null ? null : (JSON.parse(look) as FrameLook)), [look]);
}
