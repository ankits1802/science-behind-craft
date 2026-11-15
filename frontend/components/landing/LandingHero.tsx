"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { BookOpen, FlaskConical, MapPinned } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { BrandMark } from "@/components/BrandMark";
import { riseItem, staggerParent } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { useGsapHeadline } from "@/components/guide/useGsapHeadline";
import { ActionGroup } from "@/components/ui/ActionGroup";

const POINTS = [
  { icon: BookOpen, title: "455 crafts", body: "The IIT master list, searchable by name, region and family." },
  { icon: FlaskConical, title: "The science", body: "Materials, stages and reactions, each claim with its evidence." },
  { icon: MapPinned, title: "The place", body: "Where each craft is practised, on the map of India." }
];

export function LandingHero() {
  const { user } = useAuth();
  const reduce = useAppReducedMotion();
  const headline = useGsapHeadline<HTMLHeadingElement>(reduce);

  return (
    <div className="min-h-dvh bg-bg-0">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5">
        <Link href="/" className="flex items-center gap-2 text-ink-900">
          <BrandMark className="h-9 w-9 rounded-lg" />
          <span className="font-display text-lg font-bold tracking-tight">KalaVigyan</span>
        </Link>
        <Link href={user ? "/ask" : "/login"} className="field-button-secondary">
          {user ? "Open" : "Sign in"}
        </Link>
      </header>

      <main id="main-content" className="mx-auto max-w-6xl px-4 pb-16">
        <section className="surface-dark relative isolate overflow-hidden px-6 py-16 text-center md:px-12 md:py-24">
          <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 grad-mesh opacity-80" />
          <p className="eyebrow text-gold-300!">The science behind craft</p>
          <h1 ref={headline} className="mx-auto mt-4 max-w-3xl font-display text-4xl font-bold leading-tight tracking-tight text-white md:text-5xl">
            Ask how India&apos;s crafts work, and read the sources.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-base leading-7 text-white/75">
            Every sentence carries its citation, the quoted passage and a link to read further.
          </p>
          <ActionGroup className="mt-9">
            {user ? (
              <Link href="/ask" className="field-button">
                Start asking
              </Link>
            ) : (
              <>
                <Link href="/signup" className="field-button">
                  Request access
                </Link>
                <Link href="/login" className="inline-flex min-h-10 items-center justify-center rounded-md border border-white/30 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/10">
                  Sign in
                </Link>
              </>
            )}
          </ActionGroup>
        </section>

        <motion.ul
          variants={staggerParent(reduce)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.3 }}
          className="mt-10 grid gap-4 md:grid-cols-3"
        >
          {POINTS.map((point) => (
            <motion.li key={point.title} variants={riseItem(reduce)} className="panel p-5">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-field-200 text-field-600 dark:text-purple-300">
                <point.icon className="h-5 w-5" aria-hidden />
              </span>
              <h2 className="mt-4 font-display text-lg font-bold text-ink-900">{point.title}</h2>
              <p className="mt-1.5 text-sm leading-6 text-ink-500">{point.body}</p>
            </motion.li>
          ))}
        </motion.ul>

        <footer className="mt-12 flex flex-wrap items-center justify-between gap-3 text-xs text-ink-500">
          <span>KalaVigyan · Science Behind Craft</span>
          <Link href="/privacy" className="hover:text-ink-900">
            Privacy
          </Link>
        </footer>
      </main>
    </div>
  );
}
