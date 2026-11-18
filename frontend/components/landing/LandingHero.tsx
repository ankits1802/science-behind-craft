"use client";

import Link from "next/link";

import { useAuth } from "@/components/AuthProvider";
import { BrandLockup } from "@/components/BrandMark";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { buttonLook } from "@/components/ui/button";

const LANDING_POINTS = [
  { title: "The crafts", body: "The IIT master list, searchable by name, region and family." },
  { title: "The science", body: "Materials, stages and reactions, each claim with its evidence." },
  { title: "The place", body: "Where each craft is practised, on the map of India." }
];

function craftCountLine(craftCount: number | null): string | null {
  if (craftCount === null) return null;
  return `${craftCount} ${craftCount === 1 ? "craft" : "crafts"}`;
}

export function LandingHero({ craftCount }: { craftCount: number | null }) {
  const { user } = useAuth();
  const count = craftCountLine(craftCount);

  return (
    <div className="min-h-dvh bg-ground">
      <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-5">
        <Link href="/" className="flex items-center text-ink-1">
          <BrandLockup />
        </Link>
        {count ? <p className="font-ui text-ui text-ink-3 tabular-nums">{count}</p> : null}
      </header>

      <main id="main-content" className="mx-auto max-w-6xl px-4 pb-16">
        <section className="surface-dark relative isolate overflow-hidden px-6 py-16 text-center md:px-12 md:py-24">
          <p className="kicker">The science behind craft</p>
          <h1 className="mx-auto mt-4 max-w-3xl font-headline text-h1 text-ink-1">
            Ask how India&apos;s crafts work, and read the sources.
          </h1>
          <p className="mx-auto mt-5 max-w-xl font-reading text-lede text-ink-2">
            Every sentence carries its citation, the quoted passage and a link to read further.
          </p>
          <ActionGroup className="mt-9">
            {user ? (
              <Link href="/ask" {...buttonLook({ variant: "primary" })}>
                Start asking
              </Link>
            ) : (
              <>
                <Link href="/signup" {...buttonLook({ variant: "primary" })}>
                  Request access
                </Link>
                <Link href="/login" {...buttonLook({ variant: "quiet" })}>
                  Sign in
                </Link>
              </>
            )}
          </ActionGroup>
        </section>

        <ul className="mt-10 grid gap-x-10 gap-y-6 md:grid-cols-3">
          {LANDING_POINTS.map((point) => (
            <li key={point.title} className="border-t border-rule pt-4">
              <h2 className="font-ui text-h4 text-ink-1">{point.title}</h2>
              <p className="mt-1.5 font-ui text-ui text-ink-2">{point.body}</p>
            </li>
          ))}
        </ul>

        <footer className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t border-rule pt-4 font-ui text-caption text-ink-3">
          <span>KalaVigyan · Science Behind Craft</span>
          <Link href="/privacy" className="kv-link font-normal">
            Privacy
          </Link>
        </footer>
      </main>
    </div>
  );
}
