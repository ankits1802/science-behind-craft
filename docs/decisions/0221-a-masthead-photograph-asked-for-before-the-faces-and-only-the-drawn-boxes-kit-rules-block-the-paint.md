# 0221. A page asks for its masthead photograph before its faces, and only the kit rules of the boxes it draws block its first paint

The five Latin files the first screens draw are declared and preloaded by the page instead of by
`next/font`, so the head asks for the masthead photograph first and the faces after it. The kit
stylesheet no longer blocks the first paint whole: a page links one first sheet, the kit less every
rule that needs a box the server does not draw, and the whole kit follows once the page has
hydrated and before the rest of a split page is drawn.

Date: 2026-11-25. Status: accepted (the lead's lane `phone` of the leftovers round; the owner,
2026-11-25, said to fix the open issues too). It amends
[decision 0209](0209-a-phone-load-s-path-to-its-first-screen-recorded-and-cut.md) (what it left: the
faces ahead of the photograph and the kit stylesheet's split; the phone budget it recorded) and
[decision 0177](0177-differences-named-and-the-monograph-shell-measured.md) (who preloads the
first-screen faces). The contract is `docs/contracts/monograph-renderer.md` (The page); the faces
are `frontend/app/latinFonts.ts` and `app/FirstScreenFaces.tsx`, the first sheet
`frontend/lib/kitFirstSheet.ts`, `components/monograph/kitFirstScopes.ts`,
`lib/kitShellScopes.ts` and the sheet's route.

| For | Read |
|---|---|
| The phone budget, its pages and its limits | [decision 0205](0205-a-page-measured-on-a-slowed-phone-held-to-its-budget-and-heavy-kinds-loaded-near.md) |
| The path record and the cuts before these | [decision 0209](0209-a-phone-load-s-path-to-its-first-screen-recorded-and-cut.md) |
| The first-screen faces every page preloads | [decision 0177](0177-differences-named-and-the-monograph-shell-measured.md), `frontend/e2e/first-screen-fonts.smoke.spec.ts` |
| The approved page's kit and its scopes | [decision 0100](0100-ajrakh-monograph-served-as-built.md), `docs/contracts/monograph-document.md` (The kit) |
| What is still slow | `docs/TECH_DEBT.md`: Speed left after the quality lane |
| Every decision, by group | [README.md](README.md) |

## Context

- **React writes a page's font preloads first.** Its head is written in a fixed order: the
  preconnects, the font preloads, the high-priority image preloads, the stylesheets, the scripts,
  the other preloads and then the hoisted elements. `next/font` preloads each face it is told to
  through React, so the five first-screen faces (336 KB) were asked for before the masthead
  photograph and, on the smoke server's six HTTP/1.1 connections, the photograph had one only at
  about 1.7 s (decision 0209: first byte 2,367 ms, done 4,189 ms, largest element 4,612 ms).
- **A server component's preload is a font preload too.** The first attempt declared the faces in
  the page and drew their `link rel="preload"` from the root layout, a server component; React's
  server renderer turns such a link into a preload hint, which the HTML renderer writes in the same
  font queue. Run 45597927206 measured it: the faces still first, all five on a connection at once,
  the app's stylesheets waiting behind them, the first paint at 4,428 ms and the largest element at
  4,612 ms.
- **The kit stylesheet blocked the paint whole.** `monograph.css` is 526 KB (84.6 KB compressed) and
  was the last of four render-blocking sheets; with the faces moved it ended at 3,227 ms and the
  first paint, at 3,276 ms, waited for it (run 45601600699). Most of it styles boxes a page draws
  only further down. Its rules are a global head, six sections each scoped to one box
  (`.bx-chem`, `.bx-pt`, `.bx-rm`, `.bx-mb`, `.bx-ask`, `.bx-sa`) and a global tail, and a page's lead
  (its masthead and first chapter) holds any of the six, so no one subset serves every page.
- **A split by section reorders the cascade.** Some 29,000 pairs of rules share a property and a
  specificity across a scoped section and a later global rule, so loading the sections apart, in
  another order than the kit's, could change which rule wins wherever an element matches both.

## Decision

1. **The first-screen faces are the page's own.** `FIRST_SCREEN_FACES` in `app/latinFonts.ts`
   declares Newsreader roman and italic Latin and Plex Sans 400, 500 and 600 Latin-1 with their
   ranges, weights and styles, each file imported as an asset (`turbopackModuleType: "asset"`, so
   its address is the content-hashed file `next/font` served before); `app/FirstScreenFaces.tsx`
   writes their `@font-face` rules and the two metric-matched fallback faces
   (`lib/pageFaces.faceRules`) as a React style resource, and draws their preloads from a client
   component (`app/FacePreloads.tsx`), so React writes them as hoisted elements at the end of the
   head, after the photograph's preload, the stylesheets and the scripts. The fallbacks keep the
   names the type tokens use and the metrics `next/font` measured (Newsreader over Times New Roman
   73.61, 26.54, 0 and 99.84 per cent; Plex over Arial 101.35, 27.19, 0 and 101.13), and
   `tools/tests/test_webfonts.py` measures them again from the font files. `next/font` keeps every
   other face, none preloaded. The faces drawn, their files and their ranges are unchanged.
2. **The design guard reads `font-display` as the retired class only.** Its alias rule no longer
   counts the `@font-face` descriptor of that name, which a class is never written as (a colon
   follows it).
3. **A page links one first sheet for the boxes it draws.** `documentScopes`
   (`components/monograph/kitFirstScopes.ts`) and `shellScopes` (`lib/kitShellScopes.ts`) read
   from what the server draws (the chapters of the lead, or all of them when nothing is deferred;
   the lead's shell nodes) the scopes of its boxes:
   the masthead (`mb`), the contents and a sub-rail (`chem`), each passage (`pt`), each drawn slot's
   home and every box in its fragments, and the sources (`rm`). `MonographFrame` links
   `/monographs/kit/first/<scopes>.css`, named in the kit's order, served by
   `app/monographs/kit/first/[sheet]/route.ts` from the served kit through `lib/kitFirstSheet`: the
   kit's own text, in its order, less every rule whose every selector needs, outside a negation, a
   box the page does not draw, and less every grouping rule left empty. Any other name is a 404.
   Drawing every scope gives the kit back byte for byte.
4. **The whole kit follows, and the rest waits for it.** `KitRestSheet` adds the kit as a React
   stylesheet of its own precedence once the page has hydrated, and the drawn rest of a split page
   links it too, so its transition commits only when the kit has loaded. The first sheet is a
   subsequence of the kit and the kit comes after it, so every element is styled as by the kit
   alone once both have loaded, and every box the server drew was already styled so by the first
   sheet: the kit's arrival moves nothing.
5. **The budget is recorded at the new numbers** of run 45608217451 on cd9c2115, the lane's code
   whole: Kutch Ajrakh 700,893 bytes of JavaScript, 173,663 of CSS, 73,696 of first-screen pictures,
   its largest element at 2,772 ms, 351 ms blocked, 0.0293 of shift loading and none reading; the
   page of every kind 719,135, 190,219 and 73,696 bytes, 2,936 ms, 146 ms, 0.0293 and 0. The bytes
   are the cut's run's to the byte; the time blocked after the paint moved from 183 to 351 ms on
   Kutch Ajrakh between the two runs of the same code, so the record keeps the later, higher one.
   The CSS grows by the first sheet, deliberately (Consequences).

## Consequences

- **What each cut bought** (the median of three loads):

  | Kutch Ajrakh | Before (45545594071) | Faces by a server component (45597927206) | Faces after the photograph (45601600699) | And the first sheet (45604791573) |
  |---|---|---|---|---|
  | Photograph's first byte, done | 2,367 ms, 4,189 ms | 2,371 ms, 4,184 ms | 1,157 ms, 2,965 ms | 1,156 ms, 2,766 ms |
  | Render-blocking CSS, done | 121.6 KB, 4,372 ms | 121.2 KB, 4,358 ms | 121.2 KB, 3,228 ms | 77.0 KB, 2,058 ms |
  | First paint | 4,452 ms | 4,428 ms | 3,276 ms | 2,092 ms |
  | Largest element | 4,612 ms | 4,612 ms | 3,444 ms | 2,788 ms |
  | Main thread blocked | 398 ms | 452 ms | 233 ms | 183 ms |
  | CSS sent | 133,824 B | 133,454 B | 133,454 B | 173,663 B |

  The page of every kind went from 4,568 to 4,576, 3,404 and 2,920 ms, and from 194 to 197, 78 and
  80 ms blocked; its first sheet holds three sections (`chem-pt-mb.css`, 55.8 KB), so its
  render-blocking CSS is 93.1 KB and its CSS sent 190,219 B. Neither page's layout shift moved
  (0.0293 loading, none reading), and every smoke spec, the native and template parity at three
  widths in both themes among them, passed on the split page.

- **Where the time goes now.** Both pages now paint first at 2.1 and 2.6 s, as soon as
  their four render-blocking sheets end, and the photograph has a connection at once (its first
  byte, 562.5 ms of it the throttle's latency, at 1.16 s). It ends at 2.77 and 2.86 s because it
  shares the 1.47 Mbit/s with both Newsreader faces (270 KB), which are asked for after it but, at
  High priority, take the next free connections ahead of the scripts, and with the first sheet and
  the app's sheets. Kutch Ajrakh is 0.29 s over the 2.5 s target and the page of every kind 0.42 s;
  what would close it is in the debt entry: the faces' priority or Newsreader italic's preload (both
  the design's choice, since a first screen would draw in its fallback faces until after the
  photograph) and, for a lead of several sections, a first sheet narrower than its sections.
- **The cost.** A cold load sends the first sheet besides the whole kit (39.2 KB more
  CSS on Kutch Ajrakh, 55.8 KB on the page of every kind), since the kit still follows whole: it is
  one file cached across every page, where a remainder sheet would differ with each page's scopes and
  could only be ordered after the first sheet, which would let a scoped rule beat the global rule
  the kit puts after it. The kit is asked for after hydration, so it no longer shares the network
  with the photograph. A first sheet is built on its first request and kept until the next deploy;
  its route reads the served kit from the deployment (`outputFileTracingIncludes` in
  `next.config.ts`).
- **A component that draws a box names it.** A `bx-<scope>` box drawn by a component the scope
  reader does not know draws without its kit rules until the kit arrives after hydration;
  `kit-first-scopes-unit.spec.ts` renders Kutch Ajrakh, the phone fixtures, a generated page and the
  page of every kind, whole and split, and fails on a drawn box its page's sheet leaves out, and the
  design skill's trap index says so.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[RUNBOOK](../RUNBOOK.md) (Phone budget). Its rules are tested by
`frontend/e2e/page-faces-unit.spec.ts` (the faces' rules and preloads, no face preloaded by
`next/font`, a head read in the order it asks), `frontend/e2e/first-screen-fonts.smoke.spec.ts`
(every face a first screen draws preloaded, and the photograph asked for before any face, against
the built site), `tools/tests/test_webfonts.py` (the fallback metrics measured from the files),
`frontend/e2e/design-guard-unit.spec.ts` (the retired class counted, the descriptor not),
`frontend/e2e/kit-first-sheet-unit.spec.ts` (what a first sheet keeps and leaves, the kit given back
whole, its names, its route and the file traced for it), `frontend/e2e/kit-first-scopes-unit.spec.ts`
(every drawn box in its page's sheet, a box only the rest draws left out, the whole kit never linked
by the server) and `frontend/e2e/phone-budget.spec.ts` (the pages within their recorded budget).
