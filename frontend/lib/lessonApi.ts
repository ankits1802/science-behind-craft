import { apiFetch } from "@/lib/api";
import { downloadApiFile, downloadFile } from "@/lib/download";
import {
  CITATIONS_FILE_PATH,
  EXPLAINER_PDF_PATH,
  exportLinkShape,
  LESSON_FILE_PATH,
  LESSON_PATH,
  LESSONS_PATH,
  lessonListShape,
  lessonPackShape,
  type CitationFormat,
  type LessonFormat,
  type LessonList,
  type LessonPack,
  type LessonRequest
} from "@/lib/lessonContract";
import { parseShape } from "@/lib/shape";

export const FILE_FAILED = "Couldn't download that file. Try again.";

export async function buildLesson(request: LessonRequest): Promise<LessonPack> {
  return parseShape(lessonPackShape, await apiFetch<unknown>(LESSONS_PATH, { method: "POST", body: JSON.stringify(request) }));
}

export async function fetchLessons(): Promise<LessonList> {
  return parseShape(lessonListShape, await apiFetch<unknown>(LESSONS_PATH));
}

export async function fetchLesson(lessonId: string): Promise<LessonPack> {
  return parseShape(lessonPackShape, await apiFetch<unknown>(LESSON_PATH(lessonId)));
}

export async function deleteLesson(lessonId: string): Promise<void> {
  await apiFetch<unknown>(LESSON_PATH(lessonId), { method: "DELETE" });
}

async function downloadLinked(path: string): Promise<string> {
  const link = parseShape(exportLinkShape, await apiFetch<unknown>(path));
  await downloadFile(link.url, link.fileName);
  return link.fileName;
}

export function downloadLessonFile(lessonId: string, format: LessonFormat): Promise<string> {
  return downloadLinked(LESSON_FILE_PATH(lessonId, format));
}

export function downloadExplainerPdf(explainerId: string, version: number): Promise<string> {
  return downloadLinked(EXPLAINER_PDF_PATH(explainerId, version));
}

export function downloadCitations(explainerId: string, version: number, format: CitationFormat): Promise<string> {
  return downloadApiFile(CITATIONS_FILE_PATH(explainerId, version, format), FILE_FAILED);
}
