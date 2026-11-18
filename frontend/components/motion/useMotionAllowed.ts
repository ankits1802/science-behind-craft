"use client";

import { useSyncExternalStore } from "react";

import { motionReduced, motionSwitches, REDUCED_MOTION_QUERY } from "@/lib/motion";

function subscribe(onChange: () => void): () => void {
  const media = window.matchMedia(REDUCED_MOTION_QUERY);
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-reduced-motion"] });
  media.addEventListener("change", onChange);
  return () => {
    observer.disconnect();
    media.removeEventListener("change", onChange);
  };
}

function allowedNow(): boolean {
  return !motionReduced(motionSwitches(document.documentElement, window.matchMedia(REDUCED_MOTION_QUERY)));
}

function allowedOnServer(): boolean {
  return false;
}

export function useMotionAllowed(): boolean {
  return useSyncExternalStore(subscribe, allowedNow, allowedOnServer);
}

export function motionAllowedNow(): boolean {
  return typeof window !== "undefined" && allowedNow();
}
