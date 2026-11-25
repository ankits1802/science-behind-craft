import type { KitScope } from "@/lib/monographScopes";

export const KIT_SCOPES: readonly KitScope[] = ["chem", "pt", "rm", "mb", "ask", "sa"];
export const FIRST_SHEET_PATH = "/monographs/kit/first/";

const SHEET_SUFFIX = ".css";
const NO_SCOPE = "none";
const SCOPE_JOIN = "-";
const GROUPING_RULES: ReadonlySet<string> = new Set(["media", "supports", "container", "layer", "scope", "starting-style"]);
const FUNCTIONAL_PSEUDO = /:(?:not|is|where|has)\(/gi;
const SCOPE_CLASS = /\.bx-(chem|pt|rm|mb|ask|sa)(?![\w-])/g;

type Piece = { lead: string; text: string; prelude: string; block: string | null };

function skipString(css: string, at: number): number {
  const quote = css[at];
  let next = at + 1;
  while (next < css.length && css[next] !== quote) next += css[next] === "\\" ? 2 : 1;
  return next + 1;
}

function skipComment(css: string, at: number): number {
  const end = css.indexOf("*/", at + 2);
  return end < 0 ? css.length : end + 2;
}

function closing(css: string, open: number): number {
  let depth = 0;
  let at = open;
  while (at < css.length) {
    const char = css[at];
    if (char === '"' || char === "'") at = skipString(css, at);
    else if (char === "/" && css[at + 1] === "*") at = skipComment(css, at);
    else {
      if (char === "{") depth += 1;
      if (char === "}" && --depth === 0) return at;
      at += 1;
    }
  }
  return css.length - 1;
}

function pieces(css: string): { parts: Piece[]; tail: string } {
  const parts: Piece[] = [];
  let from = 0;
  let at = 0;
  while (at < css.length) {
    const char = css[at];
    if (/\s/.test(char)) at += 1;
    else if (char === "/" && css[at + 1] === "*") at = skipComment(css, at);
    else {
      let end = at;
      while (end < css.length && css[end] !== "{" && css[end] !== ";") end = css[end] === '"' || css[end] === "'" ? skipString(css, end) : end + 1;
      if (css[end] === ";") {
        parts.push({ lead: css.slice(from, at), text: css.slice(at, end + 1), prelude: css.slice(at, end), block: null });
        at = end + 1;
      } else {
        const last = closing(css, end);
        parts.push({ lead: css.slice(from, at), text: css.slice(at, last + 1), prelude: css.slice(at, end), block: css.slice(end + 1, last) });
        at = last + 1;
      }
      from = at;
    }
  }
  return { parts, tail: css.slice(from) };
}

function splitTop(selectors: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let from = 0;
  for (let at = 0; at < selectors.length; at += 1) {
    const char = selectors[at];
    if (char === '"' || char === "'") at = skipString(selectors, at) - 1;
    else if (char === "(" || char === "[") depth += 1;
    else if (char === ")" || char === "]") depth -= 1;
    else if (char === "," && depth === 0) {
      out.push(selectors.slice(from, at));
      from = at + 1;
    }
  }
  out.push(selectors.slice(from));
  return out.map((selector) => selector.trim()).filter(Boolean);
}

function withoutFunctionalPseudo(selector: string): string {
  let out = "";
  let from = 0;
  for (const found of selector.matchAll(FUNCTIONAL_PSEUDO)) {
    const start = found.index ?? 0;
    if (start < from) continue;
    let depth = 0;
    let at = start + found[0].length - 1;
    for (; at < selector.length; at += 1) {
      if (selector[at] === "(") depth += 1;
      if (selector[at] === ")" && --depth === 0) break;
    }
    out += selector.slice(from, start);
    from = at + 1;
  }
  return out + selector.slice(from);
}

export function selectorScopes(selector: string): KitScope[] {
  return [...new Set([...withoutFunctionalPseudo(selector).matchAll(SCOPE_CLASS)].map((found) => found[1] as KitScope))];
}

function drawable(prelude: string, drawn: ReadonlySet<KitScope>): boolean {
  return splitTop(prelude).some((selector) => selectorScopes(selector).every((scope) => drawn.has(scope)));
}

function atRuleName(prelude: string): string | null {
  return prelude.startsWith("@") ? (/^@([\w-]+)/.exec(prelude)?.[1] ?? "").toLowerCase() : null;
}

function kept(piece: Piece, drawn: ReadonlySet<KitScope>): string | null {
  const name = atRuleName(piece.prelude);
  if (piece.block === null) return piece.text;
  if (name === null) return drawable(piece.prelude, drawn) ? piece.text : null;
  if (!GROUPING_RULES.has(name)) return piece.text;
  const inner = firstSheet(piece.block, drawn);
  return pieces(inner).parts.length ? `${piece.prelude}{${inner}}` : null;
}

export function firstSheet(kit: string, drawn: ReadonlySet<KitScope>): string {
  const { parts, tail } = pieces(kit);
  let out = "";
  for (const piece of parts) {
    const text = kept(piece, drawn);
    if (text !== null) out += piece.lead + text;
  }
  return out + tail;
}

export function firstSheetName(drawn: ReadonlySet<KitScope>): string {
  const named = KIT_SCOPES.filter((scope) => drawn.has(scope));
  return `${named.length ? named.join(SCOPE_JOIN) : NO_SCOPE}${SHEET_SUFFIX}`;
}

export function firstSheetHref(drawn: ReadonlySet<KitScope>): string {
  return `${FIRST_SHEET_PATH}${firstSheetName(drawn)}`;
}

export function firstSheetScopes(name: string): Set<KitScope> | null {
  if (!name.endsWith(SHEET_SUFFIX)) return null;
  const stem = name.slice(0, -SHEET_SUFFIX.length);
  const scopes = new Set(stem === NO_SCOPE ? [] : (stem.split(SCOPE_JOIN) as KitScope[]));
  return firstSheetName(scopes) === name ? scopes : null;
}
