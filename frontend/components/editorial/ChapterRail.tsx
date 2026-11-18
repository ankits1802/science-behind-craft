"use client";

import { useEffect, useState } from "react";

import { motionAllowedNow } from "@/components/motion/useMotionAllowed";
import { chapterFromQuery, currentChapter, type Chapter } from "@/lib/chapters";

const NO_ALIASES: Readonly<Record<string, string>> = {};

function railLine(): number {
  const rail = document.querySelector<HTMLElement>("[data-chapter-rail]");
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
  return (rail?.offsetHeight ?? 0) + rem;
}

function useChapterInView(chapters: readonly Chapter[]): string | null {
  const [current, setCurrent] = useState<string | null>(chapters[0]?.id ?? null);
  useEffect(() => {
    let frame = 0;
    const measure = () => {
      frame = 0;
      const tops = chapters.flatMap((chapter) => {
        const node = document.getElementById(chapter.id);
        return node ? [{ id: chapter.id, top: node.getBoundingClientRect().top }] : [];
      });
      setCurrent(currentChapter(tops, railLine()));
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(measure);
    };
    measure();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [chapters]);
  return current;
}

export function ChapterRail({ chapters, label = "Chapters", aliases = NO_ALIASES }: { chapters: readonly Chapter[]; label?: string; aliases?: Readonly<Record<string, string>> }) {
  const current = useChapterInView(chapters);

  useEffect(() => {
    if (window.location.hash) return;
    const target = chapterFromQuery(window.location.search, aliases, chapters);
    if (target) document.getElementById(target)?.scrollIntoView({ behavior: motionAllowedNow() ? "smooth" : "auto", block: "start" });
  }, [aliases, chapters]);

  return (
    <nav aria-label={label} className="kv-chapters" data-chapter-rail="" data-testid="chapter-rail">
      <ol>
        {chapters.map((chapter, index) => (
          <li key={chapter.id}>
            <a href={`#${chapter.id}`} aria-current={chapter.id === current ? "location" : undefined}>
              <b>{index + 1}</b>
              {chapter.label}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
