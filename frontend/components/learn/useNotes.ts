"use client";

import { useEffect, useState } from "react";

import { fetchNotifications, markAllNotesRead, markNoteRead } from "@/lib/learningApi";
import { NO_NOTES, notesStore, type HeldNotes, type NotesState } from "@/lib/notesStore";

export type { NotesState } from "@/lib/notesStore";

const store = notesStore(fetchNotifications);

export function refreshNotes(): Promise<void> {
  return store.refreshHeld();
}

export async function readNote(id: string): Promise<void> {
  await markNoteRead(id);
  await store.refreshHeld();
}

export async function readAllNotes(): Promise<void> {
  await markAllNotesRead();
  await store.refreshHeld();
}

export function useNotes(account: string | null): NotesState {
  const [held, setHeld] = useState<HeldNotes>(() => ({ account, notes: store.notesOf(account) }));

  useEffect(() => {
    if (account === null) return;
    const unsubscribe = store.subscribe(setHeld);
    setHeld({ account, notes: store.notesOf(account) });
    if (store.due(account)) void store.refresh(account);
    const onFocus = () => {
      if (store.due(account)) void store.refresh(account);
    };
    window.addEventListener("focus", onFocus);
    return () => {
      unsubscribe();
      window.removeEventListener("focus", onFocus);
    };
  }, [account]);

  return account !== null && held.account === account ? held.notes : NO_NOTES;
}
