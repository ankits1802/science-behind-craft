import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";

import { FRONTEND } from "./moduleGraph";

export const PACKAGE = "package:";

const RUNTIME_IMPORT = /^(?:import|export)\s+(type\s+)?(?:[^;"]*?\s+from\s+)?"([^"]+)";/gm;
const DYNAMIC_IMPORT = /\bimport\("([^"]+)"\)/g;
const CLIENT_DIRECTIVE = /^\s*"use client";/;
const SOURCE = /\.(?:tsx?|mjs)$/;
const SUFFIXES = ["", ".ts", ".tsx", "/index.ts", "/index.tsx"];

function isFile(path: string): boolean {
  return existsSync(path) && statSync(path).isFile();
}

function frontendPath(path: string): string {
  return relative(FRONTEND, path).replace(/\\/g, "/");
}

function sourceText(file: string): string {
  return SOURCE.test(file) ? readFileSync(join(FRONTEND, file), "utf8") : "";
}

export function resolvedModule(specifier: string, from: string): string {
  if (!specifier.startsWith("@/") && !specifier.startsWith(".")) {
    const parts = specifier.split("/");
    return `${PACKAGE}${specifier.startsWith("@") ? parts.slice(0, 2).join("/") : parts[0]}`;
  }
  const base = specifier.startsWith("@/") ? join(FRONTEND, specifier.slice(2)) : join(FRONTEND, dirname(from), specifier);
  const found = SUFFIXES.map((suffix) => `${base}${suffix}`).find(isFile);
  if (!found) throw new Error(`${specifier}, imported by ${from}, resolves to no file`);
  return frontendPath(found);
}

export function runtimeImports(file: string): string[] {
  return [...sourceText(file).matchAll(RUNTIME_IMPORT)].filter((found) => !found[1]).map((found) => resolvedModule(found[2], file));
}

export function dynamicImports(file: string): string[] {
  return [...sourceText(file).matchAll(DYNAMIC_IMPORT)].map((found) => resolvedModule(found[1], file));
}

export function isClientModule(file: string): boolean {
  return CLIENT_DIRECTIVE.test(sourceText(file));
}

function chainTo(parents: ReadonlyMap<string, string | null>, node: string): string[] {
  const chain: string[] = [];
  for (let at: string | null = node; at !== null; at = parents.get(at) ?? null) chain.unshift(at);
  return chain;
}

export function heavyChains(entry: string, heavy: (node: string) => boolean): string[][] {
  const parents = new Map<string, string | null>([[entry, null]]);
  const queue = [entry];
  const chains: string[][] = [];
  for (let node = queue.shift(); node !== undefined; node = queue.shift()) {
    if (heavy(node)) {
      chains.push(chainTo(parents, node));
      continue;
    }
    for (const next of runtimeImports(node)) {
      if (parents.has(next)) continue;
      parents.set(next, node);
      queue.push(next);
    }
  }
  return chains;
}

export function reachedModules(entry: string): Set<string> {
  const seen = new Set<string>([entry]);
  const queue = [entry];
  for (let node = queue.shift(); node !== undefined; node = queue.shift()) {
    for (const next of runtimeImports(node)) {
      if (seen.has(next)) continue;
      seen.add(next);
      queue.push(next);
    }
  }
  return seen;
}

export function reachedStyles(entry: string): string[] {
  return [...reachedModules(entry)].filter((node) => node.endsWith(".css")).sort();
}

export function clientBoundaries(entries: readonly string[]): string[] {
  const seen = new Set<string>(entries);
  const queue = [...entries];
  const boundaries: string[] = [];
  for (let node = queue.shift(); node !== undefined; node = queue.shift()) {
    if (isClientModule(node)) {
      boundaries.push(node);
      continue;
    }
    for (const next of [...runtimeImports(node), ...dynamicImports(node)]) {
      if (seen.has(next)) continue;
      seen.add(next);
      queue.push(next);
    }
  }
  return boundaries.sort();
}
