"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

import { riseItem, staggerParent } from "@/components/guide/guideMotion";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { formatDate } from "@/lib/format";
import type { Notification } from "@/lib/learningContract";
import { explainerHref, newsText, notesCapText, NOTE_TITLE } from "@/lib/savedView";
import { cn } from "@/lib/utils";

export type NotesActions = { busy: string | null; onUpdate: (note: Notification) => void; onRead: (note: Notification) => void };

function NoteCard({ note, actions, reduce }: { note: Notification; actions: NotesActions; reduce: boolean }) {
  const unread = note.readAt === null;
  const { payload } = note;
  return (
    <motion.li
      variants={riseItem(reduce, 10)}
      className={cn("panel grid min-w-0 gap-3 p-4 md:p-5", unread && "border-purple-300 dark:border-purple-800")}
      data-testid="note"
      data-unread={unread ? "true" : "false"}
    >
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200">
          <Sparkles className="h-4 w-4" aria-hidden />
        </span>
        <h3 className="min-w-0 font-display text-base font-bold text-ink-900">{NOTE_TITLE}</h3>
        {unread ? <span className="rounded-full bg-purple-700 px-2 py-0.5 text-[11px] font-semibold text-white">New</span> : null}
        <span className="ml-auto text-xs text-ink-500">{formatDate(note.createdAt)}</span>
      </div>
      <Link href={explainerHref(payload.explainerId)} className="min-w-0 break-words text-sm font-semibold text-ink-900 underline-offset-2 hover:text-purple-700 hover:underline">
        {payload.question}
      </Link>
      <p className="text-sm text-ink-700">
        <span className="font-medium">{payload.craft.name}</span>
        <span className="text-ink-500"> · </span>
        <span data-testid="note-news">{newsText(payload.news)}</span>
      </p>
      <ActionGroup align="start">
        <button type="button" className="field-button" disabled={actions.busy !== null} onClick={() => actions.onUpdate(note)} data-testid="note-update">
          Update the answer
        </button>
        {unread ? (
          <button type="button" className="field-button-secondary" disabled={actions.busy !== null} onClick={() => actions.onRead(note)} data-testid="note-read">
            Mark read
          </button>
        ) : null}
      </ActionGroup>
    </motion.li>
  );
}

export function NotesInbox({ notes, actions, reduce }: { notes: readonly Notification[]; actions: NotesActions; reduce: boolean }) {
  if (notes.length === 0) {
    return (
      <p className="panel p-5 text-sm text-ink-500" data-testid="notes-empty">
        Nothing new yet.
      </p>
    );
  }
  const cap = notesCapText(notes.length);
  return (
    <>
      <motion.ul variants={staggerParent(reduce)} initial="hidden" animate="show" className="grid min-w-0 gap-3" data-testid="notes">
        {notes.map((note) => (
          <NoteCard key={note.id} note={note} actions={actions} reduce={reduce} />
        ))}
      </motion.ul>
      {cap ? <p className="text-xs text-ink-500">{cap}</p> : null}
    </>
  );
}
