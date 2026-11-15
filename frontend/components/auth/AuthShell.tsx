"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { BrandMark } from "@/components/BrandMark";
import { GLASS_PANEL, GlassSurface } from "@/components/ui/GlassSurface";

const BRAND_POINTS = [
  "455 crafts from the IIT master list, each on the map of India.",
  "Materials, process stages and the chemistry at every stage.",
  "Every sentence cited, with the quoted passage and a link out."
];

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[43%_57%]">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-purple-950 p-10 lg:flex">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div
            className="absolute -left-24 -top-24 h-96 w-96 rounded-full opacity-70"
            style={{ background: "radial-gradient(circle, oklch(0.47 0.198 305 / 0.5), transparent 62%)" }}
          />
          <div
            className="absolute -bottom-28 -right-16 h-104 w-104 rounded-full opacity-40"
            style={{ background: "radial-gradient(circle, oklch(0.7 0.145 80 / 0.25), transparent 60%)" }}
          />
        </div>
        <Link href="/" className="relative z-10 flex items-center gap-3">
          <BrandMark className="h-12 w-12 rounded-xl shadow-md" />
          <span className="font-display text-xl font-bold tracking-tight text-white">KalaVigyan</span>
        </Link>
        <div className="relative z-10">
          <p className="eyebrow text-gold-300!">The science behind craft</p>
          <h2 className="mt-3 font-display text-3xl font-bold leading-snug tracking-tight text-white">
            Every craft is a <span className="text-gold-gradient">working science</span>.
          </h2>
          <ul className="mt-8 space-y-4">
            {BRAND_POINTS.map((point) => (
              <li key={point} className="flex gap-3 text-sm leading-relaxed text-white/75">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-gold-400" aria-hidden />
                {point}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative z-10 text-xs text-white/40">An administrator approves each new account.</p>
      </aside>

      <main id="main-content" className="relative flex items-center justify-center overflow-hidden bg-bg-0 px-4 py-6 md:px-10">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="absolute inset-0 grad-mesh opacity-60" />
          <div className="absolute -left-16 top-12 h-72 w-72 rounded-full bg-purple-300/30 blur-3xl" />
          <div className="absolute -right-12 bottom-8 h-80 w-80 rounded-full bg-amber-500/15 blur-3xl" />
        </div>

        <GlassSurface options={GLASS_PANEL} className="glass-card relative z-10 w-full max-w-md rounded-xl p-6 shadow-lg md:p-8">
          <div className="mb-6 flex flex-col items-center gap-2 text-center">
            <BrandMark className="h-12 w-12 rounded-xl shadow-sm lg:hidden" />
            <h1 className="font-display text-2xl font-bold text-ink-900">{title}</h1>
            <p className="text-sm text-ink-500">{subtitle}</p>
          </div>
          {children}
        </GlassSurface>
      </main>
    </div>
  );
}

export function OrDivider() {
  return (
    <div className="my-4 flex items-center gap-3">
      <span className="h-px flex-1 bg-line-200" />
      <span className="text-sm text-ink-300">OR</span>
      <span className="h-px flex-1 bg-line-200" />
    </div>
  );
}
