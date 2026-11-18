# 0081. Craft page contract version 2: a page whose structure is final at first paint

Date: 2026-11-18. Status: accepted.

## Context

The audit of the craft page (Kutch Ajrakh at three widths) found that what the dossier and the
stored rows already hold never reaches the page: the GI record, the dated history, the "why here"
environment story, the people with their honours, botanical names and PubChem compounds, the
pictures' roles. The tab row grew after first paint because the Shared science and Sources tabs
waited for other routes, the header showed raw register words ("Textiles based Craft Category"),
"Sources differ" gave geographic trivia the weight of chemistry, source numbers changed between
tabs and between a researcher's and a student's view, and a craft without a dossier (442 of 462)
got a single card that repeated its own header. The redesign (plan task 1A-09, corrected by both
critiques) needs one contract it can build against before any screen changes.

## Decision

1. **Schema version 2, added fields only.** Every v1 field keeps its meaning, so today's screens
   still draw; the client refuses version 1. New: `tabs`, `depth`, `suggestedQuestions`, `giCard`,
   `events`, `environment`, `sameFamily`; on the craft `displayName`, `localNames`, `familyLabel`,
   `kindLabel`; on pictures `role`; on sources-differ rows `key` and `weight`; on stages `differ`;
   on materials `botanicalName` and `pubchemCid`; on communities `placeKey`. Every list is present
   and empty when there is nothing, so the client never guards a missing list.
2. **Editorial labels and kind questions in one data file.** `backend/app/data/craft_families.json`
   (loader `data/craft_families.py`) holds a label for each of the 9 register categories and 36
   sub-categories, each kind's name for its catch-all row, three questions per kind with a
   `{craft}` placeholder and three more for its catch-all row that name no craft, validated on load
   (version 2: every register family and kind present, three questions each naming the craft
   once). A template puts the name after "of", "for", "in", "into", "on" or "make" and uses no
   pronoun, so no verb agrees with the name and "Farrukhabad Prints" reads as well as "Kutch
   Ajrakh"; substituting a lower-cased catch-all name ("What is other crafts made from?") read
   badly, so a catch-all asks about its kind instead. Labels never replace the register's own words,
   which the page keeps in `categoryName` and `subCategoryName`.
3. **Filled from what is stored, nothing invented.** The GI card, prices and workforce come from
   the rows the import already writes (`CraftGiRecord`, `CraftPrice`, `CraftWorkforce`); events add
   every other fact whose text states a year (`research/timeline.years_offered`), never a
   hypothesis, and on a curated page only curated claims. The shared year reader reads a century
   range ("the 11th to 14th century", "the 16th and 17th centuries") as one span from the first
   century's start to the last one's end, and never offers a temperature, a sum of money or a
   multiplied count as a year; a fact that reports an absence ("no record of ... before the 18th
   century") is no event. Local names stay empty: a glossary entry glosses a word, and on the 32
   dossiers a word-match published places (Konark), materials (ringal), pastes (seven kinds of dabu)
   and etymologies (Madhubani) as cited names of the craft, so the list waits for a dossier field
   that states the craft's own names. Pictures get roles by a rule
   (the first inline picture of no stage leads); dossier roles, sizes, colours after each stage,
   repeats and temperatures wait for dossier fields that do not exist yet.
4. **Disagreements weighted, not resolved.** A sources-differ row weighs 3 when it touches a
   stage or a chemistry or physics claim, 2 for another science discipline, 1 otherwise, and rows
   come heaviest first. This replaces decision 0071's "in the order served, never ranked" for the
   row order only: every side is still shown with its own citations and none is chosen.
5. **One source numbering for the whole page.** `sources` are listed in the order a reader meets
   them, then the sources only All evidence cites, so a reader without All evidence gets the same
   list cut at the end and every number agrees between views and tabs.
6. **Tabs and relatives decided on the server.** The page reads the region places and the shared
   science view itself to set `tabs`, and lists up to six of the richest crafts of its kind
   (curated first, then by stored claims, then GI, never a catch-all row) with a curated
   relative's hero and first lede sentence carrying that sentence's own citations. The hero is
   picked by the same rule and visibility as on the relative's own page
   (`craft_page_family.shown_pictures`), and the stored-claims count is the catalogue's
   (`services/craft_claim_counts`); it counts concept claims only, so it can be lower than the
   relative's own `depth.claims`, which counts every claim its page lists.
7. **Revalidation.** The route's `ETag` is the hash of the page as served (`api/public_deps.cached_read`,
   decision 0079), which changes with every curation version and differs between the two views;
   `If-None-Match` answers 304. A tag from the curation version alone would serve a stale page
   when live research writes a claim for an uncurated craft.
8. **Two goldens.** `shared/craft.page.golden.json` stays the curated Kutch Ajrakh page and
   `shared/craft.page.register.golden.json` is Farrukhabad Prints, a craft with no dossier, beside
   the Kutch Ajrakh dossier; both are written by `app.scripts.import_curation` (`--preview` and
   `--register-preview` with `--with-dossier`) and reproduced byte for byte by the backend tests and
   parsed by the client's specs.

## Consequences

- `GET /crafts/{slug}/process` has no web caller since decision 0071; it stays for voice and the
  science view and is marked for retirement.
- The page route reads more (market rows, relatives, region places, the shared-science view); each
  is a fixed number of queries.
- A student now sees 128 of the Kutch Ajrakh page's 132 claims, since the GI card, events and
  environment steps cite claims the v1 page left to All evidence.
- When the curation schema gains picture roles, sizes, stage colours or native-script names, the
  page fills the existing fields from them; the contract does not change again for those.
