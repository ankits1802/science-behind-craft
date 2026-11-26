# 0242. Every moving figure plays: the vat, the zoom and the river, a places map's sequence that loops, a stored explainer's own Play, and the MCP answer view's timeline placed by year

The figures decisions 0228 and 0238 left out now play like the others: once in view, looping, with
one Play/Pause and a step to press that is shown at once while playing goes on from it, and with
nothing moving under either reduced-motion switch. An answer's signature vat figure plays its four
dips phase by phase, the zoom story its levels and the river story its reaches; a page's places-map
sequence loops instead of stopping on its last step, through the same shared play-in-view code; a
generated explainer stored before decision 0238 has its own Play pressed by the frame in view and
its Pause out of view; and the MCP answer view places a timeline's points by year and labels each as
the site writes its span.

Date: 2026-11-26. Status: accepted (the lead's UX round of 2026-11-26, lane `players-2`, after the
owner's "the chemical compounds and the reactions should be animated at all times" and his wish for
no gaps). It amends
[decision 0238](0238-an-answer-s-figures-play-like-a-page-s-on-the-site-and-over-mcp.md) (the vat
figure, the zoom story and the river story kept their controls, a stored explainer kept its
press-only Play and a places map's sequence its own playback),
[decision 0232](0232-every-places-map-drawn-on-the-site-s-own-map-base-and-told-what-it-is-about.md)
(the sequence played once and stopped on its last step),
[decision 0060](0060-zoom-timeline-and-film-renderers.md) (the zoom moved on Zoom out and Zoom in),
[decision 0048](0048-place-renderers.md) (the water flowed only on request),
[decision 0059](0059-sandbox-and-what-if-renderers.md) (the frame only told an explainer what is
seen) and [decision 0092](0092-design-system.md) (the answer's VatFigure played from Dip again).
The owner's instruction overrides the design system's motion on request for these figures too. The
contracts are `docs/contracts/explainer.md`, `docs/contracts/component-specs-general.md` (The places
map) and `docs/contracts/mcp-ask-and-upload.md` (`AskedStop` and the answer view).

| For | Read |
|---|---|
| The page's players that play on their own | [decision 0228](0228-players-molecules-and-timelines-that-play-and-a-reaction-s-species-drawn-from-the-kit.md) |
| An answer's figures that play, the shared play-in-view code and the MCP answer view | [decision 0238](0238-an-answer-s-figures-play-like-a-page-s-on-the-site-and-over-mcp.md) |
| The places map and its sequence | [decision 0232](0232-every-places-map-drawn-on-the-site-s-own-map-base-and-told-what-it-is-about.md) |
| The zoom story and the timeline map | [decision 0060](0060-zoom-timeline-and-film-renderers.md) |
| The region story and its river | [decision 0048](0048-place-renderers.md) |
| The sandboxed frame | [decision 0059](0059-sandbox-and-what-if-renderers.md) |
| The design system's vat moment and the two switches | [decision 0092](0092-design-system.md) and the kalavigyan-design skill, section 6 |
| Every decision, by group | [README.md](README.md) |

## Context

- **Four gaps.** After decision 0238 an answer's reaction player, molecule, timeline map, kit figure
  and what-if lab played in view, but its signature vat figure still waited for Dip again (and
  offered Start again after the fourth dip), the zoom story moved only on Zoom out and Zoom in, and
  the river story's water flowed only on Follow the water. A page's places-map sequence (decision
  0232) played once from its first step and stopped on its last, through a second playback reducer
  of its own (`usePlayback`, `reactionPlayer.playbackStep`).
- **Stored explainers.** A generated explainer is stored by its hash, so one written before
  decision 0238 cannot be asked to play in view, and its press-only Play stays press-only.
- **The MCP answer view's timeline.** It spaced its points evenly and labelled a century
  `1401–1500` where the site places points by year and writes `15th century`.

## Decision

1. **The vat figure plays.** Its twelve beats are the four dips times the three frames (in the
   vat, lifted, in the air), each as long as its named motion (dip, hold, oxidise) and a hold
   (`answerVat.vatShown`, `vatBeat`, `VAT_BEATS`); it rests on the first dip in the air, plays from
   the first dip in the vat once in view and loops through the four, replaying the dip and oxidise
   motions on the drawn cloth. Each frame's title is a button (`aria-pressed`) that shows that
   frame of the dip shown; one Play/Pause replaces Dip again and Start again; the status holds the
   height of its longest line. Under either switch nothing moves and Play shows the next phase.
2. **The zoom story plays.** Its levels are stacked in one box (`StepStack`), one Play/Pause sits
   beside its rail, and it plays a level every 4.8 s (`zoomView.ZOOM_LEVEL_MS`) once in view,
   looping; a level pressed on the rail is shown at once. Zoom out and Zoom in are gone (one control
   per job: the rail). Under either switch every level is listed, as before; in a film the scene
   drives it and it has no Play.
3. **The river story plays its reaches.** Its stops are each step's district entry along the river,
   never going back up it (a step with no district holds the water where it is), then the outlet
   (`regionStory.storyStops`); once in view the water flows to each stop in turn at `FLOW_SECONDS`
   for the whole river, holds `STOP_HOLD_MS`, and loops from the source (`stopBeat`, `flowsOn`,
   `useRiverFlow`). The step shown outlines its district and draws its stretch, one Play/Pause
   replaces Follow the water, its status names the step and its district, and a step or badge
   pressed shows that stop's water at once. It rests on the whole river; a story with no drawn river
   does not play. Under either switch nothing flows and a press shows a stop at once.
4. **A places map's sequence loops,** through the shared code: `useMapSequence` is a watch over
   `usePlayInView` (resting on the last step, a step every four seconds), `MapSequence` has the one
   `PlayPauseButton` and a status naming the step, and `usePlayback` and
   `reactionPlayer.playbackStep` are deleted, so there is one implementation. Only the hook and its
   player changed; the map, its labels and its still are untouched.
5. **A stored explainer plays.** An explainer whose HTML reads neither `kv-view` nor
   `dataset.inView` (`sandboxFrame.speaksInView`) is framed with a shim (`explainerPieces`,
   `FRAME_PLAY`): on `kv-view` and on load, with motion allowed, it presses the explainer's own Play
   (the first visible, enabled `button`, `role="button"` or button input whose `aria-label`, text or
   value has the word Play) in view and its Pause out of view, reading whether it plays from
   `aria-pressed`, else from the word its control shows, else, with separate Play and Pause
   buttons, from its own presses. A reader's own press of Pause holds until they press Play. An
   explainer with no Play control is left as it is, and no stored HTML is rewritten. The shim rides
   the generated explainer's frame only; a contributor's coded figure keeps its own Play.
6. **The MCP answer view's timeline by year.** Each `AskedStop` carries `year`, its first year, and
   its `label` is the span as the site writes it (`research/timeline.year_span_text`, the web's
   `yearSpanText`, from the stop's shortest span), and the view places each point as the web does
   (`timelinePlay.pointPositions`, then `spreadPositions` with the 6 per cent gap). The one ordinal
   moves to `research/timeline.ordinal`, which the Wikidata times also use.

## Consequences

- Every moving figure on a page and in an answer plays in view with one Play/Pause, and none
  plays under either reduced-motion switch.
- The vat figure no longer offers Dip again or Start again; the kit's dip player on a page keeps its
  Dip again label under reduced motion (decision 0228).
- A zoom story mounts every level at once to hold its height, as the reduced-motion list always did,
  so its molecule loads when the story does.
- A stored explainer whose Play is not named Play, or whose controls are not buttons, still rests
  until pressed.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`frontend/e2e/answer-vat-unit.spec.ts`, `frontend/e2e/journey-renderers-unit.spec.ts`,
`frontend/e2e/place-renderers-unit.spec.ts`, `frontend/e2e/map-sequence-unit.spec.ts`,
`frontend/e2e/explainer-frame-play-unit.spec.ts`, `frontend/e2e/answer-view-figures-unit.spec.ts`,
`backend/tests/mcp/test_mcp_ask_figures.py` and `backend/tests/research/test_timeline_words.py`.
