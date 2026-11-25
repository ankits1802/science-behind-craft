import type { ReactNode } from "react";

import type { NoteLine } from "@/lib/monographNotes";

export function noteText(note: NoteLine): string {
  return note.year === null ? note.title : `${note.title}, ${note.year}`;
}

export function NoteList({ notes, label, children = null }: { notes: readonly NoteLine[]; label: string; children?: ReactNode }) {
  if (!notes.length && !children) return null;
  return (
    <aside className={children ? "margin note keep" : "margin note"} aria-label={label}>
      {notes.length ? (
        <ul>
          {notes.map((note) => (
            <li key={note.key} data-g={note.key}>
              <b>{note.number}</b>
              <span>{noteText(note)}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {children}
    </aside>
  );
}
