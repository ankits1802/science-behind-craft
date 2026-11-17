import { createSocket } from "node:dgram";

import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { SandboxFrame } from "@/components/answer/play/SandboxFrame";
import type { SimulationBlock } from "@/lib/explainerPlay";
import { FRAME_GUARD, FRAME_PEER_NAMES, frameHeightFrom, sandboxDocument } from "@/lib/sandboxFrame";

import { CONTENT_SECURITY_POLICY } from "../next.config";
import { phaseCBlock } from "./playFixture";

type Probe = { heights: unknown[] };

const ORIGIN = "https://kalavigyan.test";
const ESCAPE = [
  '<p id="out">waiting</p>',
  "<script>",
  "const seen = [];",
  'try { seen.push(parent.document.title); } catch (error) { seen.push("page closed"); }',
  'try { seen.push(String(localStorage.length)); } catch (error) { seen.push("storage closed"); }',
  'new Image().src = "https://example.org/pixel.png";',
  'fetch("https://example.org/leak").then(() => seen.push("fetched"), () => seen.push("network closed")).finally(() => { document.getElementById("out").textContent = seen.join(", "); });',
  "</script>"
].join("");
const AWAY = '<p id="here">here</p><script>location.href = "https://example.org/away";</script>';

function probe(block: SimulationBlock, title: string, html: string): SimulationBlock {
  return { ...block, title, html };
}

function framePage(blocks: SimulationBlock[]): string {
  const frames = blocks.map((block) => renderToStaticMarkup(createElement(SandboxFrame, { block }))).join("");
  const listen = 'window.heights = []; addEventListener("message", (event) => window.heights.push(event.data));';
  return `<!doctype html><html><head><title>Kept</title><script>${listen}</script></head><body style="margin:0;width:390px">${frames}</body></html>`;
}

test("a srcdoc frame draws under the site's policy, runs on its data alone and reaches nothing", async ({ page }) => {
  const block = phaseCBlock("simulation", "s1.b1");
  const outbound: string[] = [];
  await page.route("**/*", async (route) => {
    const url = route.request().url();
    if (url === `${ORIGIN}/`) {
      const body = framePage([block, probe(block, "Escape", ESCAPE), probe(block, "Away", AWAY)]);
      await route.fulfill({ status: 200, contentType: "text/html", headers: { "Content-Security-Policy": CONTENT_SECURITY_POLICY }, body });
      return;
    }
    outbound.push(url);
    await route.fulfill({ status: 404, body: "" });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${ORIGIN}/`);

  const drawn = page.frameLocator('iframe[title="How fast the water table falls"]');
  await expect(drawn.locator("#count")).toHaveText("1");
  await expect(drawn.locator("#said")).toHaveText("The water table is 10 to 15 feet lower.");
  await expect(page.frameLocator('iframe[title="Escape"]').locator("#out")).toHaveText("page closed, storage closed, network closed");

  await page.waitForFunction(() => (window as unknown as Probe).heights.length >= 2);
  const heights = await page.evaluate(() => (window as unknown as Probe).heights);
  for (const message of heights) expect(frameHeightFrom(message)).not.toBeNull();

  await page.waitForTimeout(1000);
  expect(outbound.filter((url) => !url.endsWith("/favicon.ico"))).toEqual([]);
  expect(await page.title()).toBe("Kept");
  expect(page.frames().map((frame) => frame.url()).filter((url) => url.includes("example.org"))).toEqual([]);
});

type Listener = { port: number; packets: number[]; close: () => Promise<void> };

async function loopbackListener(): Promise<Listener> {
  const socket = createSocket("udp4");
  const packets: number[] = [];
  socket.on("message", (message) => packets.push(message.length));
  await new Promise<void>((resolve) => socket.bind(0, "127.0.0.1", resolve));
  return { port: socket.address().port, packets, close: () => new Promise((resolve) => socket.close(() => resolve())) };
}

function inScript(text: string): string {
  return JSON.stringify(text).replace(/<\//g, "<\\/");
}

function escapedAttribute(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function peerProbe(port: number): string {
  const ice = `{ iceServers: [{ urls: 'stun:127.0.0.1:${port}' }] }`;
  const offer = "pc.createDataChannel('a'); pc.createOffer().then(function (o) { return pc.setLocalDescription(o); });";
  const child = `<script>try { const pc = new RTCPeerConnection(${ice}); ${offer} } catch (error) {}</script>`;
  return [
    '<p id="out">waiting</p><script>',
    "const said = [];",
    `function peer(make) { try { const pc = make(); ${offer} said.push("made"); } catch (error) { said.push("blocked"); } }`,
    `peer(function () { return new RTCPeerConnection(${ice}); });`,
    `peer(function () { return new (Object.getOwnPropertyDescriptor(window, "RTC" + "PeerConnection").value)(${ice}); });`,
    'const nested = document.createElement("iframe");',
    `nested.srcdoc = ${inScript(child)};`,
    "document.body.append(nested);",
    'said.push(nested.contentWindow === null ? "no window" : "window");',
    `document.body.insertAdjacentHTML("beforeend", ${inScript(`<iframe srcdoc="${escapedAttribute(child)}"></iframe>`)});`,
    'document.getElementById("out").textContent = said.join(", ");',
    "</script>"
  ].join("");
}

function unguardedFrame(block: SimulationBlock): string {
  const srcdoc = sandboxDocument(block.html, block.values).replace(`<script>${FRAME_GUARD}</script>`, "");
  return `<iframe sandbox="allow-scripts" title="Unguarded" srcdoc="${escapedAttribute(srcdoc)}"></iframe>`;
}

test("a frame opens no peer connection: the guard leaves no constructor, no nested window and no nested frame", async ({ page }) => {
  const fixture = phaseCBlock("simulation", "s1.b1");
  const guarded = await loopbackListener();
  const control = await loopbackListener();
  try {
    const peer = probe(fixture, "Peer", peerProbe(guarded.port));
    const unguarded = unguardedFrame(probe(fixture, "Unguarded", peerProbe(control.port)));
    await page.route("**/*", async (route) => {
      if (route.request().url() !== `${ORIGIN}/`) return route.fulfill({ status: 404, body: "" });
      const body = framePage([peer]).replace("</body>", `${unguarded}</body>`);
      return route.fulfill({ status: 200, contentType: "text/html", headers: { "Content-Security-Policy": CONTENT_SECURITY_POLICY }, body });
    });
    await page.goto(`${ORIGIN}/`);
    expect(sandboxDocument(peer.html, peer.values)).toContain(`<script>${FRAME_GUARD}</script>`);
    for (const name of FRAME_PEER_NAMES) expect(FRAME_GUARD).toContain(name);
    await expect(page.frameLocator('iframe[title="Peer"]').locator("#out")).toHaveText("blocked, blocked, no window");
    await expect(page.frameLocator('iframe[title="Unguarded"]').locator("#out")).toHaveText("made, made, window");
    await page.waitForTimeout(3000);
    expect(guarded.packets).toEqual([]);
  } finally {
    await Promise.all([guarded.close(), control.close()]);
  }
});
