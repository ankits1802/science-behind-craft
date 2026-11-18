export type Chapter = { id: string; label: string };

export type ChapterTop = { id: string; top: number };

export function currentChapter(tops: readonly ChapterTop[], line: number): string | null {
  if (tops.length === 0) return null;
  let current = tops[0].id;
  for (const chapter of tops) {
    if (chapter.top - line > 1) break;
    current = chapter.id;
  }
  return current;
}

export function chapterFromQuery(search: string, aliases: Readonly<Record<string, string>>, chapters: readonly Chapter[]): string | null {
  const tab = new URLSearchParams(search).get("tab");
  if (!tab) return null;
  const id = aliases[tab] ?? tab;
  return chapters.some((chapter) => chapter.id === id) ? id : null;
}
