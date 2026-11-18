"use client";

import type { ReactNode } from "react";
import { WifiOff } from "lucide-react";

export function ShellFrame({ nav, onRetry, children }: { nav: ReactNode; onRetry: (() => void) | null; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-ground">
      <a
        href="#main-content"
        className="sr-only start-3 top-3 z-60 rounded-control bg-indigo px-3 py-2 text-ui text-indigo-on focus:not-sr-only focus:fixed"
      >
        Skip to content
      </a>
      {nav}
      <main
        id="main-content"
        tabIndex={-1}
        className="relative mx-auto max-w-7xl px-4 pb-[calc(var(--bottom-nav-h,env(safe-area-inset-bottom,0px))+1.5rem)] pt-[calc(60px+1.25rem)] lg:pb-12 lg:pt-24"
      >
        {onRetry ? <Reconnecting onRetry={onRetry} /> : null}
        {children}
      </main>
    </div>
  );
}

function Reconnecting({ onRetry }: { onRetry: () => void }) {
  return (
    <p role="status" className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-control border border-rule bg-sunk px-3 py-2 text-body-sm text-ink-2" data-testid="reconnecting">
      <span className="inline-flex items-center gap-2">
        <WifiOff className="h-4 w-4 text-ink-3" aria-hidden />
        Connection lost. Retrying…
      </span>
      <button type="button" onClick={onRetry} className="font-semibold text-indigo underline underline-offset-2 hover:text-indigo-hover pointer-coarse:min-h-11">
        Try again
      </button>
    </p>
  );
}
