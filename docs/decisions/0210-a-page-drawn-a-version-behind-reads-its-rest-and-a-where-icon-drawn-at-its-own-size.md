# 0210. A page drawn at the version a rebuild replaced still reads its rest, Monograph parity reads each page as a reader has it, and a reaction player's where icon is drawn at its own size

A generated page's stored copy keeps every version a rebuild replaces, so the page a cache still
holds at that version reads the rest of itself and its edition; Monograph parity compares a page
only once its rest is drawn and its kit bound, and names a rest it could not read; and a reaction
player draws a step's where icon at its own size instead of its column's.

Date: 2026-11-25. Status: accepted (the lead's lane `sanganeri-parity` of the page-quality round:
Monograph parity had failed on Sanganeri Hand Block Printing on every release since the round
began). It amends [decision 0186](0186-pages-rebuilt-by-the-release-that-serves-and-a-deploy-that-never-goes-back.md)
(what a rebuild of a stored page leaves behind). The contracts are
`docs/contracts/monograph-document.md` (the stored copy, and `version`),
`docs/contracts/component-specs-science.md` (reaction_player) and `docs/contracts/infra.md`
(Stored pages); the RUNBOOK's Monograph parity paragraph says how the run reads a page.

| For | Read |
|---|---|
| How a release and a read rebuild a stored page, which this amends | [decision 0186](0186-pages-rebuilt-by-the-release-that-serves-and-a-deploy-that-never-goes-back.md), [decision 0190](0190-a-voice-turn-bound-and-answered-and-a-page-built-while-its-inputs-move.md) |
| The lead chapter drawn by the server and the rest read after load | [decision 0177](0177-differences-named-and-the-monograph-shell-measured.md) |
| The borrowed components the parity run compares | [decision 0151](0151-a-release-the-live-side-can-read.md) |
| The drawing checks the run and the preview share | [decision 0195](0195-a-preview-drawn-seen-and-checked-before-it-is-proposed.md) |
| A heavy kind loaded near, and what the run need not wait for | [decision 0205](0205-a-page-measured-on-a-slowed-phone-held-to-its-budget-and-heavy-kinds-loaded-near.md) |
| The content changes an Admin could stage instead | `docs/content/sanganeri-parity-fixes.md` |
| Every decision, by group | [README.md](README.md) |

## Context

- **The run always failed on one page.** Monograph parity's borrowed-component test failed at
  every width and theme on `/crafts/Sanganeri-Hand-Block-Printing` (runs 45501047488,
  45509597337, 45519429136 and 45527136016): `sanganeri-hand-block-printing/chemistry/two-mordants-one-bath:
  an icon of 24 units draws 239px wide` at 360, 658 px at 834 and 651 px at 1440 and 1920, and in
  one project of two of those runs `shared/chemistry/alizarin-purpurin-3d` and
  `shared/chemistry/indigo-vat-dip ... not found`.
- **The icon was a 24-unit drawing sized by its column.** The page's payload (version 88 on
  2026-11-25) places the reaction player with five hand-drawn steps, each with a `whereIcon` of
  `viewBox="0 0 24 24"` and no class. The view drew the spec's drawing as given; the kit sizes only
  `.bx-chem .rx-where .vg` (Kutch Ajrakh's 132 by 92 vignettes, at 92 px), and `.bx-chem svg` sets
  only `max-width: 100%`, so an unclassed SVG took the width its flex row left it.
- **The two borrowed components are placed, and were missing only when the whole rest was.**
  Both are in the payload's components and layout, in the chemistry chapter. In each project that
  reported them not found, the run's report held no chemistry chapter for the page and no line for
  the player beside them: the rest of the page, everything after its lead chapter, had not been
  drawn. The rest is read from `/crafts/<slug>/shell/v<version>-<digest>`, the version the page's
  HTML names. A generated page's stored copy (`StoredDocument`) held one row per page, so once a
  rebuild moved Sanganeri to version 88, `GET /api/crafts/Sanganeri-Hand-Block-Printing/monograph?version=87`
  answered 404 `This craft's monograph has no such version.`, and so did the rest of version 87
  (`/shell/v87-170e1b3f`, 404, while `/shell/v88-170e1b3f` answered 200 with 591,996 bytes). The
  page reader saw `The rest of this monograph could not be read. Reload the page to try again.`,
  the kit still bound, and the run, which waited only for the kit and then silently went on, found
  nothing to compare. It happens to a reader handed the page's HTML from before a rebuild (a page
  refreshed after a rebuild can be served its older HTML once while it is built again), which fits
  one project in a run meeting it and the others not; Sanganeri met it because its copy changes
  at almost every release (88 versions, against 21 for Bagru).
- **A versioned address already promised more.** Cite this monograph gives `/crafts/<slug>/v<N>`,
  and for a generated page it stopped answering at the next rebuild.

## Decision

1. **A rebuild keeps the version it replaces.** When `_store` writes a changed document over a
   stored copy, it first writes the copy it replaces, its version, hash and text as stored, to
   `StoredDocumentVersion` (migration `0117_sanganeri_parity`, keyed by kind, slug, language and
   version, row-level security on and the public roles revoked as for `StoredDocument`;
   `services/stored_document_versions.py`). An unchanged rebuild keeps nothing. A page whose
   sections are withdrawn loses its kept versions with its copy, so a version number given again
   later is never the old page's. Every version is kept, as authored documents keep theirs.
2. **The craft route serves a kept version as it was stored.** `?version=N` on a generated page
   whose copy has moved on reads that version (`superseded_fallback`, the route's adapter to
   `stored_documents.superseded_copy`): in English alone, never through the page text index or a
   translation, under its own tag, its parts read the same way, and any rebuild the read claimed
   still queued. A version never kept stays 404. The rest of a page drawn at version N, and its
   edition, therefore read as the page was drawn.
3. **Parity reads a page as a reader has it.** The borrowed pass waits, for at most 60 s, until
   the page holds no rest still to read (`[data-kv-deferred]`) and its kit is bound, the state a
   reader is in once the page is whole (`e2e/parity/parityReady.ts`); a page whose rest says it
   could not be read, or that is not whole in time, is a failure naming that cause, beside the
   components it then does not draw. Nothing the run compares is loosened, skipped or narrowed.
4. **The view sizes the where drawing, never its container.** `lib/reactionWhere.whereDrawing`
   draws a where drawing at most 32 units wide (the drawing checks' `iconView`, held equal by the
   unit spec) at its own size, one unit a pixel, without the `vg` class; any other drawing gets
   the kit's `vg` vignette class where its spec leaves it out; both are `aria-hidden`, since the
   where line names the place in words. Kutch Ajrakh's four vignettes carry both already and are
   drawn exactly as before.

## Consequences

- **The failure lines.** The icon line is fixed by item 4 at every width: Sanganeri's 24-unit
  icons draw 24 px wide, under the 64 px the checks allow, with no change to its content. The two
  `not found` lines are fixed by items 1 and 2 for every rebuild after this release: the version a
  page's HTML names stays readable, so its rest draws; the release that adds the table rebuilds
  its stale pages with this code after its switch, so the version it replaces is kept. Only HTML
  naming a version replaced before that release is still met unread, and item 3 then names `the
  rest of the page could not be read, so its later chapters are not drawn` for that page. Monograph
  parity runs only after a deploy of main, so the lane could not run it on its branch.
- **No content change is needed** for parity. `docs/content/sanganeri-parity-fixes.md` records
  that, and the rebuild an owner may still ask for (the player composed from the kit, its scenes
  drawing where each step happens).
- **Storage grows with each change of a generated page.** Each changed rebuild keeps one copy of
  the page it replaces (Sanganeri's is 592,088 bytes of JSON, which Postgres stores compressed);
  nothing is pruned. Versions replaced before this release are gone and are not rebuilt.
- **What is left.** A category page reads no version (its route and its rest route take none), so
  a category page drawn a version behind still reads no rest; the table and `superseded_copy` serve
  it once the category route takes `version` and its rest route reads it. A kept version is not
  translated, so the rest of a translated page drawn a version behind is still not found.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md), the
[contracts](../contracts/README.md) and the [RUNBOOK](../RUNBOOK.md). Its rules are tested by
`backend/tests/db/test_stored_documents_db.py` (a replaced version kept and read, an unchanged
rebuild keeping nothing, a withdrawn page taking its versions, the route reading a kept version
and not an unknown one), `backend/tests/public/test_craft_monograph_versions.py` (a kept version
served in English under its own tag with its parts and its rebuild queued, and an unknown one not
found), `frontend/e2e/reaction-where-unit.spec.ts` (an icon at its own size and a vignette as the
kit sizes it, Kutch Ajrakh's unchanged, the bound equal to the drawing checks', and a player's
24-unit icon passing the checks at 360 and 1440 where the drawing as given fails them) and
`frontend/e2e/parity/parity-ready-unit.spec.ts` (a page ready, ready once its rest arrives,
unread, and still waiting while its rest is held or its kit unbound).
