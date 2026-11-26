import { expect, test } from "@playwright/test";

import { csrfRefusal, isMachineRoute, MACHINE_RESPONSE_HEADERS, upstreamHeaders } from "@/lib/server/apiProxy";

const MCP = "https://kalavigyan.example/api/mcp";

function agentPost(headers: Record<string, string>): Request {
  return new Request(MCP, { method: "POST", headers: { "content-type": "application/json", ...headers }, body: "{}" });
}

test("an agent's MCP post carries no browser origin, which the site's own forms always send", () => {
  expect(isMachineRoute("/api/mcp")).toBe(true);
  expect(isMachineRoute("/api/mcp/extra")).toBe(false);
  expect(isMachineRoute("/api/answers/stream")).toBe(false);
  expect(csrfRefusal(agentPost({}))).toBe("no-origin");
});

test("a machine route goes upstream with the caller's own token and protocol version, never the reader's session", () => {
  const request = agentPost({ authorization: "Bearer agent-token", "mcp-protocol-version": "2025-11-25", cookie: "kv_session=reader" });
  const headers = upstreamHeaders(request, null, {});
  expect(headers.get("authorization")).toBe("Bearer agent-token");
  expect(headers.get("mcp-protocol-version")).toBe("2025-11-25");
  expect(headers.get("cookie")).toBeNull();
  expect(upstreamHeaders(agentPost({}), null, {}).get("authorization")).toBeNull();
});

test("a 2026-07-28 request's mirrored method and name go upstream, so the server can check them against the body", () => {
  const request = agentPost({ "mcp-protocol-version": "2026-07-28", "mcp-method": "tools/call", "mcp-name": "get_page" });
  const headers = upstreamHeaders(request, null, {});
  expect([headers.get("mcp-protocol-version"), headers.get("mcp-method"), headers.get("mcp-name")]).toEqual([
    "2026-07-28",
    "tools/call",
    "get_page"
  ]);
  expect(upstreamHeaders(agentPost({}), null, {}).get("mcp-method")).toBeNull();
});

test("a machine route's reply is passed on unbuffered and untransformed, so a streamed MCP answer arrives as sent", () => {
  expect(MACHINE_RESPONSE_HEADERS).toEqual({ "cache-control": "no-store, no-transform", "x-accel-buffering": "no" });
  const streamed = upstreamHeaders(agentPost({ accept: "application/json, text/event-stream" }), null, {});
  expect(streamed.get("accept")).toBe("application/json, text/event-stream");
});
