# Next: handoff (2026-11-19)

Start here in a new session. The owner closed the long build session after this release.

## Live now

- **Release.** Commit `1897d80` on `main`; Deploy backend passed; frontend deployment
  `dpl_DhoBMhLgf71W3sJEzMseKFahQy3J` promoted. It carries:
  - craft page v3 with nine chapters;
  - public reading of everything except asking, and share links;
  - field voices v2 in KalaVigyan, switched off;
  - the Student and Artisan roles;
  - no caps;
  - answer richness and the wider expert panel (decision 0099);
  - the design foundation and the skills;
  - curation schema 2 with Kutch Ajrakh v2;
  - the repo-wide comment check.
- **Kutch Ajrakh.** `/crafts/Kutch-Ajrakh` serves the owner-approved monograph as built:
  - the file is `frontend/public/monographs/kutch-ajrakh/index.html` (decision 0100);
  - the published copy is https://claude.ai/artifact/YBrq1VNAZosQTbppNziK9p;
  - its build scripts are in `docs/design/monograph-build.zip`.
- **The institution's name** is "Centre of Excellence for Unified AI-Enabled Craft Ecosystem
  Platform", IIT Kharagpur. Never "for Handicrafts".

## Release steps still open (the owner has given permission)

1. **Production E2E.** Run `e2e-production.yml` without `base_url` and read the result. It
   includes the signed-out run at 360, 834 and 1440.
2. **The portals' field voices release.** designer-portal and documentation-portal have
   uncommitted work: field voices v2, sending everything except the legal floor, and the
   designer portal's identity-photo PENDING stamp.
   - Release both together: full Checks on both, the release gate, then deploy.
   - Before switching on, per portal and workspace:
     `terraform plan/apply -target=aws_iam_user_policy.media` (the `field-voices/*` objects).
   - Then set `CROSS_PORTAL_FIELD_VOICES_ENABLED` and `FIELD_VOICES_RIGHTS_HOLDER`.
   - Android only gains the PUBLICATION consent enum, and `fromWire` tolerates unknown values, so
     it ships with the next Android build. No Android release is needed now.
3. **KalaVigyan switches.** Put each value in SSM `/kalavigyan/env/*`, then `sudo kv-render-env`
   on the box. A deploy also re-renders the env.
   - `FIELD_VOICES_ENABLED=true` and `FIELD_VOICES_IMAGE_HOSTS`, then dispatch
     `field-voices-sync.yml`.
   - `ALERT_DIGEST_ENABLED=true`. The SES sender noreply@aicraft.iitkgp.ac.in is verified.
   - ElevenLabs: the owner has updated the key's permissions.
     1. From the box, verify `user_read`, `models_read`, `voices_read` and `convai_read`.
     2. Run `python -m app.scripts.provision_voice_agent --artisan`.
     3. Store `ELEVENLABS_ARTISAN_AGENT_ID` in SSM and in GitHub secrets.
     4. Set `ARTISAN_CONVERSATION_ENABLED=true`.
4. **E2E Professor and Admin accounts.**
   1. `terraform apply -target=aws_iam_role_policy.box`
   2. `backend/.venv/Scripts/python infra/scripts/seed_e2e_accounts.py`
   3. `gh workflow run e2e-accounts.yml`
5. **Never flip `field_voices.artisan_images`** before a person has reviewed the held list. It may
   contain Aadhaar cards.
6. **One critic re-scores the live Ajrakh page**, for design and chemistry together, against
   `.claude/skills/kalavigyan-craft-pages/references/page-checklist.md`. Fix to 9 or above.
   Change wording only with the owner's OK.

## Owner decisions still open

- The default of the review switch (decision 0101, item 12). The recommendation is `AUTO` for
  research and `APPROVAL` for new contributors.
- Erased testimony leaves a placeholder claim, so its concept stays listed. Should the concept be
  removed when nothing else is left?
- The short answer on the Ajrakh page says iron "oxidises with the tannic acid" (the source's
  wording; the chemistry critic flagged it).
- The text of the contribution terms and of the MCP terms of use (contributors get no public
  credit).

## The two big tracks

1. **The data architecture**: `docs/decisions/0101-knowledge-architecture-for-every-craft.md`.
   - Facts carry fields; sections are records; components form a labelled registry; one
     monograph template.
   - Retrieval is per fact; pages are rebuilt nightly as static pages; there is a review switch.
   - The database becomes the source of truth.
   - The Knowledge API and a remote MCP server: OAuth sign-in on our site with terms acceptance;
     read, ask, contribute data and layouts, open work with claim and release.
   - The Ajrakh switch-over must change nothing a reader sees.
   - Follow its build order, steps 1 to 7.
2. **The redesign of the whole app**:
   - the `kalavigyan-design` skill;
   - the boards in `docs/design/`;
   - waves 1B (landing, shell, collection, category, map), 3 (answer page), 4 (the rest) and 5
     (proof).
   - The craft page is shared with track 1, step 2: the Ajrakh design becomes the template.
   - Match boards with screenshots, not by reading code.

Later: comics on Nano Banana Pro (`gemini-3-pro-image`), and Expert auto-media (pictures, video,
film). Bringing the other 31 crafts and 9 categories to the Ajrakh level is track 1, step 6, using
`.claude/skills/kalavigyan-craft-pages` (run `scripts/gaps.py` first).

## How to work (owner rules learnt the hard way)

- **Cost.** The owner spent a USD 200 plan on this session.
  - Agents stay short: one bounded task, about 60 to 100 tool calls, a checkpoint, then stop.
  - Use Sonnet or low effort for mechanical work.
  - Run one or two lanes at a time, and release before starting more.
  - Never message a running agent; it starts a duplicate.
  - Ask before any heavy spend, with an estimate.
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
- Debt is in `docs/TECH_DEBT.md`; progress is in `docs/PROGRESS.md`.
