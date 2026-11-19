import { expect, test } from "@playwright/test";

import { csrfRefusal, isMachineRoute, upstreamHeaders } from "@/lib/server/apiProxy";

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
