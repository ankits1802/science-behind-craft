# 0106. One monograph template for every page, reached through fragments

Date: 2026-11-19. Status: accepted (owner: "go ahead with round 3 after the release"). Implements
decision 0101 build step 2's second half and item 14; builds on decision 0105.

## Context

Decision 0101 asks for the approved Kutch Ajrakh page's design to become the one renderer for
every craft, family and category page, with component views moved out of the template into specs
and a layout record per page, proven by screenshot parity before the static file is retired.

Decision 0105 left the page as structured content (1,086 text units, 79 registered components, the
layout) plus a 10,409-line HTML template. The template still holds every component's view as
hand-made markup, its styles and its scripts; only four data blocks are separate. Every other
craft is drawn by the tabbed React craft screen from the craft page contract, whose chapters
(decision 0095) already carry the answer blocks a page shares with answers.

Porting the whole template to React in one step and proving it pixel for pixel would put the
approved page at risk for weeks. Keeping the Python template as the renderer would leave answers
and pages on two renderers, against decision 0095's "one renderer for answers and the page".

## Decision

1. **The page is a document.** `research/monograph_document.MonographDocument` (schema 1) is what a
   renderer draws: the subject (craft, family or category), its title and version, the
   `MonographContent` of decision 0105 (units, components, layout, sources, citations, data), and
   for each component either a `spec` (data for a native view) or a `fragment` (its legacy markup,
   unit slots filled). `GET /api/crafts/{slug}/monograph` serves it.
2. **The template splits into a shell, fragments and a kit.** Each component's markup moves out of
   `template.html` into its own fragment file; the page-wide styles and scripts move into a kit
   (`monograph.css`, `monograph.js`) served at `/monographs/kit/`. The static build reassembles
   shell, fragments and kit and must still write the served file byte for byte, so the approved
   page never changes while the work goes on.
3. **One React renderer.** The web app draws a `MonographDocument` with React: the masthead, the
   chapter rail and numerals, the spread, text units with their marks (the same markup
   `render_nodes` writes), citation clusters and their popovers, plates, the sources chapter and the
   coda, with the kit's styles. A component with a native view is drawn by it from its spec; any
   other component is drawn from its fragment, with the kit's scripts giving it its behaviour.
   Fragments are a bridge, recorded as debt: decision 0101 item 14 wants every view to be a kind
   with a spec, never free-form markup.
4. **Component kinds move to specs a group at a time.** A kind's spec is a typed model
   (`research/component_specs_<group>.py`) and its view a React component
   (`frontend/components/monograph/kinds/<group>/`) implementing
   `lib/componentViewContract.ComponentView`. Ajrakh's spec for each component is extracted from
   the template into `backend/app/data/monographs/<Slug>/specs/<label>.json` (slashes in the label
   become `__`). A shared component's spec serves every page and answer that places it.
5. **Parity is proven before the switch.** The React page of Kutch Ajrakh replaces the static
   file only when it matches it on decision 0101's three counts (text, screenshots at 360, 834 and
   1440 in light and dark, interactions). Until then it is served at `/crafts/<slug>/monograph`.
6. **Every page follows.** After the switch, crafts, families and categories without authored
   content get a document generated from their stored sections, registered components and dossier,
   with a `PageLayout` record per page (item 14) holding chapter order, the lead component,
   picture roles and crops, and pull quotes.

## Order of work

- Round 3a: the split and the document API; the React renderer at the preview route; three groups
  of component kinds with specs and views (plates and media; data and place; science players).
- Round 3b: the parity proof and its fixes, the switch for Kutch Ajrakh, `PageLayout`, generated
  documents for every craft, family and category, and the remaining kinds.
- Round 3c: the last fragments become kinds, and the kit's scripts give way to the views.

## Built (2026-11-19)

Rounds 3a and 3b ran together: the split and the kit (the served page unchanged), the stored and
generated documents with their routes, `PageLayout` (migration 0042) and `get_layout`, all 42 kinds
of Ajrakh's components as specs with React views (every Ajrakh component draws from its spec, so no
fragment is left on that page), and the React renderer at the preview routes. Views place nested
components through `ComponentViewProps.renderComponent`. A generated plate takes the layout's focal
box. The parity proof is the **Monograph parity** workflow; the switch waits for it.

## Consequences

- The served Ajrakh page stays byte-identical through 3a; the parity proof decides the switch.
- Answers can place a shared component's native view instead of a link card once its kind has a
  spec (decision 0101 step 3).
- Until 3c the renderer loads the kit's scripts, which act on fragment markup; a fragment's view
  must not be re-rendered by React after the kit has bound it.
