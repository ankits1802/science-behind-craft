import type { TargetAndTransition, Transition, Variants } from "framer-motion";

export const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function springy(reduce: boolean): Transition {
  return reduce ? { duration: 0 } : { type: "spring", stiffness: 380, damping: 30, mass: 0.7 };
}

export function layoutSpring(reduce: boolean): Transition {
  return reduce ? { duration: 0 } : { type: "spring", stiffness: 260, damping: 32, mass: 0.9 };
}

export function cameraMove(reduce: boolean): Transition {
  return reduce ? { duration: 0 } : { duration: 1.6, ease: EASE_OUT, delay: 0.3 };
}

export function zoomThrough(reduce: boolean): Variants {
  return {
    hidden: { opacity: 0, scale: reduce ? 1 : 0.9 },
    show: { opacity: 1, scale: 1, transition: { duration: reduce ? 0 : 0.5, ease: EASE_OUT } },
    exit: { opacity: 0, scale: reduce ? 1 : 1.12, transition: { duration: reduce ? 0 : 0.28, ease: "easeIn" } }
  };
}

export function staggerParent(reduce: boolean, stagger = 0.06): Variants {
  return {
    hidden: {},
    show: {
      transition: reduce ? { duration: 0 } : { staggerChildren: stagger, delayChildren: 0.05 }
    }
  };
}

export function riseItem(reduce: boolean, distance = 14): Variants {
  return {
    hidden: { opacity: 0, y: reduce ? 0 : distance },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: reduce ? 0 : 0.5, ease: EASE_OUT }
    }
  };
}

export function slideItem(reduce: boolean, distance = 12): Variants {
  return {
    hidden: { opacity: 0, x: reduce ? 0 : -distance },
    show: {
      opacity: 1,
      x: 0,
      transition: { duration: reduce ? 0 : 0.4, ease: EASE_OUT }
    }
  };
}

export function scrollToStep(id: string, reduce: boolean): void {
  if (typeof document === "undefined") return;
  document.getElementById(id)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
}

export function soundBar(reduce: boolean, index: number): { animate: TargetAndTransition } {
  if (reduce) return { animate: { scaleY: 0.64, transition: { duration: 0 } } };
  return { animate: { scaleY: [0.27, 1, 0.27], transition: { duration: 0.9, ease: "easeInOut", repeat: Infinity, delay: index * 0.15 } } };
}

export function swapVariants(reduce: boolean): Variants {
  return {
    hidden: { opacity: 0, y: reduce ? 0 : 8 },
    show: { opacity: 1, y: 0, transition: { duration: reduce ? 0 : 0.28, ease: EASE_OUT } },
    exit: { opacity: 0, y: reduce ? 0 : -8, transition: { duration: reduce ? 0 : 0.16, ease: "easeIn" } }
  };
}
