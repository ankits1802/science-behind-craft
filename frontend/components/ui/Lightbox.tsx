"use client";

import { Minus, Plus, X } from "lucide-react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { useModalFocus } from "@/components/hooks/useModalFocus";
import { IconButton } from "@/components/ui/IconButton";
import { useZoom } from "@/components/ui/useZoom";

export type LightboxPicture = { src: string; alt: string; width?: number; height?: number; caption: ReactNode; credit: ReactNode };

export function Lightbox({ picture, open, onClose }: { picture: LightboxPicture; open: boolean; onClose: () => void }) {
  const id = useId();
  const titleId = `${id}-caption`;
  const panelRef = useRef<HTMLDivElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const [mounted, setMounted] = useState(false);
  const { zoom, step, reset, handlers } = useZoom();
  useEffect(() => setMounted(true), []);
  useEffect(() => {
    if (!open) reset();
  }, [open, reset]);
  const onKeyDown = useModalFocus({ id, open, panelRef, onEscape: onClose, initialFocusRef: closeRef });

  if (!mounted || !open) return null;

  return createPortal(
    <div ref={panelRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} data-modal-layer="" onKeyDown={onKeyDown} className="kv-lightbox outline-hidden">
      <div className="flex items-center justify-end gap-2 p-3">
        <IconButton label="Zoom out" icon={<Minus />} onPhoto edge onClick={() => step(1 / 1.25)} disabled={zoom.scale <= 1} />
        <IconButton label="Zoom in" icon={<Plus />} onPhoto edge onClick={() => step(1.25)} disabled={zoom.scale >= 4} />
        <IconButton ref={closeRef} label="Close" icon={<X />} onPhoto edge onClick={onClose} />
      </div>
      <div className="relative min-h-0 touch-none overflow-hidden" {...handlers}>
        <img
          src={picture.src}
          alt={picture.alt}
          width={picture.width}
          height={picture.height}
          referrerPolicy="no-referrer"
          draggable={false}
          className="mx-auto h-full w-auto max-w-full object-contain select-none"
          style={{ transform: `translate(${zoom.x}px, ${zoom.y}px) scale(${zoom.scale})` }}
        />
      </div>
      <div className="mx-auto w-full max-w-measure px-4 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <p id={titleId} className="font-reading text-figcaption italic">
          {picture.caption}
        </p>
        <p className="kv-lightbox-credit mt-2 font-ui text-caption">{picture.credit}</p>
      </div>
    </div>,
    document.body
  );
}
