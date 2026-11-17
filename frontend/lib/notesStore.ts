import type { NotificationList } from "@/lib/learningContract";

export const NOTES_FRESH_FOR_MS = 60_000;

export type NotesState = { list: NotificationList | null; failure: unknown };
export type HeldNotes = { account: string | null; notes: NotesState };

export const NO_NOTES: NotesState = { list: null, failure: null };

type Listener = (held: HeldNotes) => void;

export type NotesStore = {
  notesOf: (account: string | null) => NotesState;
  due: (account: string) => boolean;
  refresh: (account: string) => Promise<void>;
  refreshHeld: () => Promise<void>;
  subscribe: (listener: Listener) => () => void;
};

export function notesStore(load: () => Promise<NotificationList>, now: () => number = Date.now): NotesStore {
  let held: HeldNotes = { account: null, notes: NO_NOTES };
  let fetchedAt = 0;
  let inFlight: { account: string; done: Promise<void> } | null = null;
  const listeners = new Set<Listener>();

  function adopt(account: string) {
    if (held.account === account) return;
    held = { account, notes: NO_NOTES };
    fetchedAt = 0;
  }

  function settle(account: string, notes: NotesState, at: number | null) {
    if (held.account !== account) return;
    held = { account, notes };
    if (at !== null) fetchedAt = at;
    listeners.forEach((listener) => listener(held));
  }

  function refresh(account: string): Promise<void> {
    adopt(account);
    if (inFlight?.account === account) return inFlight.done;
    const done = load()
      .then((list) => settle(account, { list, failure: null }, now()))
      .catch((failure: unknown) => settle(account, { list: held.notes.list, failure }, null))
      .finally(() => {
        if (inFlight?.done === done) inFlight = null;
      });
    inFlight = { account, done };
    return done;
  }

  return {
    notesOf: (account) => (account !== null && held.account === account ? held.notes : NO_NOTES),
    due: (account) => held.account !== account || now() - fetchedAt > NOTES_FRESH_FOR_MS,
    refresh,
    refreshHeld: () => (held.account === null ? Promise.resolve() : refresh(held.account)),
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    }
  };
}
