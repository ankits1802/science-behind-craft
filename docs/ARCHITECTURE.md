# Architecture

How KalaVigyan is put together today: the pieces, the layers inside the backend, the direction
imports may point, and the contracts between lanes. The target design is `docs/PLAN.md` (section
0 overrides the rest); this page describes what exists and is updated in the same change that
makes it untrue.

Last reviewed: 2026-11-16.

## Deployed pieces

```
browser
  -> Vercel (Next.js App Router, frontend/)        lib/server/apiProxy.ts adds x-web-proxy-secret
  -> CloudFront d89rsltpszebp.cloudfront.net       HTTPS ends here
  -> nginx :80 on EC2 kalavigyan-api (ap-south-1)  403 without X-Origin-Verify
  -> uvicorn app.main:app, blue/green on 8000/8001
  -> Postgres 17 on Supabase (session pooler :5432; vector, postgis, pg_trgm, unaccent, citext)
```

Media goes to the private S3 bucket through presigned URLs. Ids, names and the deploy sequence
are in `docs/RUNBOOK.md`; what the box assumes from the code is in `docs/contracts/infra.md`.

## Repository map

| Folder | What it holds |
|---|---|
| `backend/` | FastAPI API, SQLAlchemy models, Alembic migrations, tests (uv, Python 3.14) |
| `etl/crafts/` | Craft data pipeline: aliases, Wikidata links, seed claims. Reuses `backend/app/data/` |
| `etl/geo/` | Per-district environment statistics from open datasets (`geo_etl`), and `load.py` |
| `frontend/` | Next.js web client (npm, Node 26) |
| `infra/` | Terraform, deploy scripts, systemd units, secret seeding, Supabase lockdown SQL |
| `shared/` | Files checked by more than one side (`craft-master.sha1`, the `*.golden.*` contract files) |
| `tools/` | Developer tooling: `hygiene_check.py` and the `hygiene` package with its tests |
| `docs/` | Plan, architecture, catalogue, contracts, decisions, debt, progress, runbook, data sources |
| `.claude/skills/` | Practice skills (engineering, backend, frontend), naming, frontend design system |

## Backend layers

```
entry points   main.py   api/ (router.py, routes/<area>.py)   scripts/ (seeds, sync, coverage job)
                 |
voice          voice/       voice sessions, the custom-LLM turn, relay turns, the encrypted
                            transcript, daily upkeep, agent provisioning (decision 0017)
media          media/       stage illustrations and clips: claim set, prompt, bundle, MP4 and
                            PNG checks, the job routes' steps, the kv-worker queue and its SQL;
                            worker.py runs it as kv-worker (decision 0018)
                 |
adapters       providers/   model adapters, AI router, spend rules, the quota ledger, ElevenLabs
                 |
domain         services/    crafts, knowledge view, access roster, credentials, keys, routing,
                            live-research write-back and the coverage job (decision 0011)
               schemas/     request and response bodies, and the science, region, voice and
                            media contracts (decision 0014), which reuse research/'s shapes
               science/     the science engine: formulas, balancing, pint units, stage
                            envelopes, the process view built from stored rows (decision 0015)
               geo/         the region profile and map layers: places, state aggregates,
                            facets, the layer registry and its classes (decision 0016)
                 |
planner        planner/     plan call, facet coverage, parallel live search across the
                            source adapters, dedupe, reading through the fetcher, open-access
                            copies and cited DOIs into an evidence pack (decision 0009)
                 |
composer       composer/    evidence pack to cited candidates, the COMPOSE call, the
                            per-sentence post-checks, one regenerate (decision 0010)
                 |
retrieval      retrieval/   stored-knowledge search: craft-scoped claims and chunks, full text
                            and pgvector fused by RRF, chunking and embedding fill
                 |
sources        sources/     external research sources: paced HTTP, record rules, one adapter
                            per service (sources/scholarly/: OpenAlex, Crossref, ...;
                            sources/reference/: Wikipedia, Wikidata, PubChem, Commons;
                            sources/web/: SearXNG, Brave, the fallback), the fetcher client
                 |
fetcher        fetcher/     the separate kv-fetcher process: address-pinned https fetch,
                            robots.txt, caps, trafilatura and pypdf extraction (no DB, no AWS)
                 |
contracts      research/    research and answering types, protocols, post-check rules
                 |
shared         core/        settings, db, security (passwords, tokens, secret keys), roles,
                            deps, logging, rate limits, India time, HTTP revalidation, work
                            shielded from a leaving caller
                 |
foundation     models/      ORM tables          data/   vendored datasets and pure loaders
```

The allowed import edges are the table `LAYER_IMPORTS` in `tools/hygiene/layers.py`, listed in
the project bindings (`.claude/skills/engineering-practices/references/project-bindings.md`).
The hygiene check fails on any other edge, including late imports inside functions, and on any
package under `backend/app` that has no row yet. Two placements are deliberate and recorded:
`core/deps.py` imports `models.User` because the current-user dependency returns the ORM row,
and `providers/` imports `services/` for the model catalogue, app settings and managed keys
(decision 0001). `schemas/` imports `research/` so the HTTP contracts reuse its citation, source
and sentence shapes (decision 0014). `science/` imports `schemas/` for the process contract's rules; since
`services/` may not import `schemas/`, `services/craft_process` reads the rows into
`science/records` and the route hands them to `science/process_view` (decision 0015). `geo/`
follows the same pattern: `services/region_records` and `services/map_layer_store` read rows
into `geo/records`, and the routes hand them to `geo/region_view` and `geo/layers` (decision
0016).

## API surface

All routes are under `/api` except `/health` and `/health/ready`. Route groups (`api/routes/`):
`auth`, `password_change` (change-password and the first-password nonce, decision 0028), `two_factor`, `me`, `access`, `users`, `crafts`, `knowledge`, `map_layers`, `media`, `secrets`,
`settings`, `usage`, `voice`. Shapes, headers and error forms are in `docs/contracts/backend.md`; the web client's
side is `docs/contracts/frontend.md`. `GET /api/crafts/{slug}/process` (in `crafts`) answers a craft's
stages, materials, conditions and reactions (`docs/contracts/science.md`);
`GET /api/crafts/{slug}/region` its places and their environment, and `GET /api/map/layers` and
`/api/map/layers/{layer}` (in `map_layers`) the district choropleths, all from the stored
district statistics (`docs/contracts/region.md`).

## How a question is answered today

1. `POST /api/answers/stream` (`api/routes/knowledge.py`) checks the mode against the asker's
   capabilities (`DEEP` for researchers and above) and the per-user ask rate limit, builds the
   answer pipeline with the asker's principal (so the router's per-role daily cap and monthly
   ceiling apply) and streams `services/answering.answer_question` through
   `research/stream.event_stream`, which sends each event as it is produced and a heartbeat
   after 60 s of silence (decision 0012).
2. The craft is resolved by `services/craft_resolver.DatabaseCraftResolver` (decision 0004):
   the slug when the learner picked one, otherwise exact, fuzzy, family and region matching
   over every craft's names, aliases and spellings, and pgvector neighbours when that leaves no
   clear winner. `RESOLVED` answers, `AMBIGUOUS` offers up to five pills, `NONE` asks for the
   craft.
3. `VERIFIED`: the craft's verified and reviewed claims are ordered into sections
   (`knowledge_view.claims_for`, `answer_events.stored_answer_events`); no model is called.
4. `HYBRID` and `DEEP`: the planner (decision 0009) plans facets and queries, searches stored
   claims and, for what they do not cover (every facet in `DEEP`), scholarly, reference and web
   sources, and reads the best documents; the composer (decision 0010) writes cited sentences
   with per-sentence post-checks; the answer and what was found are kept (an `Answer` row and
   `store_live_research`, decision 0011, run as shielded work that finishes even when the
   learner leaves, decision 0016), and each sentence is sent with the citations of the
   stored claims it rests on, including the ones just written. `status` events mark each step.
5. Another answer language (decision 0023): the answer is still composed and checked in
   English; `services/answer_translation` then translates it in one `TRANSLATE` call, keeps a
   translation only when its numbers, formulas, units and script check out (else the sentence
   stays English), copies the citations, and caches claim translations in `ClaimTranslation`. The
   planner adds native-language Wikipedia and Wikidata queries and searches stored claims with an
   English rendering of the question.
6. Nothing cited: `not_enough_evidence` says what was searched; any failure is one `error`;
   `done` always ends the stream.

## How a voice call is answered

1. `POST /api/voice/session` (`api/routes/voice.py`, `voice/sessions.py`) checks capability, a
   verified email, the voice notice consent, the craft, configuration, one live call per user, the
   day's `VOICE_SECONDS` and the platform's live calls, creates the `VoiceSession` and its `VOICE`
   `Conversation`, and loads the craft's claim pack into the process (`voice/pack.py`). `RELAY`
   answers the recording limits; `AGENT` fetches an ElevenLabs conversation token, binds the
   conversation id to the row with a stored nonce hash (decision 0017) and holds the call's whole
   length in the quota ledger (decision 0022). The user's ended agent calls are reconciled first.
2. `AGENT`: ElevenLabs calls `POST /api/voice/llm/v1/chat/completions` with the bearer and the
   conversation id header; `voice/agent_turn.py` finds and checks the bound row, ends the call at
   its length or turn cap, and `voice/llm.py` streams the turn.
   `RELAY`: the browser uploads each recording to `POST /api/voice/session/{id}/turns`;
   `voice/audio.py` measures it, `voice/relay.py` claims the turn under the session row's lock
   (a minute held, one of 40 turns), runs speech to text, writes back the unheard part, then the
   turn and text to speech, and streams the turn events.
3. A turn (`voice/turns.py`) ranks the pack's claims against the scrubbed question (rendered in
   English first when it is not in Latin script), speaks stored claims (`VERIFIED`) or makes one
   checked `VOICE_TURN` compose (`HYBRID`), translates what it will say into the session language
   (`answer_translation.translated_sentences`, decision 0025), and saves the turn to the encrypted
   transcript with an `Answer` row and its seconds in one transaction.
4. Every day `app/scripts/voice_upkeep` closes calls left open, purges transcripts after 30 days and
   reconciles agent calls with ElevenLabs in both directions (refund or charge).

## How a stage illustration is made

1. `POST /api/media/jobs` (`api/routes/media.py`, `media/jobs.py`) checks the capability, answers a
   repeated key, derives the stage's claim set from stored rows (`media/rows.py`,
   `media/claim_set.py`), builds the versioned prompt and its hash, answers a shared asset with the
   same hash at once, else holds the first route's estimate (`providers/media_router.py`) and, in
   one transaction under a per-user lock, writes the job, one quota unit and a `Job` row.
2. `kv-worker` (`app/worker.py`, `media/queue.py`) claims `Job` rows per queue (4 images, 2 videos)
   with `SKIP LOCKED`; `media/runner.py` opens the HMAC bundle, releases the hold, calls Gemini
   through the media router (one reservation per call, the Interactions API in
   `providers/gemini_media.py`), checks the PNG or strips the MP4's audio, names the file
   (`services/naming.py`), uploads it to the private bucket (`services/object_store.py`) and stores
   the labelled asset, or retries, or ends the job with a refund.
3. `GET /api/media/jobs/{id}` answers the requester with a fresh 900 s presigned URL.

## Data

Tables follow DR's Prisma naming (quoted PascalCase tables, camelCase columns) so the portals
stay mergeable; the full list is `backend/app/models/` and `backend/migrations/versions/`.
Craft data is vendored from the designer portal (`docs/contracts/crafts.md`); district and
environment data come from open datasets (`docs/contracts/geo.md`, `docs/DATA_SOURCES.md`).
Seeds (`app/scripts/seed_crafts`, `seed_claims`, `seed_districts`) run on every deploy and are
idempotent. `seed_claims` also runs the science seed (`app/data/science_seed.json`: constants,
materials, compounds, reactions, readings; decision 0015); `app/scripts/link_compounds` looks
the seeded compounds up in PubChem. After them, `app/scripts/sync_portal_crafts` adds every craft the two portals hold
beyond the master list, with their aliases, spellings and merge redirects, through the signed
peer route of `docs/contracts/portal-craft-feed.md`; it also runs daily (decision 0003).
Then `app/scripts/embed_craft_descriptors` fills missing craft name-and-alias vectors for the
resolver; the daily Coverage enrichment run fills them first too (decision 0016). The region
routes read the geo ETL's per-district statistics and compute state aggregates in Postgres per
request; nothing environmental is queried live (decision 0016).

## Frontend

Next.js App Router. Signed-in screens are under `app/(protected)/` (ask, crafts, map, settings,
admin); `app/api/` holds route handlers that proxy auth and session calls; `lib/api.ts` is the
one API client and `lib/server/apiProxy.ts` the server-side proxy. Generic components are in
`components/ui/`, domain components in `components/<area>/`. Design rules are the
`field-repo-frontend`, `motion` and `gsap` skills; practice rules are `frontend-practices`.

Who sees what is decided in `lib/permissions.ts`: the five roles' ranks and labels (checked
against `shared/roles.json`) and one route guard per admin area. The nav and the settings hub
show an admin area only when its guard admits the viewer, so the two cannot disagree; the
server checks every request again with `core/roles.py` (decision 0024).

The craft page reads the profile, then the process and region routes, each parsed by its
contract shape and cross-checked at the boundary (`lib/craftProfile.ts`, `lib/processView.ts`,
`lib/regionView.ts`); one citation numbering per page reaches every chip through
`components/craft/CitationContext.tsx`. `/map` draws craft places as pins and the environment
layers as district choropleths on `public/boundaries/district-shapes.json`, clipped to the
DataMeet outline, with no tile basemap (`components/map/`, decision 0019).

Voice (decision 0020) is a dock (`components/voice/`) over one controller, `lib/voiceCall.ts`,
which runs the consent, session, timer and client-tool checks and takes its transports
(`lib/voiceRelay.ts`, `lib/voiceAgent.ts`) and adapters as arguments: the voice routes
(`lib/voiceSession.ts`), ElevenLabs (`lib/elevenLabsAgent.ts`, the only module that loads the
SDK, on demand), and the microphone and speech player (`lib/voiceDevice.ts`). The CSP's
`connect-src` is `next.config.ts`.

Generated media (decision 0021) is one store per craft page, `lib/craftMedia.ts`, created above
the tabs by `components/craft/useStageMedia.tsx`: it reads the media options, creates jobs with an
idempotency key per press, polls them, remembers their ids in session storage and renews expiring
URLs. `ProcessTimeline` draws each stage's `StageMedia` after the stage card, so an illustration
never sits among the evidence. Files reach the browser through `lib/download.ts`; the CSP's
`connect-src`, `img-src` and `media-src` name the media bucket's host.

## Checks

| Workflow | Runs |
|---|---|
| Backend checks | ruff, DB-free pytest, hygiene tool tests, hygiene check, offline migration render; then migrations, seeds and DB tests against PostGIS with pgvector |
| Frontend checks | typecheck, lint, unit specs, smoke specs |
| Craft data | master-list sha1, lint and tests of `etl/crafts`; weekly regeneration |
| Geo ETL | `etl/geo` tests and the district statistics build |
| Deploy backend | after Backend checks succeed on a push to `main` of `cxacraftecosystem-ui/KalaVigyan` |
