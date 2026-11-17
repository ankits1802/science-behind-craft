# Architecture

How KalaVigyan is put together today: the pieces, the layers inside the backend, the direction
imports may point, and the contracts between lanes. The target design is `docs/PLAN.md` (section
0 overrides the rest); this page describes what exists and is updated in the same change that
makes it untrue.

Last reviewed: 2026-11-17.

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
                            transcript, daily upkeep, agent provisioning (decision 0017; the
                            call is switched off, decision 0035); Listen: narration of finished
                            explainers with word timings, cached in the media bucket (0035)
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
                            copies and cited DOIs into an evidence pack (decision 0009); the
                            understanding step: craft choice, fields, seats (decision 0031)
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
                            sources/web/: SearXNG, Brave, the fallback; sources/images/:
                            Openverse and the image sources), the fetcher client
                 |
fetcher        fetcher/     the separate kv-fetcher process: address-pinned https fetch,
                            robots.txt, caps, trafilatura and pypdf extraction (no DB, no AWS)
                 |
contracts      research/    research and answering types, protocols, post-check rules; the
                            explainer document, blocks, stored pieces and depth by role
                            (decision 0030)
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
`auth`, `password_change` (change-password and the first-password nonce, decision 0028), `two_factor`, `me`, `access`, `users`, `crafts`, `knowledge`, `listen` (an explainer read aloud, decision 0035), `map_layers`, `media`, `secrets`,
`settings`, `terms` (a glossary term's cited summary, decision 0034), `usage`, `voice` (404 throughout while `VOICE_CALL_ENABLED` is off, decision 0035). Shapes, headers and error forms are in `docs/contracts/backend.md`; the web client's
side is `docs/contracts/frontend.md`. `GET /api/crafts/{slug}/process` (in `crafts`) answers a craft's
stages, materials, conditions and reactions (`docs/contracts/science.md`);
`GET /api/crafts/{slug}/region` its places and their environment, and `GET /api/map/layers` and
`/api/map/layers/{layer}` (in `map_layers`) the district choropleths, all from the stored
district statistics (`docs/contracts/region.md`).

## How a question is answered today

1. `POST /api/answers/stream` (`api/routes/knowledge.py`) takes the reader's depth (default the
   role's: Student Basic, Researcher and Professor Detailed, Admin and Master Admin Expert; any
   known role may choose any depth) and the per-user ask rate limit (none for a Master Admin),
   builds the answer pipeline with the asker's principal and one per-answer spend record (so the
   depth's per-answer cap, the per-role daily cap and the monthly ceiling apply, none of them to a
   Master Admin) and
   streams `services/answering.answer_question` through `research/stream.event_stream`, which
   sends each event as it is produced and a heartbeat after 60 s of silence (decisions 0012,
   0031).
2. The question is understood (`planner/understanding.ModelUnderstander`, decision 0031): the
   craft resolver (`services/craft_resolver.DatabaseCraftResolver`, decision 0004: the slug when
   the reader picked one, otherwise exact, fuzzy, family and region matching over every craft's
   names, aliases and spellings, and pgvector neighbours when that leaves no clear winner), then
   one `PLAN` call for the choice among ambiguous candidates, crafts named but not matched, the
   fields the question touches and the experts to seat. A craft is never required: the best match
   proceeds and the others are offered, nothing found is any craft, and a resolver failure leaves
   the choice to the model's reply (decision 0038). `understood` is the first event; past the degrade mark Expert runs as Detailed for every role but Master Admin.
3. When that call is refused for spend, the chosen craft's verified and reviewed claims are
   sent as explainer sections, one `prose` block per concept heading (`knowledge_view.claims_for`,
   `services/stored_explainer`); no model is called for a Latin-script question.
4. Otherwise the answer is an explainer of sections, one per field the question touches (at most
   the depth's number). First the stored knowledge pieces (decision 0033, `services/piece_store`):
   for each field whose topic (`research/piece_topics`: the glossary terms the question names, else
   the craft's districts for place fields, else the craft) holds a set of pieces that is deep
   enough, not stale or superseded, and whose claims are all still visible as cited (and whose
   ladder still matches the process rows), that section streams first, marked "From earlier
   research" with its date, and is not researched; `fresh` (Research again) and any-craft answers
   reuse nothing. The other sections run in parallel (`services/answer_sections`, decision 0032). Each section
   researches its own field within its share of the depth's budget (Basic and Detailed `HYBRID`,
   Expert `DEEP`): the planner (decision 0009) plans facets and queries for that field and its
   experts, searches stored claims (every craft's, for any craft) and, for what they do not cover
   (every facet in `DEEP`), scholarly, reference and web sources, and reads the best documents,
   streaming each source to the trail as it is found and read. The composer (decision 0010) writes
   the section's cited sentences and chooses process stages (Claude Sonnet first, Gemini next); what
   was found is kept (`store_live_research`, decision 0011, run as shielded work that finishes
   even when the learner leaves); the server then builds the section's blocks from stored rows and
   stored citations (a process ladder from the science tables, `science/ladder`; a prose block),
   checks each and drops one that fails, marks the glossary terms in each English sentence, and
   sends each block with its sources first, then the section's pictures (decision 0039). A section
   whose stored claims compose nothing researches live once more. `section_started`,
   `section_state`, `block` and `section_done` mark each section; `status` the overall step.
5. Another answer language (decision 0023): each block is still composed and checked in
   English; `services/answer_translation.translated_block` then translates it in one `TRANSLATE`
   call, keeps a translation only when its numbers, formulas, units and script check out (else the
   sentence stays English), copies the citations, and caches claim translations in
   `ClaimTranslation`. The planner adds native-language Wikipedia and Wikidata queries and
   searches stored claims with an English rendering of the question.
6. Nothing cited: each section says what it searched and `not_enough_evidence` sums it up; any
   failure of the whole answer is one `error`; `done` always ends the stream. The explainer
   document is kept in `Answer.payload.explainer` and the plans in `Answer.plan`.

## How stored pieces stay current (decision 0033)

1. When an answer finishes, every English block of each researched section that cites claims and
   sources is kept as a `KnowledgePiece` (its facet, topic, depth, claims, sources, content hash,
   vector), superseding the earlier pieces of that topic and kind at the same or a lower depth.
   Stage concepts a `PROCESS` section cites stay concepts: no answer writes process rows, since
   no source states their order (decision 0038).
2. A trigger on `Claim` (`kv_stale_resting_pieces`) marks every piece resting on a claim stale when
   it is retracted, hidden, deleted, or changes level or text; the next answer for that topic
   researches the section again and its new pieces supersede the stale ones.
3. Every night the Coverage enrichment run calls `app.scripts.rebuild_pieces` before the coverage
   job: the stale pieces of the 10 most-asked crafts are answered again for their facet and depth,
   with fresh research, within the same day's budget.

## How an explainer is read aloud (Listen, decision 0035)

1. `GET /api/answers/{answerId}/listen` (`api/routes/listen.py`) checks `VOICE` and the 30-press
   limit, and reads the reader's own explainer from `Answer.payload.explainer`
   (`voice/listen_store.py`).
2. `voice/narration.py` picks each block's cited sentences, in reading order and each in its own
   language, and the cache id per block (piece content hash, model, voice, language).
   `voice/narration_cache.py` reads each block's manifest from `media/narration/<cacheId>/`.
3. For the misses only, `voice/listen.py` holds the estimated `VOICE_SECONDS` under the reader's
   `User` row lock (429 when too few are left), asks `ElevenLabs.narration`
   (`/with-timestamps`, `eleven_v4`) for each part of at most 2,000 characters, stores the audio
   and then the manifest, and settles the hold to the audio's seconds.
4. The answer is one track per part: a one-hour presigned link and the words with their times,
   which the explainer UI highlights (`frontend/lib/listen.ts`).

## How a voice call is answered

The call is switched off (`VOICE_CALL_ENABLED`, default false; decision 0035): every route below
answers 404 and no voice button is drawn. The steps hold when the setting is true.

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

## How pictures and terms are found

1. Pictures (decision 0034): `services/section_images.SectionImages` takes a section's block id,
   its craft and the claims its other blocks cite, searches Wikimedia Commons, Openverse (open
   licences only) and SearXNG images (`sources/images/registry.image_sources`, held by
   `LiveSourcesStore.images()`), keeps the pictures whose words meet a claim's
   (`research/image_relevance`), stores each once as a `MediaRef` with its claims
   (`services/media_ref_store`) and answers an `images` block: inline under an open licence with
   its author, else a credited link card whose thumbnail the page's own site serves. The answer
   stream calls it for every section with blocks, researched or reused, after those blocks are
   built (`services/section_enrichment`, decision 0039): each service has 6 s, the step 8 s, and a
   failure or timeout sends no `images` block and leaves the section ready.
2. Terms: `seed_claims` also seeds the `Term` glossary (`services/term_glossary.seed_terms`) from
   craft names, aliases and matched Wikidata labels, the seed's local names with what they mean,
   and its compounds. `research/term_marking.TermMarker` marks term spans in sentences against an
   answer's glossary (`glossary_entries`): every English sentence of a section's blocks, before
   translation; a translated sentence keeps the spans whose text it still shows (decision 0039). `GET /api/terms/{key}?language=` (`api/routes/terms.py`)
   answers `services/term_summaries.TermLookup.summary`: the cached summary while its claims are
   visible, else the defining stored claims, the Wikipedia lead or one web search with a
   `SUMMARISE` call, kept as quoted claims and cached per term and language.

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

`/ask` (decision 0036) is one container hook, `components/ask/useAskScreen.ts`, over pure rules:
the craft pick and what was detected (`lib/askCraft.ts`), the depth from `/answers/config`
(`lib/askConfig.ts`, `lib/askDepth.ts`), the request and the re-ask rule (`lib/askRequest.ts`), and
dictation through the browser's Web Speech API (`lib/dictation.ts`, the one adapter; no speech
reaches the server). The answer is the explainer (decision 0037): `lib/explainerStream.streamExplainer`
parses each frame with the contract's shapes, `lib/explainerState.reduceExplainer` keeps the
state (`components/ask/useAnswerStream.ts` drives it), and `components/answer/ExplainerView.tsx`
draws the understood line, the research trail, the section bar and the sections, one component
per built block kind (`ProseBlockView`, `ProcessLadder`, `ImageStrip`), over two contexts: the
citation numbering (`CitationContext`) and the reading (`ExplainerReading`: language, original
text, hidden terms, the term sheet and the word Listen is reading). Pure rules are in
`lib/explainerView.ts`, `lib/termSummary.ts` and `lib/listen.ts`.

The craft page reads the profile, then the process and region routes, each parsed by its
contract shape and cross-checked at the boundary (`lib/craftProfile.ts`, `lib/processView.ts`,
`lib/regionView.ts`); one citation numbering per page reaches every chip through
`components/answer/CitationContext.tsx` (shared with the explainer). `/map` draws craft places as pins and the environment
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
`connect-src`, `img-src` and `media-src` name the media bucket's host. Pictures from the web are
drawn with no referrer (decision 0034); `img-src` adds `https:` on every page, because a
client-side move to `/ask` keeps the first page's policy (decision 0039); plain http stays refused.

## Checks

| Workflow | Runs |
|---|---|
| Backend checks | ruff, DB-free pytest, hygiene tool tests, hygiene check, offline migration render; then migrations, seeds and DB tests against PostGIS with pgvector |
| Frontend checks | typecheck, lint, unit specs, smoke specs |
| Craft data | master-list sha1, lint and tests of `etl/crafts`; weekly regeneration |
| Geo ETL | `etl/geo` tests and the district statistics build |
| Deploy backend | after Backend checks succeed on a push to `main` of `cxacraftecosystem-ui/KalaVigyan` |
| E2E production | on dispatch only: Playwright against the deployed site at 1440, 834 and 390 px wide, every screen signed in as the E2E Researcher, and with `questions=true` two known-answer questions in Hybrid (decision 0029) |
