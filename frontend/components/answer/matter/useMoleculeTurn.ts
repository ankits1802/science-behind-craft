"use client";

import { useEffect, useState, type FocusEvent, type RefObject } from "react";

import { useMotionAllowed } from "@/components/motion/useMotionAllowed";
import type { MoleculeScene } from "@/lib/moleculeViewer";
import { IN_VIEW_MARGIN } from "@/lib/playInView";

export type MoleculeHold = { exploring: boolean; hovered: boolean; focused: boolean };
export type MoleculeTurn = {
  turning: boolean;
  wanted: boolean;
  motion: boolean;
  toggle: () => void;
  holds: { onPointerEnter: () => void; onPointerLeave: () => void; onFocus: () => void; onBlur: (event: FocusEvent<HTMLElement>) => void };
};

export function moleculeTurns(motion: boolean, wanted: boolean, seen: boolean, hold: MoleculeHold): boolean {
  return motion && wanted && seen && !hold.exploring && !hold.hovered && !hold.focused;
}

function useSeen(watched: RefObject<Element | null>): boolean {
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const node = watched.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => setSeen(entry.isIntersecting)), { rootMargin: IN_VIEW_MARGIN });
    observer.observe(node);
    return () => observer.disconnect();
  }, [watched]);
  return seen;
}

export function useMoleculeTurn(scene: MoleculeScene | null, watched: RefObject<Element | null>, exploring: boolean, quarter: () => void): MoleculeTurn {
  const motion = useMotionAllowed();
  const seen = useSeen(watched);
  const [wanted, setWanted] = useState(true);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const turning = scene !== null && moleculeTurns(motion, wanted, seen, { exploring, hovered, focused });

  useEffect(() => {
    if (!scene || !turning) return;
    scene.spin(true);
    return () => scene.spin(false);
  }, [scene, turning]);

  const toggle = () => (motion ? setWanted((now) => !now) : quarter());
  const holds = {
    onPointerEnter: () => setHovered(true),
    onPointerLeave: () => setHovered(false),
    onFocus: () => setFocused(true),
    onBlur: (event: FocusEvent<HTMLElement>) => setFocused(event.currentTarget.contains(event.relatedTarget as Node | null))
  };
  return { turning, wanted, motion, toggle, holds };
}
