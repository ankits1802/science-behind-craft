"use client";

import { useCallback, useEffect, useRef, type RefObject } from "react";

import { focusableIn, MODAL_LAYER_SELECTOR, trapTab } from "@/lib/focusable";
import { lockPageScroll, unlockPageScroll } from "@/lib/scrollLock";

const modalStack: string[] = [];

let lastFocusedOutside: HTMLElement | null = null;
let trackers = 0;

function onDocumentFocusIn(event: FocusEvent) {
  const target = event.target;
  if (!(target instanceof HTMLElement) || target === document.body) return;
  if (target.closest(MODAL_LAYER_SELECTOR)) return;
  lastFocusedOutside = target;
}

function installTracker() {
  trackers += 1;
  if (trackers === 1) document.addEventListener("focusin", onDocumentFocusIn, true);
}

function releaseTracker() {
  trackers = Math.max(0, trackers - 1);
  if (trackers > 0) return;
  document.removeEventListener("focusin", onDocumentFocusIn, true);
  lastFocusedOutside = null;
}

export type ModalFocusOptions = {
  id: string;
  open: boolean;
  panelRef: RefObject<HTMLElement | null>;
  onEscape: () => void;
  canEscape?: boolean;
  initialFocusRef?: RefObject<HTMLElement | null>;
};

export function isTopModal(id: string): boolean {
  return modalStack[modalStack.length - 1] === id;
}

export function useModalFocus({ id, open, panelRef, onEscape, canEscape = true, initialFocusRef }: ModalFocusOptions) {
  const restoreRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    installTracker();
    return releaseTracker;
  }, []);

  useEffect(() => {
    if (!open) return;
    const active = document.activeElement;
    restoreRef.current = active instanceof HTMLElement && active !== document.body ? active : lastFocusedOutside;
    modalStack.push(id);
    lockPageScroll();
    return () => {
      const index = modalStack.lastIndexOf(id);
      if (index >= 0) modalStack.splice(index, 1);
      unlockPageScroll();
      const target = restoreRef.current;
      restoreRef.current = null;
      if (target && document.contains(target)) requestAnimationFrame(() => target.focus({ preventScroll: true }));
    };
  }, [open, id]);

  useEffect(() => {
    if (!open) return;
    const frame = requestAnimationFrame(() => {
      const preferred = initialFocusRef?.current;
      if (preferred && document.contains(preferred)) {
        preferred.focus({ preventScroll: true });
        return;
      }
      const [first] = focusableIn(panelRef.current);
      (first ?? panelRef.current)?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [open, initialFocusRef, panelRef]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape" || !isTopModal(id)) return;
      event.preventDefault();
      event.stopPropagation();
      if (canEscape) onEscape();
    }
    function onFocusIn(event: FocusEvent) {
      const panel = panelRef.current;
      if (!isTopModal(id) || !panel) return;
      if (event.target instanceof Node && panel.contains(event.target)) return;
      const [first] = focusableIn(panel);
      (first ?? panel).focus({ preventScroll: true });
    }
    document.addEventListener("keydown", onKeyDown, true);
    document.addEventListener("focusin", onFocusIn);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      document.removeEventListener("focusin", onFocusIn);
    };
  }, [open, id, canEscape, onEscape, panelRef]);

  return useCallback((event: React.KeyboardEvent<HTMLElement>) => trapTab(event, panelRef.current), [panelRef]);
}
