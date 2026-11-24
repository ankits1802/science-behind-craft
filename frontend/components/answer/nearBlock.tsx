"use client";

import { createElement, Suspense, use, useEffect, useRef, useState, type ComponentType, type ReactNode } from "react";

import { BlockBoundary, retryableLazy } from "@/components/answer/lazyBlock";

export const NEAR_MARGIN = "200% 0px";
export const NEAR_ATTRIBUTE = "data-kv-near";

export type NearSignal = { reached: boolean; promise: Promise<void>; reach: () => void };
export type NearEntry = Pick<IntersectionObserverEntry, "isIntersecting">;
export type NearObserver = Pick<IntersectionObserver, "observe" | "disconnect">;
export type NearObserverMaker = (seen: (entries: readonly NearEntry[]) => void, options: IntersectionObserverInit) => NearObserver;

export function nearSignal(reached: boolean): NearSignal {
  let release: () => void = () => undefined;
  const promise = new Promise<void>((resolve) => {
    release = resolve;
  });
  const signal: NearSignal = {
    reached,
    promise,
    reach: () => {
      signal.reached = true;
      release();
    }
  };
  if (reached) release();
  return signal;
}

function browserObserver(): NearObserverMaker | null {
  if (typeof IntersectionObserver === "undefined") return null;
  return (seen, options) => new IntersectionObserver((entries) => seen(entries), options);
}

export function whenNear(element: Element | null, reach: () => void, make: NearObserverMaker | null = browserObserver()): () => void {
  if (!element || !make) {
    reach();
    return () => undefined;
  }
  const observer = make(
    (entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      reach();
    },
    { rootMargin: NEAR_MARGIN }
  );
  observer.observe(element);
  return () => observer.disconnect();
}

function NearGate({ signal, children }: { signal: NearSignal; children: ReactNode }) {
  if (!signal.reached) use(signal.promise);
  return children;
}

const onServer = () => typeof window === "undefined";
const RAISED_WHEN_DRAWN = () => undefined;
const SERVER_LOADS: Promise<void>[] = [];

export function nearBlocksLoaded(): Promise<void> {
  return Promise.all(SERVER_LOADS).then(() => undefined);
}

export function nearBlock<P extends object>(load: () => Promise<ComponentType<P>>, reserve: ReactNode): ComponentType<P> {
  const loader = retryableLazy(load);
  let ready: ComponentType<P> | null = null;
  const keep = (view: ComponentType<P>) => {
    ready = view;
  };
  if (onServer()) SERVER_LOADS.push(load().then(keep, RAISED_WHEN_DRAWN));
  function NearBlock(props: P) {
    const holder = useRef<HTMLDivElement | null>(null);
    const [signal] = useState(() => nearSignal(onServer()));
    const [drawn, setDrawn] = useState(() => ({ round: 0, Lazy: loader.current() }));
    useEffect(() => whenNear(holder.current, signal.reach), [signal]);
    const retry = () => setDrawn({ round: drawn.round + 1, Lazy: loader.retry(drawn.Lazy) });
    const View = onServer() && ready ? ready : drawn.Lazy;
    return (
      <div ref={holder} data-kv-near="">
        <BlockBoundary key={drawn.round} onRetry={retry}>
          <Suspense fallback={reserve}>
            <NearGate signal={signal}>{createElement(View, props)}</NearGate>
          </Suspense>
        </BlockBoundary>
      </div>
    );
  }
  return NearBlock;
}
