# 0229. A preview card starts as one line and minimises back to it, and what a craft's own facts could show is offered to judge, never counted against Kutch Ajrakh

The page preview's MCP App card starts as one line (the page's name, its counts passed, failed and
yours to judge, Open the private preview and an expand control) and minimises back to it, telling
the host its new height; no preview opens itself. The preview report gains rule 29, which reads the
craft's own facts for what a figure could show that the page leaves in words and offers each as an
opportunity to judge, never a failure. `compose_component` with no kind composes every kind it can
make in one call, as a shortcut. The count table beside Kutch Ajrakh becomes one quiet line.

Date: 2026-11-26. Status: accepted (the lead's UX round of 2026-11-26, lane preview-gate, with the
owner's correction of the same day). It amends [decision 0195](0195-a-preview-drawn-seen-and-checked-before-it-is-proposed.md)
(the preview set beside Kutch Ajrakh) and [decision 0198](0198-a-craft-s-own-interactives-composed-and-played-on-every-page.md)
(a craft's own interactives composed by the server). The contracts are `docs/contracts/open-work.md`
(the preview report, the view, `compose_component`) and `docs/contracts/mcp-ask-and-upload.md` (the view).

| For | Read |
|---|---|
| The preview and its report | [decision 0195](0195-a-preview-drawn-seen-and-checked-before-it-is-proposed.md) |
| The composers | [decision 0198](0198-a-craft-s-own-interactives-composed-and-played-on-every-page.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- The owner, on a contributor's rebuild of Sanganeri Hand Block Printing: "the previewer page card
  itself does not minimize, it just hides it within the card ... I want the card itself to be
  minimized ... first thing I need to scroll all this way". Only the report folded: the head (title,
  lede, two buttons, eight tiles) always showed, the newest preview opened itself
  (`setOpen(Boolean(channel))`), and the height the view reported was the document's scroll height,
  which never falls below the frame the host already gave it.
- The owner: "I have to handhold the agent ... for good-for-nothing results". The report's table
  beside Kutch Ajrakh counted pictures, figures, interactives and maps and judged nothing, so the
  agent stopped at a page with a fraction of what its facts could show.
- The brief first asked for a rule that failed a page for every component the server composes and
  the page leaves out, and for `propose_page` to refuse it. The owner corrected it the same day:
  pages must not be copies of Kutch Ajrakh; they follow its design principles and thought process,
  and over-deterministic tooling is rejected. The preview lists opportunities read from the craft's
  own facts, yours to judge; `propose_page` refuses only what is wrong.

## Decision

1. **The card minimises.** `data/design/page-preview-view.html` draws every preview as one line: an
   `h1` of the page's name, its verdict counts as status marks with words, Open the private preview,
   and Show the full preview (`aria-expanded`, `aria-controls`). Showing it draws the head (kicker,
   lede, Open the page as it stands, the expiry, the tiles) and the full report, the name growing to
   the page-title size; Minimise the preview, or Escape, returns it to the line with the focus on the
   control. The view reports the height of what it draws (`main`'s box) on every change, through
   `ui/notifications/size-changed` and a `ResizeObserver`, so the host's frame shrinks with it. No
   preview opens itself; the broadcast channel still minimises the others when one is opened or a
   newer one draws. The three verdict tiles left the head, since the line shows them.
2. **Rule 29 offers, never fails.** `research/page_report_drawable.py` reads four kinds of
   opportunity: a reaction the server balanced (`HeldReaction.balanced()`) that no figure drawing a
   reaction cites, two stages or more that no player or drawing cites, two dated sentences or more and
   a sentence of places with no map that moves through dates, and two quantities with units in one
   field with no chart, table, tiles or drawing of that field. A figure counts when it is of a kind
   that draws the thing and its units cite its facts, so a figure the contributor writes counts as
   much as a composed one, and a table of a reaction does not draw it. Each opportunity names its
   chapter, its facts and its ways: the figure the contributor writes, and, where the registry
   (`COMPOSED_KINDS`) holds a composer for it, `compose_component` with that kind as a shortcut, so
   the later `stage_player` and `timeline_map` composers join without a change here. The rule is
   JUDGE while any opportunity stands and PASS when none does; it never fails, and `propose_page`
   still refuses only a failed drawing (rule 28). The craft's reactions and stages reach the report
   through `services/page_report_held.held_shapes`, for a craft's page only.
3. **One call composes every kind.** `compose_component` with no kind (and no `about`) runs
   `compose_every_kind`, every kind of the registry for the craft, a kind the server cannot reach here
   (no media store or PubChem for a molecule) missing with its reason instead of failing the call;
   `missing` and `leftOut` are prefixed with their kind. The tool count stays 24.
4. **Kutch Ajrakh is a reference, not a target.** The card draws the counts beside Kutch Ajrakh as one
   quiet line, "For reference, never a target"; the report's `bar` is unchanged.
5. **Guidance kept to the rule.** Rule 29 enters the page checklist (its three copies, now 29 rules)
   and `compose_component`'s description says the one call is a shortcut; the contributor skill, the
   guide pages and the initialize instructions are left to the playbook lane (decision 0230).
   Nothing here departs from the design skill.

## Consequences

- A contributor's client sees each preview as one line and opens only the one it wants; the chat no
  longer has to be scrolled past full reports. Tested by `frontend/e2e/page-preview-card-unit.spec.ts`
  (the card starts as its line, its reported height falls back to the line's on minimising, Escape
  minimises and keeps the focus, a phone never scrolls sideways, the opportunities and the one
  Ajrakh line) and `backend/tests/mcp/test_page_preview_view.py`.
- The report says what the craft's facts could show and how, and leaves the choice to the
  contributor: `backend/tests/research/test_page_report_drawable.py` (each opportunity read, a figure
  citing its facts closing it, a table not, a composer offered only when the registry holds it, the
  rule never failing) and `backend/tests/pages/test_page_report_held.py` (only balanced reactions and
  stated stages, a craft's page only). The rule's count of 29 is in `test_page_report.py` and
  `test_skill_references.py`.
- `backend/tests/mcp/test_compose_tool.py` composes every kind in one call ready for `edit_draft`, and
  names each kind left uncomposed beside what it needs.
- `compose_reaction` keeps its own test for drawing an equation; it could use
  `HeldReaction.balanced()` once its lane is merged.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
