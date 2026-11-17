import { expect, test } from "@playwright/test";

import { notificationListShape, type NotificationList } from "@/lib/learningContract";
import { NO_NOTES, NOTES_FRESH_FOR_MS, notesStore, type HeldNotes } from "@/lib/notesStore";
import { parseShape } from "@/lib/shape";

import { readRepo } from "./phaseBFixture";

const ALERTS = JSON.parse(readRepo("shared", "learning.alerts.golden.json")) as { notifications: unknown };
const FIRST_READER_NOTES = parseShape(notificationListShape, ALERTS.notifications);
const SECOND_READER_NOTES: NotificationList = { schemaVersion: 1, items: [], unread: 0 };
const FIRST = "reader-1";
const SECOND = "reader-2";

type Pending = { account: string; resolve: (list: NotificationList) => void };

function scriptedServer() {
  const pending: Pending[] = [];
  let signedIn = FIRST;
  return {
    pending,
    signIn: (account: string) => {
      signedIn = account;
    },
    load: () =>
      new Promise<NotificationList>((resolve) => {
        pending.push({ account: signedIn, resolve });
      })
  };
}

test("a reader signed in after another in the same tab sees none of the first reader's notes", async () => {
  const server = scriptedServer();
  let clock = 1_000;
  const store = notesStore(server.load, () => clock);
  const seen: HeldNotes[] = [];
  store.subscribe((held) => seen.push(held));

  const first = store.refresh(FIRST);
  server.pending[0].resolve(FIRST_READER_NOTES);
  await first;
  expect(store.notesOf(FIRST).list?.unread).toBe(1);
  expect(store.due(FIRST)).toBe(false);

  clock += NOTES_FRESH_FOR_MS / 2;
  server.signIn(SECOND);
  expect(store.notesOf(SECOND)).toBe(NO_NOTES);
  expect(store.notesOf(null)).toBe(NO_NOTES);
  expect(store.due(SECOND)).toBe(true);

  const second = store.refresh(SECOND);
  expect(store.notesOf(SECOND)).toBe(NO_NOTES);
  expect(store.notesOf(FIRST)).toBe(NO_NOTES);
  server.pending[1].resolve(SECOND_READER_NOTES);
  await second;
  expect(store.notesOf(SECOND).list).toEqual(SECOND_READER_NOTES);
  expect(seen.map((held) => held.account)).toEqual([FIRST, SECOND]);
});

test("a first reader's answer arriving after the second signs in is never shown", async () => {
  const server = scriptedServer();
  const store = notesStore(server.load, () => 5_000);
  const late = store.refresh(FIRST);
  server.signIn(SECOND);
  const current = store.refresh(SECOND);
  server.pending[1].resolve(SECOND_READER_NOTES);
  await current;
  server.pending[0].resolve(FIRST_READER_NOTES);
  await late;
  expect(server.pending.map((call) => call.account)).toEqual([FIRST, SECOND]);
  expect(store.notesOf(SECOND).list).toEqual(SECOND_READER_NOTES);
  expect(store.notesOf(FIRST)).toBe(NO_NOTES);
});

test("notes refresh once a minute for the same reader and at once when asked", async () => {
  const server = scriptedServer();
  let clock = 0;
  const store = notesStore(server.load, () => clock);
  const first = store.refresh(FIRST);
  expect(store.refresh(FIRST)).toBe(first);
  server.pending[0].resolve(FIRST_READER_NOTES);
  await first;
  clock += NOTES_FRESH_FOR_MS;
  expect(store.due(FIRST)).toBe(false);
  clock += 1;
  expect(store.due(FIRST)).toBe(true);
  const again = store.refreshHeld();
  expect(server.pending.map((call) => call.account)).toEqual([FIRST, FIRST]);
  server.pending[1].resolve(SECOND_READER_NOTES);
  await again;
  expect(store.notesOf(FIRST).list?.unread).toBe(0);
});
