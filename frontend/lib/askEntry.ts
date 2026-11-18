import { signInHref } from "@/lib/sessionReturn";

export const ASK_PAGE = "/ask";

export type AskEntry = { craft?: string | null; question?: string | null };

export function askPagePath({ craft, question }: AskEntry): string {
  const search = new URLSearchParams();
  const asked = question?.trim();
  if (asked) search.set("q", asked);
  if (craft) search.set("craft", craft);
  const query = search.toString();
  return query ? `${ASK_PAGE}?${query}` : ASK_PAGE;
}

export function signedOutAskHref(entry: AskEntry): string {
  return signInHref(askPagePath(entry));
}
