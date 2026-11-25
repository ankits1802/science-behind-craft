"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { SandboxFrame } from "@/components/answer/play/SandboxFrame";
import { codedFrameHtml, codedFramePieces, type MapBase } from "@/lib/codedFigureFrame";
import { codedValues, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";

import { codedMapBase } from "./codedMapBase";
import { CodedStill } from "./CodedStill";

export type CodedFrameProps = { title: string; figure: CodedFigureSpec; words: Readonly<Record<string, string>>; live?: boolean };

type Base = { ready: boolean; base: MapBase | null };

function useMapBase(figure: CodedFigureSpec, wanted: boolean): Base {
  const map = figure.map;
  const [loaded, setLoaded] = useState<Base>({ ready: !map, base: null });
  useEffect(() => {
    if (!map || !wanted) return;
    let current = true;
    codedMapBase(map).then(
      (base) => current && setLoaded({ ready: true, base }),
      () => current && setLoaded({ ready: false, base: null })
    );
    return () => {
      current = false;
    };
  }, [map, wanted]);
  return loaded;
}

function LiveFrame({ title, figure, words, height, base }: Omit<CodedFrameProps, "live"> & { height: number; base: MapBase | null }) {
  const block = useMemo(() => ({ title, html: codedFrameHtml(figure), values: codedValues(figure) }), [title, figure]);
  const pieces = useMemo(() => codedFramePieces({ origin: window.location.origin, figure, words, base }), [figure, words, base]);
  return <SandboxFrame block={block} pieces={pieces} startHeight={height} />;
}

export function CodedFrame({ title, figure, words, live = true }: CodedFrameProps) {
  const holder = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | null>(null);
  const base = useMapBase(figure, live);
  useEffect(() => {
    if (live) setHeight(Math.max(1, Math.round(holder.current?.getBoundingClientRect().height ?? 0)));
  }, [live]);
  const running = live && height !== null && base.ready;
  return (
    <div ref={holder} className="min-w-0" data-coded-frame={running ? "live" : "still"}>
      {running ? <LiveFrame title={title} figure={figure} words={words} height={height} base={base.base} /> : <CodedStill figure={figure} words={words} />}
    </div>
  );
}
