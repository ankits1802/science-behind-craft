# 0245. The round's leftovers: every upload path scanned, a held page's critique kept, a coded figure's films from the media store, and upgrade work for the pages built before the round

The four gaps this round's lanes named are closed. Voice and artisan recordings, the field
photographs the daily sync copies from the portals and the words a contributor gives
`supply_source` in the call pass the malware scan before anything reads or keeps them, so every path
by which a person's bytes reach the site is scanned. A page held for one confirmation keeps its
agent's design critique, shows it to the person who confirms it and carries it to the layout it
proposes. A coded figure may play a clip the page holds from the media store, through a short-lived
signed address for that clip alone, drawn with its credit and on paper as the clip's still. Every
page a contributor built before this round is raised once as open work naming what its facts could
now show, and the work drops when the page is rebuilt.

Date: 2026-11-26. Status: accepted (the lead's lane brief `ux-1126/leftovers`, on the owner's word
that no gaps are left). It amends
[decision 0241](0241-tasks-that-outlive-a-deploy-workbooks-as-they-come-slots-for-several-files-and-every-upload-scanned.md)
(its "left as they are": recordings and the other upload paths),
[decision 0237](0237-a-preview-s-pictures-read-as-a-designer-by-the-agent-and-by-the-server-only-when-asked.md)
(the critique carried only by `propose_page`),
[decision 0193](0193-components-withdrawn-replaced-or-borrowed-and-pages-held-for-one-confirmation.md)
(what a held page keeps and shows),
[decision 0231](0231-a-contributor-s-ai-writes-a-figure-s-code-over-the-page-s-cited-data.md)
(films only from `/monographs/`) and
[decision 0229](0229-a-preview-card-that-minimises-and-what-a-craft-s-facts-could-show-offered-to-judge.md)
(rule 29's opportunities, now also raised for pages built before it). The contracts are
`docs/contracts/voice.md`, `roles-and-contributions.md`, `field-voices.md`, `knowledge-writes.md`
(Supplied sources), `review-queue.md` (the layout item's critique), `open-work.md` (held pages and
the upgrade task), `nightly-upkeep.md` (step 5e), `component-specs-science.md` (coded_figure) and
`craft-page.md` (the clip routes); the runbook's Upload scanner lists every scanned path.

| For | Read |
|---|---|
| The scanner and the paths it covered first | [decision 0241](0241-tasks-that-outlive-a-deploy-workbooks-as-they-come-slots-for-several-files-and-every-upload-scanned.md) |
| The agent's critique and its rubric | [decision 0237](0237-a-preview-s-pictures-read-as-a-designer-by-the-agent-and-by-the-server-only-when-asked.md) |
| Pages held for one confirmation | [decision 0193](0193-components-withdrawn-replaced-or-borrowed-and-pages-held-for-one-confirmation.md) |
| The coded figure and its frame | [decision 0231](0231-a-contributor-s-ai-writes-a-figure-s-code-over-the-page-s-cited-data.md) |
| Rule 29 | [decision 0229](0229-a-preview-card-that-minimises-and-what-a-craft-s-facts-could-show-offered-to-judge.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- Decision 0241 scanned pictures, supplied files and datasets where each is first read, and left
  voice and artisan recordings unscanned because they go to speech to text. They are still a
  person's bytes: the relay routes hand them to `ffmpeg` to measure them before speech to text is
  paid (`voice/audio.upload_seconds`), and an artisan's turn is kept in the media bucket. Listing
  every way a person's bytes reach the site found two more: the field photographs the daily sync
  downloads from the portals and opens with Pillow to make their neutral copies, and the words a
  contributor gives `supply_source` in the call (`passages` or `text`), which are kept as the
  source's text exactly as an uploaded text file is.
- Decision 0237 copied the agent's critique onto the layout only when `propose_page` proposed it. A
  page from an account whose proposals reach readers at once is held for one confirmation instead
  (decision 0193), and confirming it ran the bundle without the critique; the person confirming
  never saw it, and the preview it came from has usually expired by then (24 hours against a hold's
  3 days).
- Decision 0231 let a coded figure play films only from files the site serves under `/monographs/`.
  The media store holds the clips the site made of a craft's stages (decision 0018), shared on the
  craft's pages once approved (`CRAFT_SHARED`, with two sign-offs for a named cluster), each labelled
  with its model; they live in a private bucket and are read only through short-lived signed
  addresses.
- Pages a contributor built over MCP before the UX round (decisions 0227 to 0234 reached main at
  7f841c1c, 2026-11-26 11:21 India time) get the renderer's improvements, but nothing asks anyone to
  use what the round's tools make possible: rule 29's opportunities, places maps on the site's base,
  coded figures.

## Decision

1. **Every path scanned.** The paths by which a person's bytes reach the site, each scanned by
   `services/malware_scan.scanned_upload` before anything reads or keeps them, with 0241's refusal
   and fail-closed rules:

   | Path | Where it is scanned | Since |
   |---|---|---|
   | A picture: the site's upload, the upload link's slot and form, a picture given in `give_pictures`, an open-licence picture | `image_screens.screened`, before it is decoded | 0241 |
   | A supplied PDF or text file | `supplied_sources.fill_supplied_slot`, before its words are read | 0241 |
   | A dataset's table or GeoJSON | `dataset_proposals.fill_dataset_slot`, after its SHA-256, before it is parsed | 0241 |
   | A voice call's relay turn (`POST /api/voice/session/{id}/turns`) | `voice/audio.scanned_seconds`, before it is measured or decoded | 0245 |
   | An artisan conversation's relay turn (`POST /api/artisan/conversations/{id}/turns`) | the same, through `ArtisanUpload.measured` | 0245 |
   | A field photograph the daily sync copies from a portal | `field_voices_images.ImageCopier.copy`, after its size and SHA-256 match, before Pillow opens it | 0245 |
   | Words given to `supply_source` in the call (`passages` or `text`) | `supplied_sources.supply_source`, whole as they are kept, before the identity is looked up | 0245 |

   A recorded turn the scan refuses answers 422 with the signature's name, and a scanner that does
   not answer 503, both before a second is claimed, so no turn is taken or counted. In the field
   voices sync a found signature refuses its page, as an undecodable picture does, and a scanner
   that does not answer stops the pictures stream for that run unread, not counted as a refused
   page, for the next run to read again. Words supplied in the call are refused as a tool error and
   nothing is kept. Not paths of a person's bytes, so not scanned: an ElevenLabs agent call (its
   audio goes to ElevenLabs, never to the site), the portals' transcripts (text in signed JSON
   pages), the pictures the site's own searches find until one is given as an open-licence picture,
   what the site's providers make (illustrations, clips, narration, a film's score), the pages the
   fetcher reads and the pictures the renderer draws.
2. **A held page keeps its critique.** `hold_page` stores the account's latest live critique of the
   page (`page_critique.latest_critique`) on the hold (`PageHold.critique`). `PageHoldView.critique`
   carries it, and the held page shows it under its parts as the agent's design critique
   (`AgentCritique`, whose heading is an `h2` there). Confirming runs the bundle as before and
   copies the hold's critique onto the layout it proposes (`page_critique.carry_critique`, which
   `attach_critique` now shares), so the layout's reviewer sees it on the Review page as for any
   proposed layout, even after the preview has expired. A hold with no critique of the same account
   and page carries none. The critique still never gates.
3. **Films from the media store.** A coded figure's film is either `{key, src}` (a file under
   `/monographs/`, as before) or `{key, clip}` (a media-store asset id), never both or neither. A
   clip is one the page holds when it is the `CRAFT_SHARED` page copy of a `SUCCEEDED` `VIDEO` job
   with its model and alt text, made from at least one fact the figure's units cite: a claim
   carries no craft of its own, so a shared fact is what ties the clip to the page that holds the
   figure's facts (`services/coded_clips.filmed_spec`, run by `checked_drawing` beside the map
   placement). Any other clip is refused in one sentence naming the film's key and the clip. The
   server writes each clip film's `credit`, "AI video, made with <model> on <day>" (the day in India
   time), replacing any the agent sent, since a published spec's re-check carries it back. On the
   page the figure starts its frame only after `GET /api/crafts/media/{id}/film` answers
   `{url, expiresAt}`: a signed address of that one page copy, valid 300 seconds
   (`CLIP_LINK_SECONDS`), `Cache-Control: no-store`, 404 for anything but a shared clip and 503
   without a bucket. The frame receives it in `kv-films`, and its policy's `media-src` names exactly
   that address's origin and path (https only, no query, no folder, no whole host), so the frame can
   fetch that object and nothing else and can list nothing; a clip whose address could not be had is
   left out and the figure's still stands. The credit is drawn under the figure. On paper the
   export draws the clip's still beside the figure's own: a JPEG frame from the clip's middle, cut
   once by `ffmpeg` (`services/clip_stills`, through an injected cutter) and kept beside the page
   copy (`naming.clip_still_key`), served at `GET /api/crafts/media/{id}/still`, which is how the
   export's picture reader, limited to the site's and Commons' hosts, reaches it; a clip with no
   still keeps its credit line alone. The one runner of a local program moved down to
   `core/programs.run_program`, which the voice decoder and the still cutter share.
4. **Upgrade work for older pages.** A page counts when a contributor built it (the layout version
   of its latest approved `LayoutProposal`) and that layout was written before the round reached the
   site (`research/page_upgrades.UPGRADE_CUTOFF`, 2026-11-26 11:21 India time); Kutch Ajrakh and
   pages whose layout only the site wrote are left out. The nightly upkeep's step 5e raises one
   `PageUpgrade` row per such page (`ON CONFLICT DO NOTHING` on one row a page, so never twice),
   holding its layout version and the lines its facts could now show, read from the live stored
   document: rule 29's opportunities exactly as the preview reads them; a places map on the site's
   base when the page states places and draws none, or a line for each places map that says nothing
   of what it is about; and a figure, a `coded_figure` among the ways, for each chapter with three
   cited paragraphs or more and no figure (three because Kutch Ajrakh's market chapter, its fullest
   of prose, sets three figures beside nine paragraphs). A page with no stored document waits for a
   later night. Open work lists it as `UPGRADE_PAGE:<subject>:<slug>` (prompt `deliver_page`, the
   subject's priority, after the page tasks), naming the lines and the playbook
   (`kalavigyan://skills/references/playbook.md`). It is closed while a layout proposal made since
   it was raised waits for review, opens again if that proposal is rejected, and drops for good once
   a newer approved contributor layout is written; a component swapped in place or the site's own
   backfill writes a layout version too, so neither counts as a rebuild.
5. **The design skill.** The held page's critique and a clip's credit are drawn in the design (the
   credit in Plex at the caption size in ink-3, under its figure). A clip plays only as the coded
   figure's code plays it, so under either reduced-motion switch the frame holds it still, as
   decision 0231 already enforces. Nothing here departs from the skill.
6. One migration, `0124_leftovers` after `0123_mcp_tasks`: `PageHold.critique` and the `PageUpgrade`
   table (row level security on, closed to the public roles).

## Consequences

- Tested both ways. Recordings: `backend/tests/voice/test_recording_scans.py` (a recording scanned
  whole before it is measured; the EICAR test file and a down scanner refused before it is measured,
  through `scanned_seconds`, the voice call's turn route, which takes no turn, and the artisan
  route's upload). Portal photographs: `backend/tests/field_voices/test_image_copies.py` (scanned
  whole before decoding; EICAR and a down scanner leaving nothing stored) and `test_sync.py` (a down
  scanner stops the pictures unread without a refused page; a found signature refuses its page).
  Supplied words: `backend/tests/db/test_upload_scans_db.py` (scanned whole and kept; refused with
  nothing kept for EICAR and for a down scanner). Held critiques:
  `backend/tests/db/test_design_feedback_db.py` (a held page shows the latest critique and carries
  it to its layout and the review item after the preview expired; another account's hold carries
  none) and `frontend/e2e/page-holds-unit.spec.ts` (the critique drawn as a section of its own,
  waiting or confirmed; none drawn without one; one off its contract refused). Films:
  `backend/tests/research/test_coded_figures.py` (both or neither of `src` and `clip` refused, a bad
  clip id refused), `backend/tests/db/test_coded_clips_db.py` (a held clip credited; a private one,
  an image, a failed job, another facts' clip and a missing one refused),
  `backend/tests/media/test_clip_routes.py` (the 300-second address, 404 and 503, the still cut once
  and kept, none when the copy is missing or the cut fails), `backend/tests/test_programs.py`,
  `backend/tests/exports/test_coded_figure_export.py` (the still and credit on paper, the credit
  alone without a still) and `frontend/e2e/coded-clips-unit.spec.ts` (`media-src` exactly the signed
  object, `kv-films` carrying it, a figure without clips unchanged, a failed address left out, the
  credit drawn). Upgrade work: `backend/tests/research/test_page_upgrades.py` (the cutoff, each line
  both ways, the task's key, text and place) and `backend/tests/db/test_page_upgrades_db.py` (raised
  once and not again, which pages count, the task listed, closed while a rebuild waits, open again
  when it is rejected and dropped by a newer approved layout).
- `backend/tests/public/test_route_inventory.py` lists the two clip routes, and
  `frontend/lib/ownProposalsContract.ts` the new task kind.
- For the owner: the first nightly upkeep after the release raises the upgrade work of every page
  built before the round, once; the upkeep report's `pageUpgrades` names them.
- Left as they are: a clip's signed address is not renewed while a reader keeps the page open, so a
  film not yet loaded 300 seconds after the frame started stays still until the page is opened
  again; a clip's still is cut on its first export, not when the clip is made.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
