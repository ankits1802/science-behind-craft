"use client";

import type { ReactNode } from "react";
import { WifiOff } from "lucide-react";

import { InstitutionFooter } from "@/components/landing/Footer";

export function SkipLink() {
  return (
    <a href="#main-content" className="sr-only start-3 top-3 z-skip rounded-control bg-indigo px-3 py-2 text-ui text-indigo-on focus:not-sr-only focus:fixed">
      Skip to content
    </a>
  );
}

export function ShellFrame({ nav, onRetry, children }: { nav: ReactNode; onRetry: (() => void) | null; children: ReactNode }) {
  return (
    <div className="kv-shell">
      <SkipLink />
      {nav}
      <main id="main-content" tabIndex={-1} className="kv-shell-main kv-shell-wrap">
        {onRetry ? <Reconnecting onRetry={onRetry} /> : null}
        {children}
      </main>
      <InstitutionFooter />
    </div>
  );
}

function Reconnecting({ onRetry }: { onRetry: () => void }) {
  return (
    <p role="status" className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-control border border-rule bg-sunk px-3 py-2 font-ui text-body-sm text-ink-2" data-testid="reconnecting">
      <span className="inline-flex items-center gap-2">
        <WifiOff className="h-4 w-4 text-ink-3" aria-hidden />
        Connection lost. Retrying…
      </span>
      <button type="button" onClick={onRetry} className="kv-link pointer-coarse:min-h-11">
        Try again
      </button>
    </p>
  );
}
