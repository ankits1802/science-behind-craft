"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { SandboxFrame } from "@/components/answer/play/SandboxFrame";
import { clipAddresses, clipEnds, clipLinks, type HeldClips } from "@/lib/codedClips";
import { codedFrameHtml, codedFramePieces, type MapBase } from "@/lib/codedFigureFrame";
import { clipFilms, codedValues, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";

import { codedMapBase } from "./codedMapBase";
import { CodedStill } from "./CodedStill";
import { useClipRenewal } from "./useClipRenewal";

export type CodedFrameProps = { title: string; figure: CodedFigureSpec; words: Readonly<Record<string, string>>; live?: boolean };

type Base = { ready: boolean; base: MapBase | null };
type Clips = { ready: boolean; links: HeldClips };

const NO_CLIPS: HeldClips = {};

function useMapBase(figure: CodedFigureSpec, wanted: boolean): Base {
  const map = figure.map;
  const [loaded, setLoaded] = useState<Base>({ ready: !map, base: null });
  useEffect(() => {
    if (!map || !wanted) return;
    let current = true;
    codedMapBase(map, figure.base).then(
      (base) => current && setLoaded({ ready: true, base }),
      () => current && setLoaded({ ready: false, base: null })
    );
    return () => {
      current = false;
    };
  }, [map, wanted, figure.base]);
  return loaded;
}

function useClipLinks(figure: CodedFigureSpec, wanted: boolean): Clips {
  const clipped = clipFilms(figure).length > 0;
  const [loaded, setLoaded] = useState<Clips>({ ready: !clipped, links: NO_CLIPS });
  useEffect(() => {
    if (!clipped || !wanted) return;
    let current = true;
    clipLinks(figure).then((links) => current && setLoaded({ ready: true, links }));
    return () => {
      current = false;
    };
  }, [figure, clipped, wanted]);
  return loaded;
}

type LiveProps = Omit<CodedFrameProps, "live"> & { height: number; base: MapBase | null; clips: HeldClips };

function LiveFrame({ title, figure, words, height, base, clips }: LiveProps) {
  const block = useMemo(() => ({ title, html: codedFrameHtml(figure), values: codedValues(figure) }), [title, figure]);
  const pieces = useMemo(() => codedFramePieces({ origin: window.location.origin, figure, words, base, clips: clipAddresses(clips), ends: clipEnds(clips) }), [figure, words, base, clips]);
  return <SandboxFrame block={block} pieces={pieces} startHeight={height} />;
}

export function CodedFrame({ title, figure, words, live = true }: CodedFrameProps) {
  const holder = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | null>(null);
  const base = useMapBase(figure, live);
  const clips = useClipLinks(figure, live);
  useEffect(() => {
    if (live) setHeight(Math.max(1, Math.round(holder.current?.getBoundingClientRect().height ?? 0)));
  }, [live]);
  const running = live && height !== null && base.ready && clips.ready;
  useClipRenewal(holder, figure, running ? clips.links : NO_CLIPS);
  return (
    <div ref={holder} className="min-w-0" data-coded-frame={running ? "live" : "still"}>
      {running ? <LiveFrame title={title} figure={figure} words={words} height={height} base={base.base} clips={clips.links} /> : <CodedStill figure={figure} words={words} />}
    </div>
  );
}
