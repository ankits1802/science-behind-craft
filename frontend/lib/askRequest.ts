import { resolvedLanguage, type AnswerLanguage } from "@/lib/answerLanguages";
import type { AskRequest } from "@/lib/answerStream";
import type { CraftPick } from "@/lib/askCraft";
import type { Depth } from "@/lib/explainerContract";

export const QUESTION_MIN = 2;
export const QUESTION_MAX = 1000;

export type AskChoices = { pick: CraftPick; depth: Depth | null; language: string };

export type AskSettings = {
  pick: CraftPick;
  depth: Depth | null;
  pickedDepth: Depth | null;
  languageChoice: string;
  languages: AnswerLanguage[];
};

export type AskChange = { pick?: CraftPick; depth?: Depth; languageChoice?: string; fresh?: boolean };

export type PlannedAsk = { request: AskRequest; search: string };

export function askable(question: string): boolean {
  return question.trim().length >= QUESTION_MIN;
}

export function askRequestOf(question: string, choices: AskChoices): AskRequest | null {
  const trimmed = question.trim().slice(0, QUESTION_MAX).trim();
  if (!askable(trimmed)) return null;
  const request: AskRequest = { question: trimmed, depth: choices.depth, craftSlug: choices.pick.craftSlug, language: choices.language };
  return choices.pick.anyCraft ? { ...request, anyCraft: true } : request;
}

export function askSearch(question: string, craftSlug: string | null, depth: Depth | null): string {
  const search = new URLSearchParams();
  search.set("q", question);
  if (craftSlug) search.set("craft", craftSlug);
  if (depth) search.set("depth", depth);
  return search.toString();
}

export function plannedAsk(question: string, settings: AskSettings, change: AskChange = {}): PlannedAsk | null {
  const pick = change.pick ?? settings.pick;
  const language = resolvedLanguage(change.languageChoice ?? settings.languageChoice, question, settings.languages).code;
  const asked = askRequestOf(question, { pick, depth: change.depth ?? settings.depth, language });
  if (!asked) return null;
  const request = change.fresh ? { ...asked, fresh: true } : asked;
  return { request, search: askSearch(request.question, pick.craftSlug, change.depth ?? settings.pickedDepth) };
}

export function reasksOnChange(started: boolean, asked: string, current: string): boolean {
  const question = current.trim();
  return started && askable(question) && asked.trim() === question;
}
