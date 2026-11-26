# 0231. A contributor's AI writes a figure's code over the page's cited data, and the site runs it sandboxed, still under reduced motion and inside the phone budget

A contributor's AI may deliver a `coded_figure`: its own HTML, CSS and script beside the values and
cited units it shows. The site runs the code in the sandboxed frame the answers' explainers use
(scripts only, no same origin, no network but the pinned libraries the spec names), hands it the
page's design tokens, its values, the words of its units and, for a map, the site's own base with
the Survey of India outline, and draws a still of it for paper and the first paint. Delivery refuses
a coded figure only when a fact it states is not the page's, when it reaches past its frame, when it
would not rest still and complete under reduced motion or has no still, or when it is past its
budget, each with the reason the agent can act on. It is never refused for its look.

Date: 2026-11-26. Status: accepted (the UX round of 2026-11-26, lane `coded-figures`,
`.lead/tools/lanes/ux-1126/coded-figures.md`, widened the same day by the owner's direction relayed
by the lead: real libraries, films, figures as large as a section, free labels and controls, and
only the hard rules below). It amends
[decision 0059](0059-sandbox-and-what-if-renderers.md) (the sandbox now runs a contributor's code,
its safety rules apart from its number rules),
[decision 0114](0114-kinds-and-datasets.md) (a twenty-fourth contributable kind),
[decision 0131](0131-drawings-in-the-design.md) (a coded figure reaches for the tokens and is not
refused for its look),
[decision 0206](0206-every-new-kind-exported-as-its-still-and-read-in-a-page-s-languages.md) (the
export draws the new kind's still) and
[decision 0218](0218-an-explainer-s-frame-still-from-its-first-paint-a-paint-read-through-its-variables-and-a-drawing-kept-to-its-box.md)
(the frame's stillness also holds a film). The contracts are `docs/contracts/component-specs-science.md`
(coded_figure), `docs/contracts/component-specs-general.md` and the contributor's
`references/components.md`.

| For | Read |
|---|---|
| The frame, its policy and its data channel | [decision 0059](0059-sandbox-and-what-if-renderers.md), [decision 0218](0218-an-explainer-s-frame-still-from-its-first-paint-a-paint-read-through-its-variables-and-a-drawing-kept-to-its-box.md) |
| The contributable kinds and their fixtures | [decision 0114](0114-kinds-and-datasets.md) |
| The drawing bar this kind is not held to | [decision 0131](0131-drawings-in-the-design.md), [decision 0215](0215-every-searched-picture-served-names-its-craft-s-world-and-every-drawing-is-judged-by-the-paint-a-reader-sees.md) |
| Stills on paper | [decision 0206](0206-every-new-kind-exported-as-its-still-and-read-in-a-page-s-languages.md) |
| The phone budget and loading near the viewport | [decision 0205](0205-a-page-measured-on-a-slowed-phone-held-to-its-budget-and-heavy-kinds-loaded-near.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **What Kutch Ajrakh has, a contributor could not build.** Ajrakh is rich because developer
  sessions wrote its HTML, CSS and JavaScript, three.js interactives and short films among them. A
  contributor's AI could only fill specs of a fixed set of kinds, so a molecule that moves, a bond
  that breaks, a route that animates on a map or a stage scene that moves could not be built at all;
  a contributor's map was four dots. The owner: "At the end of the day, we only need structured
  data, and then obviously that same data can be used in the HTML as well", and the platform's only
  job is to guarantee the research and the citations.
- **The pieces existed for answers.** A generated explainer's HTML runs in a frame drawn with
  `sandbox="allow-scripts"`, a policy of no network and its values passed in (`SimulationBlock`,
  `SandboxFrame`, `lib/sandboxFrame`), held still under either reduced-motion switch (decision
  0218), and checked by `sandbox_problems`. `model_explainer` draws Kutch Ajrakh's one authored
  explainer.

## Decision

1. **A new kind, not `model_explainer` opened.** `coded_figure` (`research/component_specs_science_coded`,
   in the science group; migration `0121_coded_figures` widens the two kind checks). Of the two ways
   the brief offered, this takes the new kind: `model_explainer`'s spec is the extraction of one
   authored figure (its stills, badge, slider and key drawn by hand, its document a whole page whose
   text and numbers are its own and that no check reads), so opening it would give one kind two
   meanings and put Ajrakh's parity at stake, while the new kind's spec states exactly what a
   contributor sends: `head`, `alt`, `code`, `values {key, value, reading}`, `texts {key, unit}`,
   `libraries`, `map {layers, districts}`, `films {key, src}` and an optional `still`.
2. **The hard rules, and only those, refuse it at delivery** (`research/coded_figure_code`,
   `coded_figure_still`), every reason in one sentence:
   - *Facts are the page's.* A number the figure shows (in its markup, a text attribute, a
     stylesheet's `content`, a prose string in its script, or its still) is one of its values, each
     stated by its cited `reading`, or a counting number up to 12; a run of free text longer than a
     label (80 characters and six words) is a sentence, which is a unit shown by `data-unit`. A key
     the code names is one its `texts` or `films` hold. Labels, controls and decoration are free
     text, and the code's own geometry and colours are free: the sandbox's rule that every numeral
     in a script is a value is kept for generated explainers and not applied here
     (`sandbox_safety_problems` beside `sandbox_problems`).
   - *It runs sandboxed.* The sandbox's safety rules (no network, storage, cookie, other window,
     navigation, nested frame, loaded script or address), the frame's reserved ids, and a library
     only from the pinned list, served from the site's own origin. The frame's policy allows those
     library files and the named films and nothing else, and the frame has no same origin.
   - *It rests still and complete.* A script that times motion reads the frame's
     `data-reduced-motion` flag, so it can draw its last state at once, since under either switch no
     timer, animation frame, animation or film plays. A still exists: the code's one `svg`, cut by
     the server, or a `still` the agent sends (a canvas or WebGL figure must).
   - *It keeps the budget.* The code is at most 64 KiB, which a chapter-sized SVG scene and its
     script fit while the page's document stays within the phone budget's margin; libraries load
     only in the frame, and the frame only within two screens of the viewport.
   A hand-drawn map is refused as for every drawing (`drawn_maps`), unless the figure declares
   `map`, whose base and outline the site draws.
3. **Its look is not judged.** The design's drawing bar (`simulation_art`, `drawn_art`) is not
   applied. The frame is handed the kit: the tokens the code and the kit sheet name, read from the
   page in the reader's theme, and a small sheet that draws buttons, focus, status and the map's
   layers in the design (`lib/codedFigureFrame.FRAME_KIT_SHEET`).
4. **Words and films are filled by the frame, not the code.** The page passes the units' plain words
   (`kv-words`) and the films' addresses (`kv-films`); the frame's own script puts a unit's words in
   every element with `data-unit`, its label in `data-unit-label`, and a film's address in
   `data-film`, and does so again whenever the code changes which key an element names. Every unit
   the figure shows is also listed beneath it with its citations ("Words and sources in this
   figure"), so each fact carries its sources.
5. **Pinned libraries from the kit.** `d3` 7.9.2 and `three` 0.187.0 are vendored in
   `frontend/public/monographs/kit/vendor/` with their licences, three bundled once as a classic
   script with the global `THREE` (its package ships only modules). The frame loads them by
   `<script src>` from the site's own origin, which the frame's policy names file by file, before the
   figure's code. They are exempt from the comment rule and from lint as vendored code.
6. **Maps on the site's base.** A figure that declares `map {layers, districts}` gets, in the frame,
   the base the site draws: the Survey of India outline, the Rann, and the state and district lines,
   rivers and relief bands it names, in the India frame of `components/map/projection.ts`, with the
   craft's districts outlined. `kvMap.project(longitude, latitude)` and `kvMap.box(...)` match the
   site's projection, `kvMap.places` gives each named district's centre, and the frame draws the base
   into every `svg[data-map]` and draws it again if the code removes it, so a coded map cannot leave
   the outline out.
7. **At rest, lazy, a still, keyboard.** On the page the server draws the still (four theme
   variants, its words filled from the units) and loads the frame's code when the figure nears the
   viewport (`NearCodedFrame`, decision 0205), starting the frame at the still's height; the frame is
   reached by Tab like any frame and its controls are the code's buttons. The export draws the
   still with the figure's words beneath it (`services/page_export_coded`). The Review page shows
   the still beside a live run (`components/review/CodedFigureReview`), and preview_page draws and
   judges it as any component of the interactive role.
8. **The owner's direction overrides the design skill here.** A coded figure may move on its own
   when neither reduced-motion switch is on (the design's rule is motion on request only), may use
   any colour or face it chooses, and may carry free labels. Under either switch it rests, and the
   frame enforces it; a visible pause is the guidance, not a refusal.

## Consequences

- Twenty-four kinds are contributable; Bidriware's patina bath is the fixture (two salts weighed,
  dissolved and the alloy blackened, every number a cited value).
- A coded figure counts as an interactive in the preview's comparison with Kutch Ajrakh.
- The answers' generated explainers keep every rule they had; the stillness script now also holds a
  film still under either switch.
- **What is left.** A still of a map figure, on the page and on paper, holds the figure's own marks
  but not the base, which only the frame draws; the maps lane brings the outline to the still. A
  film is one the site serves under `/monographs/`; a clip in the media store needs its signed
  address passed in. A figure taller than the frame's largest height (1,200 px) scrolls inside it.
  A fact stated in a short label or a number up to 12 is not caught by delivery and is left to the
  Review page.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by `backend/tests/research/test_coded_figures.py`
(a figure that fetches, navigates, reads a cookie or storage, loads a script, shows a number or a
sentence of its own, times motion without the flag, has no still, names a key it does not hold,
declares a map with no base or hand-draws one, or passes its budget is refused with its reason; one
that draws from its data is accepted with free labels, its still cut and served in four themes),
`backend/tests/exports/test_coded_figure_export.py` (its still and words on paper),
`backend/tests/test_coded_figures_migration.py`, `backend/tests/research/test_kind_fixtures.py`,
`frontend/e2e/coded-figure-unit.spec.ts` (the still at first paint and no frame, the frame sandboxed
with its words, data and pinned libraries, nothing reaching the network, at rest under reduced
motion and stepping on Play, playing and pausing with motion allowed, the map base and its outline
kept, the projection the site's, and the Review page's still beside its run),
`frontend/e2e/kind-fixtures-unit.spec.ts` and `frontend/e2e/near-views-unit.spec.ts`.
