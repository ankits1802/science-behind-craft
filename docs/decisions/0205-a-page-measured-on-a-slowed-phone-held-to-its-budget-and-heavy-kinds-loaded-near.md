# 0205. A page is measured on a slowed phone in CI and held to its recorded budget, naming what grew, and a heavy kind's code loads as it nears the viewport after its still state

The Frontend checks' smoke job loads Kutch Ajrakh and a page that holds every contributable kind at
360 on a phone whose CPU is slowed four times and whose network is Lighthouse's slow 4G, records what
each sends and how soon and how steadily its first screen is drawn, and fails when a page passes the
limits drawn from its recorded numbers, naming the scripts, pictures, element or nodes that grew. A
component kind whose code is heavy is drawn whole by the server and sends its code only as its
holder nears the viewport.

Date: 2026-11-25. Status: accepted (the lead's lane `phone-budget` of the page-quality round; the
owner reads on a phone first). It amends
[decision 0177](0177-differences-named-and-the-monograph-shell-measured.md), item 7, which left
what a release gains on a phone to the lead's Lighthouse because CI ran none. The contract is
`docs/contracts/monograph-renderer.md` (Component slots); the measure and the budget are `frontend/e2e/phoneBudget.ts`,
`frontend/e2e/phoneMeasure.ts` and `frontend/e2e/phone-budget.json`, and the loading is
`frontend/components/answer/nearBlock.tsx` with `frontend/components/monograph/kinds/nearViews.tsx`.

| For | Read |
|---|---|
| The production Lighthouse targets and slack the limits reuse | `frontend/e2e/release/auditBudgets.ts`, [decision 0126](0126-measurement-that-grows.md) |
| The lead chapter drawn by the server and the rest read later | [decision 0177](0177-differences-named-and-the-monograph-shell-measured.md), [decision 0183](0183-the-shared-template-draws-the-approved-page.md) |
| The kind fixtures the page of every kind draws | [decision 0114](0114-kinds-and-datasets.md), [decision 0196](0196-a-contributor-s-map-drawn-by-the-site-from-places-it-resolves.md) |
| The design rule: complete at rest, the largest element never at opacity 0 | `.claude/skills/kalavigyan-design`, section 6 |
| Every decision, by group | [README.md](README.md) |

## Context

- **A page built to the Kutch Ajrakh bar is heavy.** It now carries the site's maps with relief and
  rivers, 3D molecules, reaction, dip and stage players, figures composed from the kit with their
  motion, and open-licence photographs. Nothing held a page's weight or its time to a usable first
  screen to a budget; decision 0177 left the phone to the lead's Lighthouse on production, after
  the release.
- **Every kind's code reached the browser with the first one drawn.** The client registry
  `COMPONENT_VIEWS` imported every view outright, so the first app-drawn component on a page, or
  the rest of a page read after its lead chapter, brought the code of all of them: the declared
  timeline map (the answers' map on the base map with its layers, 137 modules and about 510 KB of
  source), the why-here ground map (67 modules, about 310 KB, with the 47 KB neighbours table), the
  declared map layer with India's outline (about 100 KB) and the six page tools, whose generator
  reaches the answer machinery (308 modules, about 1 MB of source).
- **The kit already binds its heaviest motion on approach.** The page kit (`monograph.js`, loaded
  once the page is idle) starts its molecule viewer, region maps and timeline only near the
  viewport (`KV.near`); its players, vats and dips bind as it starts, and several unit specs drive
  them straight after the kit loads, so changing when they bind is not this lane's to make.

## Decision

1. **Two pages are measured on a slowed phone in the Frontend checks.** After the smoke specs, the
   smoke job runs `e2e/phone-budget.spec.ts` alone (`--project=phone-budget`, one worker, so no
   other spec shares the CPU) against the same production build and smoke API. It opens
   `/crafts/Kutch-Ajrakh` and `/crafts/Phone-Fixtures`, a page the smoke API serves through the
   craft page route: the 26 kind fixtures of the 23 contributable kinds as `/design/kinds` places
   them, opened by a masthead with an open-licence photograph (`e2e/phoneFixturePage.ts`; the
   picture is the site's own copy of Kutch Ajrakh's Commons photograph, with its credit, since CI
   reaches no outside site). Each page is opened once to fill the server's cache, then loaded three
   times in a fresh context at 360 by 800 (the matrix's Phone 360, a Pixel 7) with the CPU slowed
   four times and Lighthouse's slow 4G as DevTools applies it (562.5 ms a request, 1,474.56 kbit/s
   down, 675 up), each load waited on until the kit is bound, the rest of the page has arrived and
   no task has run for two seconds; the third load then reads to the end, 0.8 of a screen every
   800 ms, a skim of a screen a second. A load records, from the browser's own network events, the bytes sent of scripts,
   stylesheets, pictures, the document and fonts; the pictures shown in the first screen; the last
   largest contentful paint and its element; every task over 50 ms with the scripts each long
   animation frame ran; and every layout shift with the nodes it moved. The numbers are each
   budgeted metric's median over the three loads (the reading shift is the read's), written per
   page as `phone-measure.json` in the job's artifact and as one line in its log.
2. **The budget is per page and drawn from recorded numbers.** `e2e/phone-budget.json` records,
   per page, `scriptBytes`, `styleBytes`, `firstScreenImageBytes`, `lcpMs`, `blockingMs` (the time
   tasks ran past 50 ms after the first contentful paint, Lighthouse's total blocking time over the
   whole load), `cls` (the worst session window of shifts, a second's gap and five seconds at most,
   as the browser's metric) and `readingShift` (the same over the read), with the run and the date.
   The limits reuse the production audit's targets and slack (`e2e/release/auditBudgets.ts`): bytes
   a tenth over the record; the largest element at 2.5 s or half again its record, whichever is
   later; blocking at 200 ms or twice its record; either shift at 0.1 or 0.05 over its record. A page
   past a limit fails the spec with a sentence naming the page, the number, its limit and record,
   and what grew: the five largest scripts, stylesheets or first-screen pictures, the largest
   element, the scripts that ran longest, or the nodes that moved. A page with no record fails. A
   change that must grow a page records new numbers from its run, in the change that says why.
3. **A heavy import is caught twice.** In the browser, the spec loads Kutch Ajrakh again with the
   build's largest chunk the page does not load added to its document, and passes only when the
   budget fails on its JavaScript naming that chunk. In the source, `e2e/near-views-unit.spec.ts`
   walks the craft route's layouts and page to every client module and from each, and from the
   rest of a page's two chunks, through every runtime import, and fails naming the imports that
   reach a near-loaded view, 3Dmol.js, KaTeX or the ElevenLabs client outright; a fixture registry
   that imports the declared timeline map outright is named with its one import.
4. **A heavy kind sends its code as it nears the viewport, after its still state.** `nearBlock`
   (`components/answer/nearBlock.tsx`, beside `lazyBlock`, whose retry it shares) wraps a view's
   loader in a holder `div[data-kv-near]`. On the server it draws the view whole: the view's module
   is loaded once when the server starts it, and until then the render waits on it, so the page's
   HTML always holds the complete still state. In the browser the view inside the holder is kept
   as the server drew it, unhydrated, until an `IntersectionObserver` sees the holder within
   two screens (1,600 px on a phone 800 px tall); then its chunk loads and it hydrates in place. Where
   the browser draws a part itself (the rest of a page read after its lead chapter), the holder
   shows a figure-shaped skeleton until it nears, then draws the view two screens before the
   reader reaches it. The kinds are the declared map layer and timeline map, the why-here
   ground map and the six page tools (`components/monograph/kinds/nearViews.tsx`, which the family
   registries name), and a composed kit figure's Play (`components/artkit/NearKitPlay.tsx`); a
   stylesheet one of them brings is imported with the loaders, so the still state is styled at
   first paint. The other kinds stay in the registry as they were.

## Consequences

- **The first measure, before the heavy kinds loaded near** (run 45471317370 on 6ab05b42, the
  median of three loads). Kutch Ajrakh sent 788,260 bytes of JavaScript (the largest chunks 83.7,
  72.9 and 44.5 KB, then the kit's `monograph.js`, 44.5 KB), 140,802 bytes of CSS (the kit's
  `monograph.css`, 83.6 KB, render-blocking), 708,770 bytes of pictures of which 73,696 in the
  first screen (the masthead photograph at 960 px through the image service), 683,867 bytes of
  fonts and a 40,472-byte document; its largest element, that photograph, painted at 4,912 ms; the
  main thread was blocked 916 ms, 766 of them in the framework chunk that draws the rest of the
  page and 215 in the kit; its layout moved 0.0293 as it loaded (the app shell's `main`, its page
  nav and brand) and not at all as it was read. The page of every kind sent 804,618 bytes of
  JavaScript and the same CSS and first screen, painted its largest element at 4,896 ms and was
  blocked 334 ms.
- **The measure with the heavy kinds loading near** (run 45475377032 on 290b62a9), which
  `e2e/phone-budget.json` records. Kutch Ajrakh sends 697,810 bytes of JavaScript (90,450 fewer:
  the 83.7 KB chunk that carried every kind's view is gone, although its page draws none of the
  heavy kinds, because the registry no longer brings them), 142,254 bytes of CSS (1,452 more, the
  ground map's stylesheet now on the page before its code), the same first screen and pictures;
  its largest element paints at 4,760 ms and the main thread is blocked 747 ms, 530 of them in the
  framework chunk drawing the rest of the page and 201 in the kit. The page of every kind sends
  715,853 bytes of JavaScript (88,765 fewer) and 73,696 bytes of pictures (81,683 fewer: the maps
  below its first screen load nothing until they near), is blocked 227 ms (107 fewer) and paints
  its largest element at 5,180 ms. Read then at 0.8 of a screen every 300 ms, a fling, with the
  views drawn a screen and a half ahead, it moved by 0.0325 (`section#k26`) in that run and by
  0.7733 in the next (run 45481973342: `section#k26`, `section#sources`), because the fling
  outran the views' code on this network and their reserve was replaced in view; the margin was
  widened to two screens and the read slowed to a skim of a screen a second, and the record was
  taken again (below). With the build's largest chunk it
  does not load added to its document, Kutch Ajrakh sends 865,932 bytes, past its 767,591-byte
  budget, and the spec names `/_next/static/chunks/2np8vbiqedr4p.js` first.
- **A page past its budget fails the pull request**, with the sentence that names what grew, and
  the numbers are in every run's log and artifact for the lead's release notes.
- **What is left.** The kit's players, vats and dips bind as the kit starts, not on approach, and
  the kit is one approved script loaded once the page is idle: splitting it, or binding them near,
  changes the approved page's script and the unit specs that drive it, and waits on a kit-parts
  lane. The render-blocking kit stylesheet stays one file (decision 0177, item 7). A plate's
  Commons picture is still offered at one standard width, 960 px, because no standard size names a
  figure in the reading column; a new size is a design-system decision. The first screen's largest
  element paints after about 4.9 s on this phone, against Lighthouse's 2.5 s target: the budget
  holds it where it is, and bringing it down is the speed entry of the debt register, which the
  lead may now clear or rewrite from these numbers instead of production's Lighthouse.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[RUNBOOK](../RUNBOOK.md) (Phone budget). Its rules are tested by
`frontend/e2e/phone-budget-unit.spec.ts` (the measure, the limits and the named breaches),
`frontend/e2e/phone-budget.spec.ts` (the pages within their budget, and a heavy import refused and
named, in the smoke job) and `frontend/e2e/near-views-unit.spec.ts` (each heavy kind's still state
at first paint, its code reached only near the viewport, its stylesheet on the page first), with
`frontend/e2e/monograph-tools-unit.spec.ts` and `frontend/e2e/art-kit-unit.spec.ts` drawing the
page tools and a kit figure at rest through their near views.
