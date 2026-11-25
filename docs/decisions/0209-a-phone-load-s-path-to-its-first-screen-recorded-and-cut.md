# 0209. A phone load's path to its first screen is recorded, the views' stylesheets load as one sheet, a masthead's photograph is asked for first, and the rest of a page is drawn in a transition

The phone budget's run now records, for every load, the path to its largest element: every request
started before it with the priority Chrome gave it and when it was asked for, answered and done,
the requests that shared the network with the picture, and the main thread's work before the
paint. Read from that record, three cuts were kept: the views' stylesheets are one sheet of the
root layout instead of a request each; a page's masthead photograph is always the picture the
document's head asks for first; and the rest of a page read after its lead is drawn in a React
transition that yields. A fourth, binding the kit's players and dips as they near the screen, was
measured, bought nothing and was not kept.

Date: 2026-11-25. Status: accepted (the lead's lane `phone-lcp` of the page-quality round; the
owner, 2026-11-25, said to build what decision 0205 left). It amends
[decision 0205](0205-a-page-measured-on-a-slowed-phone-held-to-its-budget-and-heavy-kinds-loaded-near.md)
(what is left; the record the run keeps; a heavy view's stylesheet, which no view now imports) and
the phone budget it records. The contract is `docs/contracts/monograph-renderer.md` (Component
slots); the record is `frontend/e2e/phonePath.ts`, the sheet `frontend/app/component-views.css`.

| For | Read |
|---|---|
| The measure, the limits and the pages | [decision 0205](0205-a-page-measured-on-a-slowed-phone-held-to-its-budget-and-heavy-kinds-loaded-near.md) |
| The first-screen faces every page preloads | [decision 0177](0177-differences-named-and-the-monograph-shell-measured.md), `frontend/e2e/first-screen-fonts.smoke.spec.ts` |
| The approved page's kit, its script and stylesheet | [decision 0100](0100-ajrakh-monograph-served-as-built.md), `docs/contracts/monograph-document.md` (The authored files) |
| What is still slow | `docs/TECH_DEBT.md`: Speed left after the quality lane |
| Every decision, by group | [README.md](README.md) |

## Context

- **The largest element waited on the network, not the main thread.** The first record (run
  45536780822 on 58729a67, the code of main) shows, on all three loads of both pages, no long task
  before the masthead photograph painted. Kutch Ajrakh's document arrived at 564 to 777 ms and
  asked for everything in its head within 40 ms: the five preloaded faces, the photograph's preload
  (`High`), ten render-blocking stylesheets (`VeryHigh`) and about 25 scripts (`Low`). The smoke
  server speaks HTTP/1.1, so the browser holds six connections to it, and DevTools' slow 4G adds
  562.5 ms to every request: a request's first byte, less 562.5 ms, is when a connection was free
  for it, and each connection serves its queue one request after another, highest priority first
  and, within a priority, in the order asked. The photograph was the sixteenth: after the
  document, ten stylesheets (seven of them 332 to 1,330 bytes) and the five faces, it had a
  connection at 2,265 ms, its first byte at 2,827 and its last at 4,760, while 38 other requests
  (804 KB, 270 KB of it the two Newsreader faces) shared the 1.47 Mbit/s. The first paint waited
  for the last stylesheet, the kit's (84.6 KB), done at 3,742 ms.
- **Each view brought its own stylesheet.** Seven components the craft page draws (the ground map,
  the general kinds, their themes, the art kit, the authored shell, the document's languages and
  page) imported a stylesheet, and Turbopack served each as a file of its own, so each cost the
  page a connection's turn.
- **A generated page's masthead photograph was not marked first.** Kutch Ajrakh's authored spec
  asks `fetchPriority: "high"`; a spec the server composes, and the page of every kind's, asks
  nothing, so React's preload of the photograph went out without it.
- **The rest of a page was drawn in one task.** `DeferredShellSlot` set the rest it had read as an
  ordinary update, which React renders without yielding: on Kutch Ajrakh the framework chunk ran
  for 621 ms in long frames as it drew the rest.

## Decision

1. **The run records each load's path to its largest element.** `phoneLoad` reads every resource
   timing (start, first byte, end, bytes, render-blocking or not) and the navigation's, the
   priority each request was given and last changed to (`Network.requestWillBeSent`,
   `Network.resourceChangedPriority`) and the start of every script a long animation frame ran.
   `paintPath` (`e2e/phonePath.ts`) turns a load into the largest element's time and node, the first
   paint, the document's first byte and end, every request started before the paint, the
   render-blocking ones, the fonts, the picture's own request, the requests that overlapped it (the
   eight heaviest named, all counted and summed) and the long tasks before the paint with the scripts
   that ran them. The spec keeps the three loads' paths in `phone-measure.json` (`paths`) and logs
   one line per load. It is a record, not a limit: the budget still judges the numbers alone.
2. **No view imports a stylesheet; the root layout loads them as one sheet.**
   `app/component-views.css` `@import`s the seven stylesheets the craft page linked, in their order,
   then the answer block's, and the root layout imports it after `globals.css`, so they keep their place in the
   cascade after the app's own rules and before the kit's. A new component's stylesheet joins it;
   `e2e/component-styles-unit.spec.ts` holds every stylesheet under `components/` to one of the
   layout's two sheets, and `e2e/near-views-unit.spec.ts` that no view, near-loaded or not, reaches
   one of its own.
3. **A masthead's photograph is asked for first.** `shownPage` gives the spec of the picture the
   plan places in the masthead (`mastheadPictureLabel`) `fetchPriority: "high"` and no `loading`,
   whatever the stored spec says, and changes no other spec; React then preloads it from the head
   with its widths and sizes, as it already did Kutch Ajrakh's, so the phone asks for the 960 px
   picture it draws and nothing else first.
4. **The rest of a page is drawn in a transition.** `DeferredShellSlot` sets the rest inside
   `startTransition`, so React renders it in slices and the reader's input is answered between them;
   the page, its order and its announcements are unchanged.
5. **The kit binds its players and dips as it starts, as the approved page does.** Binding them as
   they neared the screen, or when pressed, was built and measured (run 45542944823): the kit's
   long frames on Kutch Ajrakh ran 176 ms against 164 ms the run before, within a run's noise, since
   what the kit costs at start is its own start-up, not its players. It was reverted, so the approved
   page's script is unchanged.
6. **The budget is recorded at the new numbers** of run 45545594071 on 1750e824: Kutch Ajrakh
   698,254 bytes of JavaScript, 133,824 of CSS, 73,696 of first-screen pictures, its largest element
   at 4,612 ms, 398 ms blocked, 0.0293 of shift loading and none reading; the page of every kind
   716,397, 133,824 and 73,696 bytes, 4,568 ms, 194 ms, 0.0293 and 0.

## Consequences

- **What each cut bought** (the median of three loads; the times move from run to run by up to a
  few hundred ms on a shared runner, the requests do not):

  | Kutch Ajrakh | Before (45536780822) | One sheet (45540824695) | Masthead first, rest in a transition (45545594071) |
  |---|---|---|---|
  | Render-blocking requests | 10, 124.4 KB | 4, 121.6 KB | 4, 121.6 KB |
  | Picture's first byte, done | 2,827 ms, 4,760 ms | 2,309 ms, 4,202 ms | 2,367 ms, 4,189 ms |
  | First paint | 3,808 ms | 4,388 ms | 4,452 ms |
  | Largest element | 4,784 ms | 4,560 ms | 4,612 ms |
  | Main thread blocked | 733 ms | 678 ms | 398 ms |
  | CSS sent | 142,249 B | 133,824 B | 133,824 B |

  The page of every kind went from 4,556 to 4,508 and 4,568 ms and from 216 to 172 and
  194 ms blocked. Seven fewer stylesheet requests gave the photograph a connection about
  520 ms sooner; it finished about 560 ms sooner, but the first paint moved later in two loads of
  three, because the connections freed went to scripts that then shared the kit stylesheet's
  transfer. The transition took the framework chunk's long frames on Kutch Ajrakh from 621 ms to
  275 and 332 ms in the two runs that carried it. Marking the masthead's photograph first moved
  neither page here (Chrome had raised the page of every kind's photograph to `High` before a
  connection was free for it); it keeps a generated page's photograph ahead of its scripts from the
  first byte.
- **2.5 s is not reached on either page; the floor is about 4.5 s, and the network holds it.** No
  long task runs before the paint. The photograph is still asked for after the five preloaded faces,
  because React writes font preloads into the head before image preloads and the browser serves a
  priority's requests in the order asked: it has a connection only when the Newsreader roman face
  (127.7 KB) has one, at about 1,750 ms, and then shares 1.47 Mbit/s with both Newsreader faces
  (270.4 KB), the kit stylesheet (84.6 KB) and the first scripts until about 4.2 s; the kit
  stylesheet, render-blocking and served after the app's three, ends at 2.9 to 4.4 s. Everything
  the first paint waits on or shares the network with comes to about 680 KB, 3.6 s at this speed.
  What would move it is named in the debt entry: the photograph asked for before the faces (which
  needs the faces preloaded by the page rather than by `next/font`), fewer or smaller first-screen
  faces (Newsreader italic, 142.8 KB, is preloaded for one caption line on Kutch Ajrakh's first
  screen), and the kit stylesheet split so only what a page's lead draws blocks its paint (a
  page's lead holds any of the kit's six scopes, and the stylesheet interleaves them, so the split
  is per page).
- **The approved page looks and answers the same.** Its fragments, its kit and its static page are
  unchanged; its stylesheets are the same rules in the same order, one request instead of seven.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[RUNBOOK](../RUNBOOK.md) (Phone budget). Its rules are tested by
`frontend/e2e/phone-path-unit.spec.ts` (the path, its requests, the picture and what shared the
network, the work before the paint), `frontend/e2e/component-styles-unit.spec.ts` and
`frontend/e2e/near-views-unit.spec.ts` (every component stylesheet in one of the layout's two
sheets, none reached by a view), `frontend/e2e/masthead-preload-unit.spec.ts` (the masthead's
photograph preloaded first, and no picture first on a page without one) and
`frontend/e2e/phone-budget.spec.ts` (the pages within their recorded budget, in the smoke job).
