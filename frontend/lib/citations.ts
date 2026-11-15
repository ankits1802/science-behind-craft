import type { AnswerReaction, AnswerSection, Citation, SourceRef } from "@/lib/types";

export function sourceNumbers(sections: readonly AnswerSection[], reactions: readonly AnswerReaction[] = []): Map<string, number> {
  const numbers = new Map<string, number>();
  const take = (citations: readonly Citation[]) => {
    for (const citation of citations) {
      if (!numbers.has(citation.sourceId)) numbers.set(citation.sourceId, numbers.size + 1);
    }
  };
  for (const section of sections) for (const sentence of section.sentences) take(sentence.citations);
  for (const reaction of reactions) take(reaction.citations);
  return numbers;
}

export function uniqueCitations(citations: readonly Citation[]): Citation[] {
  const seen = new Set<string>();
  const out: Citation[] = [];
  for (const citation of citations) {
    const key = `${citation.sourceId}:${citation.claimId}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(citation);
  }
  return out;
}

const ALLOWED_PROTOCOLS = new Set(["https:"]);

export function safeOutboundUrl(value: string | null | undefined): string | null {
  const text = (value ?? "").trim();
  if (!text) return null;
  try {
    const url = new URL(text);
    return ALLOWED_PROTOCOLS.has(url.protocol) ? url.toString() : null;
  } catch {
    return null;
  }
}

export function doiUrl(doi: string | null | undefined): string | null {
  const text = (doi ?? "").trim().replace(/^https?:\/\/(dx\.)?doi\.org\//i, "").replace(/^doi:\s*/i, "");
  if (!/^10\.\d{4,9}\/\S+$/.test(text)) return null;
  return `https://doi.org/${encodeURI(text)}`;
}

export function sourceHref(source: Pick<SourceRef, "url" | "doi">): string | null {
  return safeOutboundUrl(source.url) ?? doiUrl(source.doi);
}

export function sourceHost(href: string | null): string | null {
  if (!href) return null;
  try {
    return new URL(href).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

export function sourceByline(source: SourceRef): string {
  const authors = source.authors.filter(Boolean);
  const people = authors.length > 3 ? `${authors.slice(0, 3).join(", ")} et al.` : authors.join(", ");
  return [people, source.year ? String(source.year) : null, source.publisher].filter(Boolean).join(" · ");
}

export type HighlightPart = { text: string; mark: boolean };

function squash(value: string): string {
  return value.normalize("NFKC").replace(/\s+/g, " ");
}

export function highlightQuote(context: string | null | undefined, quote: string | null | undefined): HighlightPart[] {
  const body = squash(context ?? "").trim();
  const needle = squash(quote ?? "").trim();
  if (!body) return needle ? [{ text: needle, mark: true }] : [];
  if (!needle) return [{ text: body, mark: false }];
  const at = body.toLowerCase().indexOf(needle.toLowerCase());
  if (at < 0) return [{ text: needle, mark: true }];
  const parts: HighlightPart[] = [];
  if (at > 0) parts.push({ text: body.slice(0, at), mark: false });
  parts.push({ text: body.slice(at, at + needle.length), mark: true });
  if (at + needle.length < body.length) parts.push({ text: body.slice(at + needle.length), mark: false });
  return parts;
}
