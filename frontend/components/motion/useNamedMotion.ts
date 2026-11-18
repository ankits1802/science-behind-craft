"use client";

import { useCallback, useRef, type RefObject } from "react";

import { motionAllowedNow } from "@/components/motion/useMotionAllowed";
import { MOTION_CLASS, type NamedMotion } from "@/lib/motion";

export function playMotion(element: HTMLElement | null): boolean {
  if (!element || !motionAllowedNow()) return false;
  element.removeAttribute("data-playing");
  void element.offsetWidth;
  element.setAttribute("data-playing", "");
  element.addEventListener("animationend", () => element.removeAttribute("data-playing"), { once: true });
  return true;
}

export function motionClass(name: NamedMotion): string {
  return MOTION_CLASS[name];
}

export function useNamedMotion<T extends HTMLElement>(): [RefObject<T | null>, () => boolean] {
  const ref = useRef<T | null>(null);
  const play = useCallback(() => playMotion(ref.current), []);
  return [ref, play];
}
