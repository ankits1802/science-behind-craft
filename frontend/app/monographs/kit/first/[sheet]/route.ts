import { readFileSync } from "node:fs";
import { join } from "node:path";

import { firstSheet, firstSheetScopes } from "@/lib/kitFirstSheet";
import { KIT_FILE } from "@/lib/server/kitFile";

type SheetRoute = { params: Promise<{ sheet: string }> };

export const dynamic = "force-static";
export const dynamicParams = true;

export function generateStaticParams(): { sheet: string }[] {
  return [];
}

export async function GET(_request: Request, { params }: SheetRoute): Promise<Response> {
  const scopes = firstSheetScopes((await params).sheet);
  if (scopes === null) return new Response(null, { status: 404 });
  const kit = readFileSync(join(process.cwd(), KIT_FILE), "utf8");
  return new Response(firstSheet(kit, scopes), { headers: { "Content-Type": "text/css; charset=utf-8" } });
}
