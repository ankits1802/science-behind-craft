"use client";

import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

import { stackNotes, type MarginNote } from "@/lib/marginNotes";
import { cn } from "@/lib/utils";

function usePlacedNotes(notes: readonly MarginNote[]) {
  const list = useRef<HTMLOListElement | null>(null);
  const [tops, setTops] = useState<number[] | null>(null);
  useLayoutEffect(() => {
    const rail = list.current;
    if (!rail) return;
    const measure = () => {
      if (rail.getBoundingClientRect().width === 0) return setTops(null);
      const origin = rail.getBoundingClientRect().top;
      const items = Array.from(rail.children) as HTMLElement[];
      const wanted = notes.map((note) => (document.getElementById(note.anchorId)?.getBoundingClientRect().top ?? origin) - origin);
      setTops(stackNotes(wanted, items.map((item) => item.offsetHeight)));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(rail);
    if (rail.parentElement) observer.observe(rail.parentElement);
    return () => observer.disconnect();
  }, [notes]);
  return { list, tops };
}

export function MarginNotes({ notes, label = "Sources in this chapter" }: { notes: readonly MarginNote[]; label?: string }) {
  const { list, tops } = usePlacedNotes(notes);
  const height = tops && tops.length > 0 ? tops[tops.length - 1] + 64 : undefined;
  return (
    <ol ref={list} aria-label={label} className="kv-notes relative grid gap-2" style={tops ? { height, display: "block" } : undefined} data-testid="margin-notes">
      {notes.map((note, index) => (
        <li key={note.number} style={tops ? { position: "absolute", insetInline: 0, top: tops[index] } : undefined}>
          <b>{note.number}</b>
          <span>
            {note.title}
            {note.year ? `, ${note.year}` : ""}
          </span>
        </li>
      ))}
    </ol>
  );
}

export function Spread({ rail, margin, children, className }: { rail?: ReactNode; margin?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div data-spread="" className={cn("kv-spread", className)}>
      {rail ? <div className="kv-spread-rail">{rail}</div> : null}
      <div className="kv-spread-main">{children}</div>
      {margin ? (
        <div className="kv-spread-margin" data-margin-rail="">
          {margin}
        </div>
      ) : null}
    </div>
  );
}
