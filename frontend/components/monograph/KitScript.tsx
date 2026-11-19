"use client";

import { useEffect } from "react";

import { MONOGRAPH_KIT_JS } from "@/lib/monographDocument";

export const KIT_SCRIPT_MARK = "data-monograph-kit";

type KitWindow = Window & { KV?: unknown };

export function kitAlreadyBound(view: KitWindow): boolean {
  return view.KV !== undefined;
}

export function KitScript() {
  useEffect(() => {
    if (kitAlreadyBound(window)) {
      window.location.reload();
      return;
    }
    if (document.querySelector(`script[${KIT_SCRIPT_MARK}]`)) return;
    const frame = requestAnimationFrame(() => {
      const script = document.createElement("script");
      script.src = MONOGRAPH_KIT_JS;
      script.async = false;
      script.setAttribute(KIT_SCRIPT_MARK, "");
      document.body.appendChild(script);
    });
    return () => cancelAnimationFrame(frame);
  }, []);
  return null;
}
