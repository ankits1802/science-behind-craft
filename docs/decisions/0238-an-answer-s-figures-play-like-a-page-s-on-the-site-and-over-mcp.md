# 0238. An answer's figures play like a page's, on the site and in the MCP answer view

Every moving figure an answer draws plays on its own once in view, loops and has one Play/Pause, as
a page's players have since decision 0228: the reaction player, the 3D molecule, the timeline map
(which loses its slider), a kit figure that names a motion, the what-if lab and, by its prompt and
its frame, a generated explainer. A step, option or point pressed is shown at once and playing goes
on from it. Under either reduced-motion switch nothing moves and every end state is drawn. A figure
holds the height of its tallest step without measuring, and no name, formula or lane scrolls. An
answer asked over MCP carries its moving figures as data, and the MCP answer view draws and plays
them the same way.

Date: 2026-11-26. Status: accepted (the lead's UX round of 2026-11-26, lane `answer-players`, after
the owner's "the chemical compounds and the reactions should be animated at all times" and, of the
dated record, "it should be a play pause button" with a click to jump; the owner, through the lead,
"everything must be usable through MCP too"). It amends
[decision 0228](0228-players-molecules-and-timelines-that-play-and-a-reaction-s-species-drawn-from-the-kit.md)
(an answer's timeline map kept its slider),
[decision 0049](0049-matter-and-expert-renderers.md) (the reaction player stopped on its last step),
[decision 0059](0059-sandbox-and-what-if-renderers.md) (the what-if's outcomes changed only on a
press),
[decision 0060](0060-zoom-timeline-and-film-renderers.md) (the timeline was a slider) and
[decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md)
(a kit figure played once through on Play). The owner's instruction overrides the design system's
motion on request (decision 0092) for these figures too. The contracts are
`docs/contracts/explainer.md`, `docs/contracts/component-specs-general.md` (the declared timeline
map) and `docs/contracts/mcp-ask-and-upload.md` (`AskedAnswer` and the answer view).

| For | Read |
|---|---|
| The page's players, molecules and timelines that play on their own | [decision 0228](0228-players-molecules-and-timelines-that-play-and-a-reaction-s-species-drawn-from-the-kit.md) |
| The answer's matter renderers | [decision 0049](0049-matter-and-expert-renderers.md) |
| The sandboxed frame and the what-if lab | [decision 0059](0059-sandbox-and-what-if-renderers.md) |
| The timeline map and film mode | [decision 0060](0060-zoom-timeline-and-film-renderers.md) |
| An answer's kit figure | [decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md) |
| The design system's motion rules and the two switches | [decision 0092](0092-design-system.md) and the kalavigyan-design skill, section 6 |
| The vat figure, the zoom and river stories, a places map's sequence and a stored explainer play too, and the MCP answer view places its timeline by year (amends this record) | [decision 0242](0242-every-moving-figure-plays-the-vat-the-zoom-the-river-a-map-s-sequence-and-a-stored-explainer.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **The answer did not move.** Decision 0228 made a page's players play in view, but an answer's
  React figures kept the press-only behaviour: the reaction player played on Play and stopped on its
  last step, with Previous and Next beside it; the timeline map had a range slider; a kit figure ran
  its panels once on Play; the what-if lab changed only on a press; the molecule turned only on Turn;
  a generated explainer was asked for "a Play and Pause control", and its frame could not know
  whether the reader saw it.
- **Heights moved.** The reaction player opened one step's detail at a time, so a step that played
  changed the player's height and moved everything below it; the what-if swapped its outcomes in
  place.
- **Formulas scrolled.** `ChemistryMarkup` wrapped every formula in `overflow-x-auto`, so a long
  equation, and KaTeX's struts, gave a lane horizontal and vertical scroll bars on a phone. KaTeX sets
  a chemical equation as one unbreakable box, so it cannot wrap where it is.
- **MCP drew cards.** The `ask` result carried each section's sentences and component cards only; the
  MCP answer view drew no figure at all.

## Decision

1. **One play state, shared.** The page timelines' reducer moves to `lib/playInView.ts` (`played`,
   `restingPlay`, `isPlaying`, `nextStop`, `IN_VIEW_MARGIN`) and their hook to
   `components/motion/usePlayInView.ts`, which takes a beat for each step; `lib/timelinePlay.ts`
   keeps the timeline's points. `PlayPauseButton` (`components/ui/`) is the one Play/Pause:
   `aria-pressed` once motion is allowed, Pause while playing. `StepStack` (`components/ui/`) stacks
   every step in one grid cell, the others hidden and inert, so a figure holds its tallest step with
   no measuring and no layout change on load.
2. **The reaction player** is a rail of steps (`aria-pressed`, one tab stop, arrows, Home and End),
   one Play/Pause with the status line, and a stage stacking each step's cast and detail. It rests on
   its first step and plays a step every 4 s in view, looping; under either switch it lists every
   step open, as before. Previous and Next are gone (one control per job: the rail).
3. **The molecule** turns at 15 degrees a second in view (`MoleculeScene.spin`, 3Dmol's `spin`),
   holding still under the pointer, in focus, while explored and on Pause; its Turn reads Pause while
   it turns. Under either switch Turn turns a quarter at once.
4. **The timeline map** draws the page's `TimelineTrack` (moved to `components/answer/journey/`):
   one Play/Pause, a point to press for each year, Space on a point toggling play; the slider and the
   frame's `control` option are gone. It rests on the last year.
5. **A kit figure that names a motion** plays its panels in turn and a rest beat (`kitBeat`,
   `kitPanel`), looping, with one Play/Pause; its status keeps three lines so it never grows.
6. **The what-if lab** plays its options one every 4.8 s, stacked in one box.
7. **A generated explainer** is told when the reader sees it: the frame sets `data-in-view` on its
   root and fires `kv-view` on `document` (`sandboxFrame.FRAME_VIEW`, an `IntersectionObserver` in the
   frame, which sees the top viewport), and the prompt asks it to play on its own while it is "true",
   loop, hold its tallest stage, with one Pause and its stages to press.
8. **No scroll bars.** A formula has no scroll box; an equation is set term by term
   (`chemistryKeys.equationPieces`), each term its own KaTeX box, so a line breaks between terms; the
   page's pre-rendered chemistry asks for the terms. A single formula wider than its box may break
   between its parts rather than scroll.
9. **Over MCP.** Each `AskedSection` carries `figures` (`research/mcp_ask_figures.py`): a player
   (`reaction`, `stages`, `dips`) with steps, a timeline with stops, a molecule with its conformer's
   geometry (`services/mcp_ask_molecules.py`, read through the composer's conformer store, left
   out when it cannot be read). `said` indexes the section's sentences a step shows. The answer view
   draws and plays them as the site does (in view, one Play/Pause, a press shows a step at once, no
   slider, Space toggles a timeline, a turning molecule, still under both switches, nothing
   scrolling), draws a figure's sentences in its steps rather than the paragraph, and its theme adds
   the depicted materials, the atoms and the motion durations. The colour words map to the web
   player's paints (`COLOUR_SPECIMENS`, checked against `DYE_FILL`).
10. **At rest for comparison.** The production run's answer views open with motion reduced, as the
    page parity and smoke runs do; the release controls spec reads an answer's player playing in view
    where the site serves it (`data-plays`) and the earlier press-only one otherwise.

## Consequences

- An answer's figures and its pages' share one play state and one Play/Pause; a page's places-map
  sequence (`useMapSequence`, decision 0232) keeps its own playback and stops on its last step.
- The signature vat figure keeps its Dip again (the design system's vat moment), and the zoom story
  and the river story keep their controls; they are not among the figures this record makes play.
- Stored generated explainers written before this record keep their press-only Play; new ones are
  asked to play in view.
- The MCP answer view is larger (one script of about 620 lines) and still loads nothing.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`frontend/e2e/answer-players-unit.spec.ts`, `frontend/e2e/answer-view-figures-unit.spec.ts`,
`frontend/e2e/matter-renderers-unit.spec.ts`, `frontend/e2e/journey-renderers-unit.spec.ts`,
`frontend/e2e/what-if-unit.spec.ts`, `frontend/e2e/art-kit-unit.spec.ts`,
`frontend/e2e/rendered-chemistry-unit.spec.ts`, `frontend/e2e/generated-explainer-unit.spec.ts`,
`backend/tests/mcp/test_mcp_ask_figures.py` and `backend/tests/mcp/test_answer_kit.py`.
