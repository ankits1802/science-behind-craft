"use client";

import { createElement, lazy, Suspense, type ComponentType, type ReactNode } from "react";

function NotDrawn() {
  return null;
}

export function lazyBlock<P extends object>(load: () => Promise<ComponentType<P>>, placeholder: ReactNode): ComponentType<P> {
  const Lazy = lazy(() =>
    load()
      .then((component) => ({ default: component }))
      .catch((cause: unknown) => {
        console.error(cause);
        return { default: NotDrawn as ComponentType<P> };
      })
  );
  function LazyBlock(props: P) {
    return <Suspense fallback={placeholder}>{createElement(Lazy as ComponentType<P>, props)}</Suspense>;
  }
  return LazyBlock;
}
