import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

export const FRONTEND = join(__dirname, "..");

const STATIC_IMPORT = /^import\s+(type\s+)?[^;]*?from\s+"([^"]+)";/gm;

export function moduleFile(specifier: string): string {
  const base = join(FRONTEND, specifier.slice(2));
  const found = [".ts", ".tsx", "/index.ts", "/index.tsx"].map((suffix) => `${base}${suffix}`).find((file) => existsSync(file));
  if (!found) throw new Error(`${specifier} resolves to no file`);
  return found;
}

export function staticImports(text: string): string[] {
  return [...text.matchAll(STATIC_IMPORT)].filter((found) => !found[1]).map((found) => found[2]);
}

export function eagerModules(entry: string): Set<string> {
  const seen = new Set<string>();
  const queue = [moduleFile(entry)];
  while (queue.length > 0) {
    const file = queue.pop() as string;
    if (seen.has(file)) continue;
    seen.add(file);
    for (const specifier of staticImports(readFileSync(file, "utf8"))) if (specifier.startsWith("@/")) queue.push(moduleFile(specifier));
  }
  return new Set([...seen].map((file) => file.slice(FRONTEND.length + 1).replace(/\\/g, "/")));
}
