import { NextResponse, type NextRequest } from "next/server";

import { callbackTarget } from "@/lib/oidcSignIn";

export function GET(request: NextRequest) {
  const target = new URL(callbackTarget(request.nextUrl.searchParams), request.nextUrl.origin);
  const response = NextResponse.redirect(target, 302);
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("Referrer-Policy", "no-referrer");
  return response;
}
