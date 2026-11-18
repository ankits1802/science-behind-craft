import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import {
  catalogueCountLine,
  craftIndex,
  groupCrafts,
  placedCountLine,
  readerCount,
  searchCatalogue,
  shownCountLine,
  withinCategory
} from "@/lib/craftCatalogue";
import { CRAFT_STATUSES, FAMILY_PALETTES, parseCraftCatalogue, type CraftCatalogue } from "@/lib/craftCatalogueContract";
import { SESSION_COOKIE, INSECURE_SESSION_COOKIE } from "@/lib/sessionCookie";
import { UNKNOWN_VIEWER, upstreamHeaders } from "@/lib/server/apiProxy";
import { publicFetch, signedInFetch, type IncomingRequest } from "@/lib/server/serverFetch";
import { ShapeError } from "@/lib/shape";

const FRONTEND = join(__dirname, "..");
const BACKEND = join(FRONTEND, "..", "backend", "app");
const SHARED = join(FRONTEND, "..", "shared");
const ENV = { API_ORIGIN: "https://api.example.test", NODE_ENV: "production" };

function golden(): unknown {
  return JSON.parse(readFileSync(join(SHARED, "craft.catalogue.golden.json"), "utf8"));
}

function catalogue(): CraftCatalogue {
  return parseCraftCatalogue(golden());
}

function backendTuple(file: string, name: string): string[] {
  const source = readFileSync(join(BACKEND, ...file.split("/")), "utf8");
  const found = new RegExp(`^${name} = \\(([^)]*)\\)`, "m").exec(source);
  if (!found) throw new Error(`${name} is not a tuple in backend/app/${file}`);
  return [...found[1].matchAll(/"([^"]+)"/g)].map((value) => value[1]);
}

function sources(folder: string): string[] {
  return readdirSync(folder).flatMap((name) => {
    const path = join(folder, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.tsx?$/.test(name) ? [path] : [];
  });
}

function names(crafts: readonly { displayName: string }[]): string[] {
  return crafts.map((craft) => craft.displayName);
}

type Call = { url: string; init: RequestInit };

function recorder(answer: () => Promise<Response>): { calls: Call[]; fetcher: typeof fetch } {
  const calls: Call[] = [];
  const fetcher = (async (url: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(url), init: init ?? {} });
    return answer();
  }) as typeof fetch;
  return { calls, fetcher };
}

function json(body: unknown, status = 200): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }));
}

function visitor(host: string, cookies: Record<string, string>, proto?: string): IncomingRequest {
  const headers = new Headers({ host, "x-real-ip": "203.0.113.9" });
  if (proto) headers.set("x-forwarded-proto", proto);
  return { headers, cookie: (name) => cookies[name] ?? null };
}

test("the catalogue golden parses on the client exactly as the backend wrote it", () => {
  expect(parseCraftCatalogue(golden())).toEqual(golden());
});

test("a catalogue off its contract is refused, not patched", () => {
  const body = golden() as Record<string, unknown>;
  const { summary: _summary, ...withoutSummary } = body;
  expect(() => parseCraftCatalogue(withoutSummary)).toThrow(ShapeError);
  const crafts = body.crafts as Record<string, unknown>[];
  expect(() => parseCraftCatalogue({ ...body, crafts: [{ ...crafts[0], palette: "purple" }] })).toThrow(ShapeError);
  expect(() => parseCraftCatalogue({ ...body, crafts: [{ ...crafts[0], nickname: "x" }] })).toThrow(ShapeError);
  expect(() => parseCraftCatalogue({ ...body, schemaVersion: 1 })).toThrow(ShapeError);
});

test("the palette keys and craft statuses are the backend's", () => {
  expect([...FAMILY_PALETTES]).toEqual(backendTuple("data/craft_families.py", "FAMILY_PALETTES"));
  expect([...CRAFT_STATUSES]).toEqual(backendTuple("models/enums.py", "CRAFT_STATUSES"));
});

test("a search for a material or a technique leads with the concept and the crafts it links", () => {
  const indigo = searchCatalogue(catalogue(), "indigo");
  expect(indigo.concepts[0].concept.label).toBe("Indigo");
  expect(names(indigo.concepts[0].crafts)).toEqual(["Bagru Hand Block Print", "Kutch Ajrakh", "Sanganeri Hand Block Printing"]);
  expect(names(indigo.crafts)).toEqual(["Bagru Hand Block Print", "Kutch Ajrakh", "Sanganeri Hand Block Printing"]);
  expect(searchCatalogue(catalogue(), "mordant").concepts.map((hit) => hit.concept.label)).toEqual(["Printing the mordants"]);
  expect(searchCatalogue(catalogue(), "alum").concepts.map((hit) => hit.concept.label)).toEqual(["Potassium alum"]);
  expect(searchCatalogue(catalogue(), "fitkari").concepts.map((hit) => hit.concept.label)).toEqual(["Potassium alum"]);
  const lostWax = searchCatalogue(catalogue(), "lost wax");
  expect(lostWax.concepts.map((hit) => hit.concept.label)).toEqual(["Lost-wax casting"]);
  expect(names(lostWax.crafts)).toEqual(["Bastar Dhokra"]);
  expect(searchCatalogue(catalogue(), "harda").concepts.map((hit) => hit.concept.label)).toEqual(["Harda", "Myrobalan"]);
});

test("a search for a craft, its alias or its state still finds crafts first", () => {
  const ajrak = searchCatalogue(catalogue(), "Ajrak");
  expect(ajrak.concepts).toEqual([]);
  expect(names(ajrak.crafts)[0]).toBe("Kutch Ajrakh");
  expect(names(searchCatalogue(catalogue(), "Punjab").crafts)).toEqual(["Phulkari"]);
  expect(names(searchCatalogue(catalogue(), "embossing").crafts)).toEqual(["Metal Embossing"]);
  const everything = searchCatalogue(catalogue(), "  ");
  expect(everything.concepts).toEqual([]);
  expect(everything.crafts).toHaveLength(catalogue().crafts.length);
});

test("reader counts come from the summary and leave catch-all rows out", () => {
  const body = catalogue();
  expect(body.crafts.some((craft) => craft.isCatchAll)).toBe(true);
  expect(body.summary.crafts).toBe(body.crafts.filter((craft) => !craft.isCatchAll).length);
  expect(catalogueCountLine(body)).toBe("7 crafts · 5 GI-registered · 6 states");
  expect(placedCountLine(body)).toBe("5 crafts placed in 6 states");
  expect(shownCountLine(body, body.crafts)).toBe("Showing 7 of 7 crafts and 1 “Other” entry");
  const prints = body.crafts.filter((craft) => craft.kindLabel === "Hand block printing");
  expect(prints).toHaveLength(4);
  expect(shownCountLine(body, prints)).toBe("Showing 3 of 7 crafts and 1 “Other” entry");
  expect(shownCountLine(body, prints.filter((craft) => craft.isCatchAll))).toBe("Showing 0 of 7 crafts and 1 “Other” entry");
  expect(shownCountLine(body, prints.filter((craft) => !craft.isCatchAll))).toBe("Showing 3 of 7 crafts");
});

test("each group's count is its readers, the number the status line adds up", () => {
  const body = catalogue();
  const groups = groupCrafts(body, body.crafts);
  const prints = groups.find((group) => group.heading === "Textiles · Hand block printing");
  expect(prints?.crafts).toHaveLength(4);
  expect(readerCount(prints?.crafts ?? [])).toBe(3);
  expect(groups.reduce((sum, group) => sum + readerCount(group.crafts), 0)).toBe(body.summary.crafts);
});

test("a category filter narrows each concept to its crafts in that category, so none points at a hidden craft", () => {
  const body = catalogue();
  const familyId = (label: string) => body.categories.find((row) => row.label === label)?.id ?? "";
  const [textiles, metal] = [familyId("Textiles"), familyId("Metal")];
  expect(textiles && metal).toBeTruthy();
  expect(withinCategory(searchCatalogue(body, "indigo"), metal)).toEqual({ concepts: [], crafts: [] });
  expect(withinCategory(searchCatalogue(body, "indigo"), "")).toEqual(searchCatalogue(body, "indigo"));
  const shared = { ...body, concepts: [...body.concepts, { key: "wax", label: "Wax", names: [], craftSlugs: ["Kutch-Ajrakh", "Bastar-Dhokra"] }] };
  expect(searchCatalogue(shared, "wax").concepts.map((hit) => hit.concept.label)).toEqual(["Wax", "Lost-wax casting", "Beeswax"]);
  const inTextiles = withinCategory(searchCatalogue(shared, "wax"), textiles);
  expect(inTextiles.concepts.map((hit) => [hit.concept.label, names(hit.crafts)])).toEqual([["Wax", ["Kutch Ajrakh"]]]);
  expect(names(inTextiles.crafts)).toEqual(["Kutch Ajrakh"]);
  const inMetal = withinCategory(searchCatalogue(shared, "wax"), metal);
  expect(inMetal.concepts.map((hit) => [hit.concept.label, names(hit.crafts)])).toEqual([
    ["Wax", ["Bastar Dhokra"]],
    ["Lost-wax casting", ["Bastar Dhokra"]],
    ["Beeswax", ["Bastar Dhokra"]]
  ]);
  for (const found of [inTextiles, inMetal]) {
    for (const hit of found.concepts) expect(hit.crafts.every((craft) => found.crafts.includes(craft))).toBe(true);
  }
});

test("groups are headed by the family and kind labels, not the master list's taxonomy", () => {
  const body = catalogue();
  const headings = groupCrafts(body, body.crafts).map((group) => group.heading);
  expect(headings).toContain("Textiles · Hand block printing");
  expect(headings).toContain("Metal · Brass and bell metal");
  expect(headings.join(" ")).not.toContain("Craft Category");
  expect(craftIndex(body).bySlug.get("Other-Hand-Block-Print")?.displayName).toBe("Other hand block printing");
});

test("no screen states a craft count of its own", () => {
  const counted = /\b\d{2,4}\s+crafts?\b/i;
  const offenders = ["app", "components", "lib"]
    .flatMap((folder) => sources(join(FRONTEND, folder)))
    .filter((path) => counted.test(readFileSync(path, "utf8")));
  expect(offenders).toEqual([]);
});

test("public data is fetched anonymously, tagged for the cache, and never carries the session", async () => {
  const { calls, fetcher } = recorder(() => json(golden()));
  const result = await publicFetch("/crafts/catalogue", { parse: parseCraftCatalogue, tags: ["craft-catalogue"], deps: { fetcher, env: ENV } });
  expect(result.ok).toBe(true);
  expect(calls).toHaveLength(1);
  expect(calls[0].url).toBe("https://api.example.test/api/crafts/catalogue");
  const headers = new Headers(calls[0].init.headers);
  expect(headers.has("authorization")).toBe(false);
  expect(headers.has("cookie")).toBe(false);
  expect(calls[0].init.next).toEqual({ tags: ["craft-catalogue"], revalidate: 300 });
  const proxied = recorder(() => json(golden()));
  await publicFetch("/crafts/catalogue", { parse: parseCraftCatalogue, tags: [], deps: { fetcher: proxied.fetcher, env: { ...ENV, WEB_PROXY_SECRET: "proxy" } } });
  const sent = new Headers(proxied.calls[0].init.headers);
  expect(sent.get("x-web-proxy-secret")).toBe("proxy");
  expect(sent.has("x-viewer-address")).toBe(false);
});

test("only the web server's own reads come without a viewer address", () => {
  const source = { ...ENV, WEB_PROXY_SECRET: "proxy" };
  const browser = (headers: Record<string, string>) => new Request("https://kalavigyan.example/api/crafts/catalogue", { headers });
  expect(upstreamHeaders(browser({ "x-real-ip": "203.0.113.9" }), null, source).get("x-viewer-address")).toBe("203.0.113.9");
  expect(upstreamHeaders(browser({ "x-forwarded-for": "198.51.100.4, 10.0.0.1" }), null, source).get("x-viewer-address")).toBe("198.51.100.4");
  expect(upstreamHeaders(browser({}), null, source).get("x-viewer-address")).toBe(UNKNOWN_VIEWER);
  const unsigned = upstreamHeaders(browser({ "x-real-ip": "203.0.113.9" }), null, ENV);
  expect([unsigned.has("x-web-proxy-secret"), unsigned.has("x-viewer-address")]).toEqual([false, false]);
});

test("a slow or unready backend gives a fallback result instead of hanging the page", async () => {
  const hanging = (async (_url: string | URL | Request, init?: RequestInit) =>
    new Promise<Response>((_resolve, reject) => init?.signal?.addEventListener("abort", () => reject(init.signal?.reason)))) as typeof fetch;
  const slow = await publicFetch("/crafts/catalogue", { parse: parseCraftCatalogue, tags: [], deps: { fetcher: hanging, env: ENV, timeoutMs: 20 } });
  expect(slow).toEqual({ ok: false, failure: "timeout", status: null });
  const down = recorder(() => json({ detail: "busy" }, 503));
  expect(await publicFetch("/crafts/catalogue", { parse: parseCraftCatalogue, tags: [], deps: { fetcher: down.fetcher, env: ENV } })).toEqual({
    ok: false,
    failure: "failed",
    status: 503
  });
  const wrong = recorder(() => json({ crafts: [] }));
  const original = console.error;
  console.error = () => undefined;
  try {
    const off = await publicFetch("/crafts/catalogue", { parse: parseCraftCatalogue, tags: [], deps: { fetcher: wrong.fetcher, env: ENV } });
    expect(off).toEqual({ ok: false, failure: "invalid", status: 200 });
  } finally {
    console.error = original;
  }
  expect(await publicFetch("/crafts/catalogue", { parse: parseCraftCatalogue, tags: [], deps: { fetcher: wrong.fetcher, env: { NODE_ENV: "production" } } })).toEqual({
    ok: false,
    failure: "unconfigured",
    status: null
  });
});

test("signed-in data forwards the reader's session and nothing is sent without one", async () => {
  const secure = recorder(() => json({ ok: true }));
  const parse = (body: unknown) => body;
  const request = visitor("kalavigyan.example", { [SESSION_COOKIE]: "token-a", [INSECURE_SESSION_COOKIE]: "token-b" }, "https");
  await signedInFetch("/saved", { parse, request, deps: { fetcher: secure.fetcher, env: { ...ENV, WEB_PROXY_SECRET: "proxy" } } });
  const sent = new Headers(secure.calls[0].init.headers);
  expect(sent.get("authorization")).toBe("Bearer token-a");
  expect(sent.get("x-viewer-address")).toBe("203.0.113.9");
  expect(secure.calls[0].init.cache).toBe("no-store");
  const local = recorder(() => json({ ok: true }));
  await signedInFetch("/saved", { parse, request: visitor("192.168.1.5:3000", { [INSECURE_SESSION_COOKIE]: "token-b" }), deps: { fetcher: local.fetcher, env: ENV } });
  expect(new Headers(local.calls[0].init.headers).get("authorization")).toBe("Bearer token-b");
  const hidden = recorder(() => json({ ok: true }));
  const unplaced: IncomingRequest = { headers: new Headers({ host: "kalavigyan.example", "x-forwarded-proto": "https" }), cookie: () => "token-c" };
  await signedInFetch("/saved", { parse, request: unplaced, deps: { fetcher: hidden.fetcher, env: { ...ENV, WEB_PROXY_SECRET: "proxy" } } });
  expect(new Headers(hidden.calls[0].init.headers).get("x-viewer-address")).toBe(UNKNOWN_VIEWER);
  const nobody = recorder(() => json({ ok: true }));
  expect(await signedInFetch("/saved", { parse, request: visitor("kalavigyan.example", {}, "https"), deps: { fetcher: nobody.fetcher, env: ENV } })).toEqual({
    ok: false,
    failure: "refused",
    status: 401
  });
  expect(nobody.calls).toEqual([]);
  const refused = recorder(() => json({ detail: "Sign in to continue." }, 401));
  expect(await signedInFetch("/saved", { parse, request, deps: { fetcher: refused.fetcher, env: ENV } })).toEqual({ ok: false, failure: "refused", status: 401 });
});
