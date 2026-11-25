"use client";

import { useLayoutEffect, useMemo, useRef, useState } from "react";

import { useFrameLook } from "@/components/answer/play/useFrameLook";
import { SANDBOX_ATTRIBUTE, type SimulationBlock } from "@/lib/explainerPlay";
import { FRAME_DEFAULT_HEIGHT, NO_PIECES, ownFrameHeight, sandboxDocument, type FramePieces } from "@/lib/sandboxFrame";

type FrameProps = { block: Pick<SimulationBlock, "title" | "html" | "values">; pieces?: FramePieces; startHeight?: number };

export function SandboxFrame({ block, pieces = NO_PIECES, startHeight = FRAME_DEFAULT_HEIGHT }: FrameProps) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(startHeight);
  const look = useFrameLook(block.html);
  const srcDoc = useMemo(() => sandboxDocument(block.html, block.values, look, pieces), [block.html, block.values, look, pieces]);

  useLayoutEffect(() => {
    const listen = (event: MessageEvent) => {
      const next = ownFrameHeight(event, frame.current?.contentWindow);
      if (next !== null) setHeight(next);
    };
    window.addEventListener("message", listen);
    return () => window.removeEventListener("message", listen);
  }, []);

  return (
    <iframe
      ref={frame}
      sandbox={SANDBOX_ATTRIBUTE}
      srcDoc={srcDoc}
      title={block.title}
      className="block w-full min-w-0 max-w-full rounded-plate border border-rule bg-sunk"
      style={{ height }}
      data-testid="sandbox-frame"
    />
  );
}
