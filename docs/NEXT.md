# Next

Start here in a new session: what is live now, the release status, the owner's decisions, the two
big tracks and how to work. The lead keeps it current. Every choice made without the owner is
recorded below or in decisions 0102 and 0103 for review.

| For | Read |
|---|---|
| Everything done, in order | [PROGRESS.md](PROGRESS.md) |
| What is knowingly below standard | [TECH_DEBT.md](TECH_DEBT.md) |
| How to deploy, switch on and roll back | [RUNBOOK.md](RUNBOOK.md) |
| The owner's standing direction | [PLAN.md](PLAN.md), section 0 |

The current handoff is the quality round of 2026-11-24 to 2026-11-25: the owner judged the pages
built over MCP below the Kutch Ajrakh bar and had every lane that closes the gap built in parallel;
the lanes before the last four were released one at a time, the last four at once (the owner,
2026-11-25, this once). Releases go back to one at a time, each verified on production.

## Live now

- **KalaVigyan `main` with the quality round** (2026-11-25, decisions 0191 to 0210, PROGRESS.md,
  Quality round). Verified on production alone: `4911166e` (relief), `8796f591` (preview and
  budget), `4e5a6a96` (pictures), `e60b43db` (lifecycle), `d53aead5` (colour key), `2d9b5194`
  (maps), `fc180ebb` (interactives), `c88db1a9` (art kit), `093c19f5` (colours), `63d10f1c`
  (render review), `d61e3ed4` (guidance), `60b779a5` (kit players), `92fcf17a` (smoke and renderer
  installer), `3b0049eb` (answer figures, migration 0111), `fa3f1443` (exports), `2d7e7286` (phone
  budget and admin curation, migration 0104). Then the batch of PR #192: picture relevance (0207),
  downloads (0208), the phone's first screen (0209) and Sanganeri's parity (0210, migration 0117).
  - **Answers** after answer figures (run 45529163130, four questions): rubric 0.975, judge 0.81,
    $0.29; the judge's drop was three off-topic pictures stored before the round, which 0207 stops
    serving.
  - **The renderer** (`kv-renderer`, chrome-headless-shell on 127.0.0.1:8091) draws previews on
    the box; its installer resolves Ubuntu's t64 package names.
  - **Admins** remove and edit published content over MCP by staging it; nothing changes until a
    person confirms the batch on the Review page.
- **Before the quality round:** `main` at `401f73ae` (2026-11-24, decision 0190).
- **KalaVigyan `main` at `401f73ae`** (2026-11-24, decision 0190). Every release of the round was
  verified on production before the next: `1e366637` (0182), `dab903fd` (0183), `db1efa4a` (0184),
  `b9178d42` (0185, migration `0101_oauth_code_token_version`, the chain's head), `b72cd8b4` (0186),
  `8dde0612` (0187), `6a56f435` (0188), `6cd9385e` (0189) and `401f73ae` (0190).
  - **Generated craft pages** are drawn in the approved Kutch Ajrakh form (masthead, contents,
    margin notes, the five source groups); Kutch Ajrakh keeps its authored shell.
  - **Answers:** the last whole answer-quality run (45230293916) answered 24 of 24 at rubric 0.930
    and judge 0.807; the rubric floor is 0.88 and an unscored question breaks it. Four-question
    samples after the releases that touched answers held (rubric 0.976, judge 0.84 and 0.86, $0.48
    and $0.26).
  - **Voice:** the reader agent's turns are bound and answered (decision 0190: a cited reply in
    10.1 s). The call stays switched off (`VOICE_CALL_ENABLED` false) and `voice.transport` stays
    `RELAY` until the owner chooses the agent.
  - **Security:** an MCP code approved before a password change no longer opens a connection; a
    hostile robots.txt or compressed body can no longer hang or flood the fetcher.
  - **Releases:** stored pages are rebuilt only by the release that serves them, and Deploy backend
    refuses a commit older than the one production serves.
- **Portals 0.0.8** (designer-portal `2d468af3`, documentation-portal `28abc96d`), released together:
  - field voices for KalaVigyan;
  - question takes name their section;
  - the designer portal's identity-photo PENDING stamp.
  - Android is not published with this release; the `PUBLICATION` consent value ships with the
    next Android build.
- **Switches set in the sessions of 2026-11-19 to 2026-11-21:**
  - Parameter Store:
    - `ALERT_DIGEST_ENABLED=true` (SES has production access, and the domain is verified with DKIM);
    - `ARTISAN_CONVERSATION_ENABLED=true` with `ELEVENLABS_ARTISAN_AGENT_ID=agent_0901m7rcnsz5f379ejhxyd47bbqv`
      (key permissions checked from the box: all four answer 200; the agent id is also a GitHub secret);
    - `FIELD_VOICES_ENABLED=true` and `FIELD_VOICES_IMAGE_HOSTS`;
    - `MCP_SERVER_ENABLED=true`.
  - Both portal repositories' Actions variables: `CROSS_PORTAL_FIELD_VOICES_ENABLED=true` and
    `FIELD_VOICES_RIGHTS_HOLDER`.
  - The `field-voices/*` grant is applied to both portals' media keys.
  - The box policy reads `/kalavigyan/e2e/*`; the Professor and Admin E2E accounts are provisioned.
- **Kutch Ajrakh.** `/crafts/Kutch-Ajrakh` serves the owner-approved monograph
  (`frontend/public/monographs/kutch-ajrakh/index.html`, decision 0100; published copy
  https://claude.ai/artifact/YBrq1VNAZosQTbppNziK9p; build scripts in `docs/design/monograph-build.zip`).
  - The served file now has one override block, `style#kv-release-fixes`. The published copy and
    the build scripts do not have it.
- **The institution's name** is "Centre of Excellence for Unified AI-Enabled Craft Ecosystem
  Platform", IIT Kharagpur. Never "for Handicrafts".

## Release status

- **Proof on production:** the first clean production questions run, 45292939163 (38 of 38,
  2026-11-24); parity 25 of 25 after every release; CloudWatch without errors but one false
  stored-page alarm, whose cause decision 0190 fixed.
- **Phone speed:** CI's phone budget (decision 0205: 360 px, CPU 4x, slow 4G, HTTP/1.1) measures
  Kutch Ajrakh's largest element at 2.79 s after decision 0221 (4.61 s before), blocking 183 ms:
  the masthead photograph is asked for before the faces and only the kit rules of the boxes a page
  draws block its paint. The 2.5 s target waits on the two Newsreader faces sharing the network with
  the photograph (their priority, and Newsreader italic's preload for one caption line, are the
  design's choice) (`docs/TECH_DEBT.md`, Speed left after the quality lane). Lighthouse at 360 on
  release dab903fd: Kutch Ajrakh 83 with an LCP of 4.68 s; 98 to 100 at 1440.
- **The register** (`docs/TECH_DEBT.md`) holds 46 entries, most waiting on the owner or on time.
  Among the lead's: the ElevenLabs tool calls, languages and CSP hosts; the relief bands' rebuild;
  a rollback's window before its pages are rebuilt; the Listen dock's first focus; the write-back
  rows stored before decision 0188.
- **Never flip `field_voices.artisan_images`** before a person has reviewed the held list. It may
  contain Aadhaar cards.

## Owner decisions (2026-11-19)

Settled:
- The rights holder stays the Centre; the MCP server stays on.
- Ajrakh: wordings 1 to 6 applied, the question removed from the page, design fixes 6, 7, 8, 11, 12
  and 13 applied; wordings 8, 9, 11 to 14 left as they are; wording 7 waits for a source
  (`docs/design/ajrakh-critique-2026-11-19.md`, Applied).
- The review switch defaults to `AUTO` for research and `APPROVAL` for contributors and agents.
- Consent cannot be revoked: an approved contribution stays published.
- When erased testimony leaves a concept with nothing else, the concept goes (to build with the
  review queue).
- The contribution terms, the image declaration and the MCP terms of use, version 2026-11-19, are
  approved (`docs/legal/`). The MCP terms are served from `backend/app/data/mcp_terms_of_use.md`,
  held equal to the approved text by a test; a new version changes both and
  `research/oauth_rules.MCP_TERMS_VERSION`.
- The nightly build's Vercel deploy hook (`nightly-pages`, branch `main`) is created and stored as
  SecureString at `/kalavigyan/env/VERCEL_DEPLOY_HOOK_URL`; the next deploy renders it into the
  box `.env`.

Open:
- Artisan testimony can still be withdrawn as built (decision 0083); say whether irrevocable
  consent applies to it too.

## The two big tracks

1. **The data architecture**: `docs/decisions/0101-knowledge-architecture-for-every-craft.md`.
   - **Done:** step 1 (schema, decision 0102), the MCP read slice (decision 0103), the Ajrakh page
     as structured content and loaded into the database (decision 0105).
   - **Round 1, integrated on `track1`:** step 3 (retrieval by field, components by label), step
     4's gates, review switch and nightly upkeep, MCP slices 2 (OAuth, terms, connected apps) and
     3 (open work, `propose_fact`, `propose_component`, prompts, the contributor skill), nightly
     static builds, the bulk export (`docs/PROGRESS.md`).
   - **Round 2, integrated on `track1`:** the unified review queue, MCP `ask` and
     `start_image_upload`, approved pictures on craft pages, contribution screens, the dossier
     export and the curation skill on the write path (`docs/PROGRESS.md`).
   - **Round 3 (decision 0106):** the split, the document API, `PageLayout`, generated documents,
     all 42 component kinds as specs with React views, the React renderer. The parity proof passed
     on 2026-11-20 and `/crafts/Kutch-Ajrakh` draws its document.
   - **Rounds 4 and 5 (2026-11-20, released):** retrieval and MCP finished, every craft as its
     English document (decision 0107), field coverage everywhere (`docs/contracts/coverage.md`).
     Curated crafts keep the tabbed page as a bridge until their documents carry their structure.
   - **Round 6 (2026-11-20, released):** every curated craft drawn as its document (the tabbed
     page retired), the structure write path (`propose_structure`, decision 0108), signed-out pages
     refreshed when content changes, 70 of Kutch Ajrakh's 79 components as native views under
     parity.
   - **Round 7 (2026-11-20):** MCP is where knowledge is created. Contributors work in parallel
     through a queued, batched, idempotent proposal flow with trust tiers, stewardship and a cost
     ledger; deliver facts, structure, components (42 kinds and five general kinds) and whole
     pages, previewed before submitting; give pictures in every format straight from the chat,
     screened before review; and follow one body of method served over MCP (the page checklist,
     source rubric, quotes, fields, component and dataset guides). Knowledge heals itself and
     expert seats research their thin fields live. The landing leads everyone into reading, the
     map is drawn from Natural Earth on the Survey of India outline with relief, rivers and
     minerals layers, curated documents read as the board, and the release gate checks every
     deploy (post-deploy pages and MCP, a real OAuth MCP client, accessibility and performance).
   - **Round 7 quality, the debt round and the review round (2026-11-21 to 2026-11-24, released):**
     the register cleared lane by lane and kept so it can only shrink, two whole-codebase
     adversarial reviews and their fixes, and every release proved on production
     (`docs/PROGRESS.md`).
   - **Content:** arrives through MCP over time; the paid completeness run stays off.
2. **The redesign of the whole app**:
   - the `kalavigyan-design` skill and the boards in `docs/design/`;
   - waves 1B, 3 and 4 released in rounds 4 and 5 (landing, shell, atlas, category hub, map,
     answer page, every signed-in screen); wave 5 (proof) runs in round 6: every screen matched to
     its board with **Capture screens** on previews (round 6 matched the landing, atlas, hub, map,
     sign-in, phone appbar and the craft without a monograph); the production E2E suite and the
     design guard brought to the redesign.
   - The craft page is shared with track 1, step 2.
   - Match boards with screenshots, not by reading code.
   - The landing's "426 crafts" counts the master list's named crafts plus six from the portals,
     without the 35 "Other …" rows. Give it context when the landing is redesigned.

Later: comics on Nano Banana Pro (`gemini-3-pro-image`), and Expert auto-media (pictures, video,
film). Bringing the other crafts and 9 categories to the Ajrakh level is track 1, step 6, using
`.claude/skills/kalavigyan-craft-pages` (run `scripts/gaps.py` first).

## How to work (owner rules learnt the hard way)

- **Cost.** Agents stay short: one bounded task, about 60 to 100 tool calls, a checkpoint, then
  stop. Use Sonnet or low effort for mechanical work. At most five agents per round, on files that do not
  conflict (owner, 2026-11-20), each in its own worktree. Never message a running agent. Ask before any heavy spend, with an estimate.
- **Ship approved work as built.** Do not plan rebuilds of approved pages.
- **Commits.** Author and committer are `ankits1802 <ankits1802@gmail.com>`. Never a
  Co-Authored-By line. Use `GH_TOKEN=$(gh auth token --user ankits1802)` for each gh command.
- **No code comments** anywhere; `tools/hygiene_check.py` enforces it.
- **This machine is for development only** (owner, 2026-11-20): no tests, type-checks, builds,
  dev servers or browsers run locally, only formatters and linters on changed files. Push the
  branch to `deploy` and open a (draft) PR; Backend checks, Frontend checks and Hygiene run on
  any PR. Visual checks go through the **Monograph parity** workflow or a Vercel preview.
- **Release backend before frontend** is automatic: a push to `main` that changes the API runs
  Deploy backend, whose last step starts the web build through the Vercel deploy hook; a push
  that changes only the web app runs **Deploy web app** at once (`docs/RUNBOOK.md`).
- **Portals release together.** Fix everything, then release once.
  - Both portals' terraform state is in the `default` workspace.
  - `REPO_FACTS.md` must be regenerated on a clean tree after the last change.
- **Git Bash rewrites `/kalavigyan/...` paths** in `aws ssm` calls and `/crafts/...` workflow
  inputs; set `MSYS_NO_PATHCONV=1`.
- **One lane at a time** (owner, 2026-11-24): each change is released and verified on production
  before the next; lanes that touch the same subsystem never run together, and this machine runs
  at most two or three agents at once.
- Debt is in `docs/TECH_DEBT.md`; progress is in `docs/PROGRESS.md`.

## How this document is kept true

| Part | Kept true by |
|---|---|
| Live now and release status | the lead, at each release, from the deployed commit (`/api/version`) and the Vercel deployment's state |
| Owner decisions | the owner's words, dated; settled ones also land in a decision record |
| The two big tracks | [PROGRESS.md](PROGRESS.md), which records each round as it is integrated |

Re-read it at the start of every session and after every release.
