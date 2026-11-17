import { API_BASE, APP_PLATFORM, APP_VERSION, APP_VERSION_CODE, ApiError, describeApiBody, statusFallback } from "@/lib/api";
import type { Depth } from "@/lib/explainerContract";

export const ANSWER_STREAM_PATH = "/answers/stream";

export type AskRequest = {
  question: string;
  depth: Depth | null;
  craftSlug?: string | null;
  anyCraft?: boolean;
  language?: string | null;
  fresh?: boolean;
  conversationId?: string | null;
};

export function sseFields(block: string): { name: string; data: string | null } {
  let name = "message";
  const data: string[] = [];
  for (const raw of block.split("\n")) {
    const line = raw.endsWith("\r") ? raw.slice(0, -1) : raw;
    if (!line || line.startsWith(":")) continue;
    const colon = line.indexOf(":");
    const field = colon < 0 ? line : line.slice(0, colon);
    const value = colon < 0 ? "" : line.slice(colon + 1).replace(/^ /, "");
    if (field === "event") name = value;
    else if (field === "data") data.push(value);
  }
  return { name, data: data.length ? data.join("\n") : null };
}

export function splitSseBuffer(buffer: string): { blocks: string[]; rest: string } {
  const normalised = buffer.replace(/\r\n/g, "\n");
  const parts = normalised.split("\n\n");
  const rest = parts.pop() ?? "";
  return { blocks: parts, rest };
}

export async function openEventStream(path: string, init: { body: BodyInit; json: boolean; signal?: AbortSignal; fallback: string }): Promise<ReadableStream<Uint8Array>> {
  const headers = new Headers({ Accept: "text/event-stream" });
  if (init.json) headers.set("Content-Type", "application/json");
  headers.set("X-Client-Time", new Date().toISOString());
  headers.set("X-App-Version", APP_VERSION);
  headers.set("X-App-Platform", APP_PLATFORM);
  if (APP_VERSION_CODE) headers.set("X-App-Version-Code", APP_VERSION_CODE);

  const response = await fetch(`${API_BASE}/api${path}`, { method: "POST", headers, body: init.body, cache: "no-store", signal: init.signal });

  if (!response.ok || !response.body) {
    const contentType = response.headers.get("content-type") ?? "";
    const body = contentType.includes("application/json") ? await response.json().catch(() => null) : await response.text().catch(() => "");
    throw new ApiError(response.status, describeApiBody(body, statusFallback(response.status, init.fallback)), body, response.headers);
  }
  return response.body;
}

export async function readSseBlocks(stream: ReadableStream<Uint8Array>, onBlock: (block: string) => void): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { blocks, rest } = splitSseBuffer(buffer);
    buffer = rest;
    for (const block of blocks) onBlock(block);
  }
  buffer += decoder.decode();
  if (buffer.trim()) onBlock(buffer);
}
