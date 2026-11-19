# Next: handoff (2026-11-19, night session)

Start here in a new session. The owner went to sleep and asked Claude to finish the release and
start on decision 0101's database and MCP work on its own recommendations. Every choice made
without the owner is recorded below or in decisions 0102 and 0103 for review.

## Live now

- **KalaVigyan `main` at `afa152b`.** Deploy backend passed; frontend `dpl_8Sj3NTJWGjZ85NHRXjvPRnjtQ8i9`
  promoted after it. On top of release `1897d80` it carries:
  - **Knowledge fields, step 1 of decision 0101** (migration `0032_knowledge_fields`, decision 0102):
    - `SOCIETY` and `POLICY` join the fields (16);
    - `Claim.field` and `Claim.fields`, backfilled and stamped by every writer;
    - `ArticleSection`;
    - the component registry columns on `KnowledgePiece` and `KnowledgePieceSubject`.
  - **The MCP server, slice 1** (decision 0103, `docs/contracts/knowledge-api.md`):
    - `POST <PUBLIC_API_URL>/mcp` with five public read tools;
    - switched **on** at `/kalavigyan/env/MCP_SERVER_ENABLED`; smoke-tested live.
  - **Craft page hotfixes:** every curated craft page answers 200 again (32 of 32 swept). Four
    page-build defects had been returning 500 for most curated crafts:
    - the region story's and the history timeline's choices went over their limits;
    - link-card pictures were made into plates;
    - the process ladder cited claims and sources the page did not list.
  - **The Ajrakh monograph's design fixes** that change no words (critic re-score below).
  - **The production E2E specs** read Kutch Ajrakh as the served monograph.
- **Portals 0.0.8** (designer-portal `2d468af3`, documentation-portal `28abc96d`), released together:
  - field voices for KalaVigyan;
  - question takes name their section;
  - the designer portal's identity-photo PENDING stamp.
  - Android is not published with this release; the `PUBLICATION` consent value ships with the
    next Android build.
- **Switches set this session:**
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

- **Done:**
  - **Field voices refresh on both portal boxes:**
    - designer portal: 2 images;
    - documentation portal: 501 transcripts and 613 images, with 3 originals missing from the
      bucket;
    - KalaVigyan's `field-voices-sync.yml` applied all of them, ok.
  - **Both portals' release gates** pass (`44431722874`, `44431727650`).
- **Never flip `field_voices.artisan_images`** before a person has reviewed the held list. It may
  contain Aadhaar cards.
- **The production E2E** (latest run `44432649960`): 17 passed, 10 screen runs failed, 1 skipped.
  - The Professor and Admin accounts now pass.
  - Every curated craft page renders.
  - The failures that remain are findings, not regressions from this release:
    1. **The router's prefetch of `/crafts/Kutch-Ajrakh` answers 404.** The rewrite to the static
       monograph cannot answer a React Server Components request. Readers are not affected: the
       router falls back to a full page load. Fix: links to a monograph slug
       (`next.config.ts` `CRAFT_MONOGRAPHS`) render a plain `<a>`, or an RSC request there gets a
       redirect that forces a full load.
    2. **Sanganeri's Region tab** runs about 70 screens before "All measurements", against a
       limit of 3. This is a design problem of the tabbed craft page; the redesign or track 1,
       step 2 replaces it.
    3. **The monograph** has no app theme attribute, and some small labels spill out of their
       boxes at some widths ("leucoindigo, on the fibre", the Devanagari brand). These are design
       details of the approved page; see the critique.
    4. **Occasional 500s from the five-connection database pool** under four parallel browsers
       (`docs/TECH_DEBT.md`, Infrastructure).

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

Open:
- The terms texts are drafted in `docs/legal/` for the owner and IIT's legal office.
- Artisan testimony can still be withdrawn as built (decision 0083); say whether irrevocable
  consent applies to it too.

## The two big tracks

1. **The data architecture**: `docs/decisions/0101-knowledge-architecture-for-every-craft.md`.
   - **Done:** step 1 (schema, decision 0102) and the MCP read slice (decision 0103).
   - **Step 2, first half done** (decision 0105): the Ajrakh page is structured content plus a
     template, rebuilt byte for byte by `app.scripts.build_monograph`. **Next:** load it into the
     database (sections, the 79 components, facts and sources for the 97 citations the dossier
     lacks), then move component views into specs so other crafts reuse the template. Then steps 3 (retrieval by field, components by
     label) and 4 (the gates, the review queue that grows from `admin/testimony`, nightly upkeep).
   - **MCP slice 2:** OAuth 2.1 with our web app as the authorization server, the versioned MCP
     terms, connected clients in Settings with revoke, then `ask`.
   - **MCP slice 3, after step 4:** proposals, open work, and the method as MCP prompts and a
     `kalavigyan-contributor` skill (decision 0101, item 15).
2. **The redesign of the whole app**:
   - the `kalavigyan-design` skill and the boards in `docs/design/`;
   - waves 1B (landing, shell, collection, category, map), 3 (answer page), 4 (the rest) and 5
     (proof).
   - The craft page is shared with track 1, step 2.
   - Match boards with screenshots, not by reading code.
   - The landing's "426 crafts" counts the master list's named crafts plus six from the portals,
     without the 35 "Other …" rows. Give it context when the landing is redesigned.

Later: comics on Nano Banana Pro (`gemini-3-pro-image`), and Expert auto-media (pictures, video,
film). Bringing the other crafts and 9 categories to the Ajrakh level is track 1, step 6, using
`.claude/skills/kalavigyan-craft-pages` (run `scripts/gaps.py` first).

## How to work (owner rules learnt the hard way)

- **Cost.** Agents stay short: one bounded task, about 60 to 100 tool calls, a checkpoint, then
  stop. Use Sonnet or low effort for mechanical work. Run one or two lanes at a time, and release
  before starting more. Never message a running agent. Ask before any heavy spend, with an estimate.
- **Ship approved work as built.** Do not plan rebuilds of approved pages.
- **Commits.** Author and committer are `ankits1802 <ankits1802@gmail.com>`. Never a
  Co-Authored-By line. Use `GH_TOKEN=$(gh auth token --user ankits1802)` for each gh command.
- **No code comments** anywhere; `tools/hygiene_check.py` enforces it.
- **Nothing heavy runs locally**: no database, no full suites. GitHub runs them through a PR.
- **Release backend before frontend.**
  1. Before pushing `main`, start a watcher that runs `vercel rollback <current production>` as
     soon as the new build takes the domain.
  2. After Deploy backend passes, run `vercel promote <new deployment>`.
- **Portals release together.** Fix everything, then release once.
  - Both portals' terraform state is in the `default` workspace.
  - `REPO_FACTS.md` must be regenerated on a clean tree after the last change.
- **Git Bash rewrites `/kalavigyan/...` paths** in `aws ssm` calls; set `MSYS_NO_PATHCONV=1`.
- Debt is in `docs/TECH_DEBT.md`; progress is in `docs/PROGRESS.md`.
