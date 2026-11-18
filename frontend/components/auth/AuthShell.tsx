"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { BrandLockup } from "@/components/BrandMark";

const BRAND_POINTS = [
  "Every craft on the IIT master list, each on the map of India.",
  "Materials, process stages and the chemistry at every stage.",
  "Every sentence cited, with the quoted passage and a link out."
];

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[43%_57%]">
      <aside className="hidden flex-col justify-between border-e border-rule bg-sunk p-10 lg:flex">
        <Link href="/" className="flex items-center text-ink-1">
          <BrandLockup />
        </Link>
        <div>
          <p className="kicker">The science behind craft</p>
          <h2 className="mt-3 font-headline text-h2 text-ink-1">Every craft is a working science.</h2>
          <ul className="mt-8 space-y-4">
            {BRAND_POINTS.map((point) => (
              <li key={point} className="flex gap-3 text-ui text-ink-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-ink-3" aria-hidden />
                {point}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-caption text-ink-3">An administrator approves each new account.</p>
      </aside>

      <main id="main-content" className="flex items-center justify-center bg-ground px-4 py-6 md:px-10">
        <div className="w-full max-w-md rounded-card border border-rule bg-raised p-6 md:p-8">
          <div className="mb-6 flex flex-col items-center gap-2 text-center">
            <BrandLockup compact className="lg:hidden" />
            <h1 className="font-headline text-h3 text-ink-1">{title}</h1>
            <p className="text-ui text-ink-3">{subtitle}</p>
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}

export function OrDivider() {
  return (
    <div className="my-4 flex items-center gap-3">
      <span className="h-px flex-1 bg-rule" />
      <span className="text-ui text-ink-3">OR</span>
      <span className="h-px flex-1 bg-rule" />
    </div>
  );
}
