# 0249. A category draws the shared figures on its own crafts' science, a craft the shared figures of its own place, and the checks after a deploy wait for the API

A category's page holds the facts of the crafts on its shelves, so a shared figure resting on them
draws there again; a craft's page draws a shared figure keyed to a place it is about; every other
borrowed figure still draws only on facts its page holds. The Post-deploy check and Monograph parity
read the pages only once the site serves the deployed commit and the API serves what that build
needs, and the Bagru control test checks what Bagru draws under the rule.

Date: 2026-11-27. Status: accepted (the lead's lane brief `ux-1126/borrowed-held`, on the owner's
choice of the same day). It amends
[decision 0248](0248-what-the-fresh-agent-could-not-fix-on-sanganeri.md) (item 3: a category held only
its curated facts, family science and sections, and a craft no place figure of its own place). The
contracts are `docs/contracts/open-work.md` (Withdrawn, replaced, borrowed and held) and the
contributor reference `components.md` (Borrowing); the runbook names the wait (`docs/RUNBOOK.md`,
Release gate and the parity proof).

| For | Read |
|---|---|
| The release it follows | [decision 0248](0248-what-the-fresh-agent-could-not-fix-on-sanganeri.md), item 3 |
| The runs that found it | Monograph parity 45772026177 (before) and 45866632827 (after), Post-deploy check 45866633303 |

## Context

After the backend deploy of `5d41a13e`, every category page drew no component, Kutch Bandhani and
Mud Mirror Work (Lippon) lost Kachchh's rainfall chart, district climate map and Banni and Great Rann
photographs, and Bagru its five borrowed chemistry figures. Monograph parity failed its guard (no
component borrowed from Kutch Ajrakh anywhere) and the Post-deploy check found no dip player on
Bagru. The lead's reading was checked against the code and production's own facts (`get_facts`):

1. **Categories: right, by another link.** The Textiles category reaches its four figures
   (`alizarin-purpurin-3d`, `indigo-leaf-to-cloth-chain`, `indigo-reduction-player`,
   `indigo-vat-dip`) by claim overlap, not by concept: they are keyed to compounds and crafts only,
   and each cites a few of the category's own facts (the dip rests on "Indigo is insoluble in water,
   so it is reduced to a soluble colourless leuco form...") beside Kutch Ajrakh's, filed under
   Ajrakh's concepts (`Concept.craftId`). A category held its curated facts, its family science and
   its sections' facts; `_told_alike` holds a cited fact about a concept one of the page's facts is
   about, and the category's facts are about the category's own concepts, so no Ajrakh fact was
   held and no figure drew. The test passed because its figure cited a fact about the very concept
   the category's sentence was about, a shape production does not have.
2. **Kachchh's figures: right.** They cite Kutch Ajrakh's climate facts; Kutch Bandhani's scope
   never holds another craft's facts, and decision 0248 let nothing else hold them.
3. **The checks: half right.** Both read only the site's `/api/version` (the `await-build` action);
   neither read the API. The first wave of `5d41a13e` read no page at all: Deploy web app had handed
   its build to Deploy backend, so the commit check said `no-build` and parity skipped, green having
   read nothing. But any wave whose site serves the commit while the API runs an older release with
   another API (a backend deploy that failed after a web build, the hourly check, a dispatched one,
   or the deploy hook building a newer head of main) read the pages against the old API.

## Decision

1. **A category holds its crafts' facts** (`page_held_facts._crafts_science`). Besides its curated
   facts, family science and sections, a category's page holds a `CONCEPT` fact about a visible
   concept owned by a craft on one of its shelves (`Concept.craftId`, the craft's `subCategoryId`
   under the category) or by one of its shelves (`Concept.subCategoryId`), and an `EDGE` fact joining
   such a concept. This is the data model's own ownership of a fact (fact, concept, craft, shelf,
   category), the one a craft's page reads for its own facts (`scope_concepts`), lifted to the
   shelves. Claim overlap and the pieces' concept keys only choose which figures a category
   considers (`_category_pieces`); as ties they would hold whatever a figure happens to cite beside
   the shared fact, and a shared concept linked to crafts belongs to no one category. The second tie,
   a fact about a concept the category's facts are about, stays `_told_alike`. A figure whose facts
   all belong to another category's crafts is held by neither its concepts' owners nor the page's
   told concepts, so it is never drawn. The draft and the page read one rule (`held_claims` serves
   `borrowed_problem` and `held_rows`).
2. **A craft draws a shared figure of its own place** (`component_places_held.held_by_place`, used
   by `held_rows` and `borrowed_problem`). A shared component (no owning craft) keyed to a place
   (`KnowledgePieceSubject.placeKey`) is held by a craft's page when its place binding
   (`component_binding` over its place keys and the places its title, description and units name,
   the binding the page's place filter and parity's place check read) meets the craft's own
   districts or states (`subject_places`). It is never looser: a figure with no place key is no place
   figure even when its words name the craft's district or its field is climate; another craft's own
   figure is never borrowed by place; a family's or a category's page has no place tie. The figure
   draws its home's units and citations, numbered by the page (`borrow_drawn`), as before decision
   0248, so rules 9 and 15 read it as they did.
3. **Every other borrowed figure keeps decision 0248.** Bagru, Sanganeri, Bagh and Machilipatnam
   draw no borrowed chemistry figure until they build their own on their own facts.
4. **The control test follows the rule.** The Bagru test checks its rail, citations, reaction
   player and 3D molecule and that it draws no shared indigo vat dip (`DIP_UNBORROWED`; a dip player
   of its own is operated); Kutch Ajrakh's test still requires the dip player. The Textiles category
   was not chosen: the Post-deploy check also runs on a pull request, against production, which draws
   the category's figures only after the backend deploy of the change that restores them, so it
   would fail the very pull request. The category's figures are guarded by Monograph parity, whose
   guard of more than one borrowed case is kept, and by the database tests.
5. **The checks wait for the API.** The `await-build` action's read moves to
   `.github/actions/await-build/served.sh` and takes `api-origin` (`vars.API_BASE_URL` in both
   workflows). Production is reached only when the site serves the commit or a later commit of main
   and the API's `/health` names that build's release, a later one, or one since which main changes
   nothing under Backend checks' push paths (the test the web build's gate, `api_ready.sh`, already
   makes). The wait stays within the one run each deploy starts (40 minutes); a wave that started no
   build still reads nothing and says so. The messages and the commit issue name the API's release.

## Consequences

- After the backend deploy, the Textiles category draws its four figures again wherever every fact
  they cite is its own or its crafts', and Kutch Bandhani and Lippon draw Kachchh's four; Monograph
  parity has borrowed cases again. No other category reaches these figures.
- A craft added to a shelf can add shared figures to its category's page; the category's stamp
  already counts its member crafts.
- A check whose API lags the commit waits, then fails naming both; an hourly check whose API lags
  past the 90-minute grace opens `Production is not serving main`.
- Tests: `backend/tests/db/test_shared_figures_held_db.py` with `shared_figures_seed.py` (a category
  holding shared figures linked by concept and by overlap, a category of another science that never
  does, a craft drawing the figure keyed to its district and no other borrowed one, a sibling outside
  it drawing none, and drafts refused exactly where the page does not draw),
  `test_borrowed_and_held_pages_db.py` (its category test held the rejected rule and now expects the
  category to hold its crafts' facts; the family's is unchanged), `backend/tests/deploy/test_served_commit.py`
  (the site and the API both ways, no release, no API origin, both workflows wired), and the release
  control test `frontend/e2e/release/controls.spec.ts`.

## What is left

- No control test operates the Textiles category's players after a deploy; Monograph parity draws
  and compares them. A control test there needs a check that runs only after the backend deploy.
- A wave that started no build ends green with a notice; GitHub has no conclusion between passing
  and failing for a run that had nothing to read.
