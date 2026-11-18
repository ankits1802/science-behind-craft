# Architecture

How KalaVigyan is put together today: the pieces, the layers inside the backend, the direction
imports may point, and the contracts between lanes. The target design is `docs/PLAN.md` (section
0 overrides the rest); this page describes what exists and is updated in the same change that
makes it untrue.

Last reviewed: 2026-11-18.

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
| `tools/` | Developer tooling: `hygiene_check.py` and the `hygiene` package; `curation/` (fetch, verify, check and schema for curated dossiers, decision 0051); their tests |
| `docs/` | Plan, architecture, catalogue, contracts, decisions, debt, progress, runbook, data sources |
| `.claude/skills/` | Practice skills (engineering, backend, frontend), naming, frontend design system |

## Backend layers

```
entry points   main.py   api/ (router.py, routes/<area>.py)   scripts/ (seeds, sync, coverage job)
                 |
voice          voice/       voice sessions, the custom-LLM turn, relay turns, the encrypted
                            transcript, daily upkeep, agent provisioning (decision 0017; the
                            call is switched off, decision 0035); Listen: narration of finished
                            explainers with word timings, cached in the media bucket (0035);
                            film mode's score: scenes, fixed prompts, content-addressed clips
                            and a manifest per explainer and language (0058)
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
curation       curation/    curated craft dossiers: the model, the offline rules, the check
                            file and the index, read by tools/curation and the importer;
                            imports research/, models/ and data/ only (decision 0051)
                 |
contracts      research/    research and answering types, protocols, post-check rules; the
                            explainer document, blocks, stored pieces and depth by role
                            (decision 0030); dataset rows, rivers, the calendar words,
                            reaction rules and the expert panel (decision 0042)
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
`services/` imports `curation/` so the dossier import reads the checker's own model and rules
(decision 0053); the craft page's response models live in `research/craft_page.py` so
`services/craft_page` can build them.

## API surface

All routes are under `/api` except `/health` and `/health/ready`. Route groups (`api/routes/`):
`auth`, `password_change` (change-password and the first-password nonce, decision 0028), `two_factor`, `me`, `access`, `users`, `crafts`, `film` (film mode's music and sound score, decision 0058), `knowledge`, `lessons` (lesson packs and their files, decision 0067), `explainer_exports` (an explainer version's PDF and citations, decision 0067), `listen` (an explainer read aloud, decision 0035), `map_districts` (ask the map, decision 0065), `map_layers`, `media`, `rivers` (a basin's river lines as TopoJSON, decision 0043), `secrets`,
`settings`, `terms` (a glossary term's cited summary, decision 0034), `usage`, `voice` (404 throughout while `VOICE_CALL_ENABLED` is off, decision 0035). Shapes, headers and error forms are in `docs/contracts/backend.md`; the web client's
side is `docs/contracts/frontend.md`. `GET /api/crafts/{slug}/page` (in `crafts`) answers the whole craft page from stored rows: the
curated overview and facts and All evidence (`docs/contracts/craft-page.md`, decision 0053);
`GET /api/crafts/{slug}/process` (in `crafts`) answers a craft's
stages, materials, conditions and reactions (`docs/contracts/science.md`);
`GET /api/crafts/{slug}/region` its places and their environment, and `GET /api/map/layers` and
`/api/map/layers/{layer}` (in `map_layers`) the district choropleths, all from the stored
district statistics (`docs/contracts/region.md`). `GET /api/map/districts/{districtLgd}` (in
`map_districts`, ask the map, decision 0065) answers a tapped district's located crafts, its
stored region story and place prose pieces and its land values, with no model call
(`docs/contracts/learning.md`).

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
   experts (each seat speaking to the field is named with the kinds of source it reads, and those
   kinds take every other early read; decision 0046), searches stored claims (every craft's, for any craft) and, for what they do not cover
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
7. A follow-up (`buildsOn`, decision 0063) is the same flow with a layout
   (`services/follow_ups`): the explainer's crafts, depth and language are kept, a field it has
   deepens that section (blocks numbered after its own, already-cited sentences and shown kinds
   left out, never reused from or stored as pieces) and any other field is added after its
   sections; `builds_on` follows `understood`. `services/version_merge` merges the follow-up into
   the latest version, `version_problems` must hold, and the merged document is kept on the
   follow-up's answer with its `VersionMark` (`Answer.explainerId`, `explainerVersion`); `version`
   precedes `done`. Earlier versions are never rewritten.

## How a saved explainer gets better (decision 0063)

1. A reader saves an explainer (`SavedItem` with its first answer). Every night the last module of
   the Coverage enrichment job, `app.scripts.recheck_saved`, counts per saved field the craft's
   fact-level claims created or raised since the last check that the latest version does not cite,
   and writes one `ANSWER_IMPROVED` note when any field has news; no model is called.
2. The note's Update asks a follow-up for the fields with news, as the reader and under the
   reader's caps. On Mondays the **Alert digest** workflow mails opted-in readers their unread
   notes through SES, only while `ALERT_DIGEST_ENABLED` is set.

## How a lesson pack and its files are made (decision 0067)

1. A Professor or above chooses finished sections of one version of their explainer. The server
   builds the pack from the stored version with no model: the sections' cited fact sentences whose
   claims are still shown, five a slide, each section's first open picture, the quiz by the one
   `quiz_block`, the reading list and sources, and stores it as a `LessonPack` row.
2. A file (HTML deck, PPTX or PDF, or an explainer version's PDF) is asked for by format. The
   route reads the pack or version and its sources' access days, releases its connection, and
   looks for `exports/<builder>/<sha256>/<name>` in the private bucket; only when it is missing
   are the open pictures read from Commons or Openverse, then the APA references written by
   citeproc-py with the vendored APA 7 style and the file rendered, both in one worker thread
   (reveal.js, python-pptx, fpdf2 with HarfBuzz and the Noto fonts), and stored. The export
   libraries are imported on the first file a process makes, never at start-up, and a version is
   read with its hidden generated explainers left out (decision 0070). The answer is a five-minute
   signed link; citation files are answered directly.

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

## How a film gets its score (decision 0058)

1. `GET /api/answers/{answerId}/film-score?language=` (`api/routes/film.py`) checks `VOICE` and
   the 10-ask limit (Master Admin unlimited) and reads the reader's own explainer with hidden
   simulations marked, in one short session (`voice/film_store.py`).
2. `voice/film_scenes.py` makes the scenes (drawn blocks in reading order, timed by their
   narration estimate or `FILM_SCENE_SECONDS`), their hash, the bed length and the cues the
   fixed table of `voice/score_prompts.py` names. A manifest at
   `media/score/<answerId>/<language>/score.json` whose hash matches is served at once.
3. Otherwise `voice/film_score.py` looks up each clip by its content address
   (`media/score/<cacheId>/clip.json`) and makes only the missing ones, three at a time, through
   `providers/media_router.MediaRouter` (`MUSIC`, `SOUND_EFFECT`: reserve, ElevenLabs through
   `providers/elevenlabs_media.py`, settle), checks each MP3's length, stores clip and record,
   then the manifest. Any failure stores no manifest. The work runs shielded, so a reader who
   leaves still fills the cache.
4. The answer is `FilmScore`: one-hour presigned links to the bed and cues, labelled with the
   models that made them.

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
3. Later blocks (decision 0042): `services/block_builders.BLOCK_BUILDERS` maps a block kind to the
   fields it may be added to, listed in the order a section reads its blocks (`PIECE_BLOCK_ORDER`).
   A researched section with a checked prose or ladder block starts its field's builders together
   with its pictures; their blocks go out after the section's own and before the pictures, each
   builder bounded by its wait, and a failing builder adds nothing. A reused section starts only
   the builders of kinds that are never stored as pieces (map layers, molecules) over its placed
   pieces (decision 0050). Builders implement `services/builder_interface`; only kinds already
   built start, and every phase B kind is built. The matter
   builders (`services/matter_builders`, decision 0045) read the craft's matter in one short
   session (`services/craft_matter`), then add the reaction player (the Process tab's reactions,
   re-checked against the rows), material cards (stored rows and glossary terms, one plan-model
   call sorting stored claims into facts and handling) and one molecule whose 3D conformer the
   PubChem adapter fetched once into the private bucket (`services/molecule_conformers`), served
   to signed-in readers by `GET /api/molecules/{pubchemCid}/conformer`, which releases its
   database connection before the bucket and PubChem (decision 0050). The place builders
   (`services/place_builders`, decision 0044) read a craft's cited districts in one short session
   (`services/place_offers`): a geography section's region story offers the rivers crossing them
   (by stream order and discharge, traced through the stored network), the districts and the
   layers with values there, and one plan-model call chooses a river, the stored claims for its
   steps and their order by ref, a step keeping its district only when its sentence names it; it
   is kept as a cross-craft piece by basin or districts and reused with its geography section
   (`services/region_pieces`). Geology and climate sections get the
   registry layer their sentences name, built as the layer route answers it. Climate sections also
   get a seasons strip, the trends of the craft's districts with the section's cited claims on
   what they mean (`services/climate_risk`, decision 0065), and materials sections a supply map (`services/season_supply_builders`,
   decision 0047): the craft's stages and the section's claims placed only on the months or season
   their own text names, a season given months only by a cited quote that states them, the CHIRPS
   rainfall of the first craft district with twelve normals; supply links whose material and
   origin words one plan-model call chose and the sentence states, placed only with Wikidata
   coordinates the Wikidata adapter reads. The expert panel
   (`services/expert_views`, decision 0046) makes one `COMPOSE` call per section for the seats
   speaking to its field (`research/expert_panel.speaking_seats`), over the stored facts the
   section's checked sentences rest on; a take passes the prose checks (which also refuse a month,
   season, state or district no source states, `services/stated_names`) or is not shown, "Experts
   differ" is kept only for two stored facts about one concept from two sources, and the call
   spends only from the answer's headroom (`providers/budget.AnswerHeadroom`).
   Sections of the mechanism fields also get a generated explainer (`services/simulation_builder`,
   decision 0055; built since the review, decision 0061): every figure
   the section's cited quotes state is offered with its own words; a stored explainer whose claims
   the section offers is placed first with no model call; otherwise one `COMPOSE` call from the
   headroom chooses values and writes an HTML fragment that must pass the value, static
   (`research/sandbox`) and block checks, with one redraft; it is kept as a cross-craft piece by
   concept and claim set from any section (also an any-craft answer and a deepened follow-up), and
   a professor's hide (`PUT /api/answers/{answerId}/simulations/{blockId}/hidden`) keeps it from
   being served or built again; every route that reads a stored explainer back marks it hidden.
   Process, chemistry and water sections also get a what-if (`services/what_if_builder`, decision
   0056; built since decision 0061): a stage's materials that a
   stored contrast relation or a stored text ("madder or al root") relates as alternatives, once a
   section sentence names one, each offered the relation claims on its concept (a hypothesis
   marked and later labelled), its own fact claims and the claims of reactions of its compound;
   after the process rows and one short read of those claims, one plan-model call chooses the
   input, its words and each option's outcomes by ref; an option without evidence is shown
   unknown, and the block is re-checked against the process rows when built and when reused.
   Materials sections also get a powers-of-ten zoom and history sections a timeline map
   (`services/journey_builders`, decision 0057), registered and waiting for their renderers to
   join the built kinds: the zoom reads the craft's mapped districts, the boundary row, the craft's
   claims naming a district and the open pictures already kept for the offered claims in one short
   session, searches Commons and Openverse only for levels still missing, keeps what it shows as
   `MediaRef` rows and shows the molecule only with a kept conformer, every level captioned by a
   distinct stored claim and none faked; the timeline offers the section's facts with the spans of
   years their own texts state, one plan-model call picks points, routes and years by ref, and
   places are pinned only with Wikidata coordinates through the supply origins' rule.
   The web client draws each block kind through one renderer
   (`components/answer/blockRenderers.ts`); a kind without one is not drawn.

## Data

Tables follow DR's Prisma naming (quoted PascalCase tables, camelCase columns) so the portals
stay mergeable; the full list is `backend/app/models/` and `backend/migrations/versions/`.
Craft data is vendored from the designer portal (`docs/contracts/crafts.md`); district and
environment data come from open datasets (`docs/contracts/geo.md`, `docs/DATA_SOURCES.md`).
Seeds (`app/scripts/seed_crafts`, `seed_claims`, `seed_districts`) run on every deploy and are
idempotent; right after them `app/scripts/import_curation` imports every checked dossier of
`backend/app/data/curation/` into the same tables, withdraws the seed's edge sentences and
supersedes claims a new dossier version drops (decision 0053). `seed_claims` also runs the science seed (`app/data/science_seed.json`: constants,
materials, compounds, reactions, readings; decision 0015); `app/scripts/link_compounds` looks
the seeded compounds up in PubChem, nightly in the Coverage enrichment run (decision 0045). After them, `app/scripts/sync_portal_crafts` adds every craft the two portals hold
beyond the master list, with their aliases, spellings and merge redirects, through the signed
peer route of `docs/contracts/portal-craft-feed.md`; it also runs daily (decision 0003).
Then `app/scripts/embed_craft_descriptors` fills missing craft name-and-alias vectors for the
resolver; the daily Coverage enrichment run fills them first too (decision 0016). The region
routes read the geo ETL's per-district statistics and compute state aggregates in Postgres per
request; nothing environmental is queried live (decision 0016). River lines (decision 0043) are
HydroRIVERS reaches the geo ETL loads into `RiverReach` and `RiverBasin` and writes as one
TopoJSON per basin to the media bucket (`riverlines` in the Geo ETL run); `services/river_store`
traces a river through a reach (`geo/river_trace`: the largest upstream branch to the source,
`NEXT_DOWN` to the mouth) and orders the districts it crosses with PostGIS, and
`GET /api/rivers/{mainRiv}` serves the basin's file. A district's CHIRPS monthly normals reach a
`seasons` block through `services/monthly_rain`. The CHIRPS and GHCN CAMS layers write each
district's yearly series from 1981 with its normal and its Theil-Sen and Mann-Kendall trend
(`etl/geo/geo_etl/trend.py`); `services/climate_store` reads a craft's district trends through
`geo/climate` for a `climate_risk` block (decision 0065).

## Frontend

Next.js App Router. Signed-in screens are under `app/(protected)/` (ask, crafts, map, saved,
lessons, compare, settings, admin); `app/api/` holds route handlers that proxy auth and session calls; `lib/api.ts` is the
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
`lib/explainerView.ts`, `lib/termSummary.ts` and `lib/listen.ts`. The place kinds (decision 0048)
are `components/answer/place/`: the region story (a river from the served basin TopoJSON flowing
across the real district polygons, `lib/riverTopology.ts`, `lib/riverGeometry.ts`,
`lib/regionStory.ts`), the map layer on `IndiaMap`, the seasons strip (`lib/seasonsView.ts`) and
the supply list with its pin map (`lib/supplyView.ts`); map code reaches the browser only when a
map block is drawn (`components/answer/lazyBlock.tsx`). The matter kinds (decision 0049) are
`components/answer/matter/`: the reaction player (`lib/reactionPlayer.ts`), material cards, and
3D molecules drawn by 3Dmol.js through its one adapter (`lib/moleculeViewer.ts`, imported only
when a molecule nears the viewport) from the conformer route (`lib/conformer.ts`); a section's
expert views are one panel with its "Experts differ" cards (`components/answer/experts/`,
`lib/expertPanel.ts`). The phase C kinds (generated explainers in a sandboxed `srcdoc` frame, the
what-if lab, the zoom story, the timeline map) and film mode with its score have their client
shapes in `lib/explainerPlay.ts` and `lib/filmScore.ts` (decision 0054); the score's route is
built (decision 0058). The zoom story and the timeline map are `components/answer/journey/`,
loaded on demand (`lib/zoomView.ts`, `lib/timelineView.ts`, decision 0060). Film mode is
`components/answer/film/`, loaded only when a film starts: one clock over the drawn blocks
(`lib/filmScenes.ts`), the Listen script and audio for narration and captions, each block's own
animation driven through `components/answer/FilmScene.tsx`, and the optional score mixed by
`lib/filmSound.ts`.
The phase D kinds (the cloze quiz, compare, the concept graph, local measures, market and GI,
climate and risk) have their client shapes in `lib/explainerLearning.ts` and
`lib/explainerInsight.ts`, and the learning routes (versions and follow-ups, saved explainers
and notifications, lesson packs and citation export, the shared-science explorer, ask the map)
theirs in `lib/learningContract.ts`, `lib/lessonContract.ts`, `lib/sharedScienceContract.ts`,
`lib/quizContract.ts`, `lib/compareContract.ts` and `lib/districtCraftsContract.ts` (decision
0062). On the server the quiz, compare and the concept graph follow fixed
rules in `research/quiz.py`, `research/craft_compare.py` and `research/shared_science.py`, read
their rows through `services/shared_concepts.py` and `services/craft_compare.py`, and reach answers
through `services/learning_builders.py` (decision 0064). Local measures and market and GI
follow fixed rules too: stated quantities, regional factors and prices in
`research/stated_quantities.py` and `research/stated_prices.py` over the one Pint registry
(`research/unit_registry.py`, shared with the science engine), GI registry fields in
`research/gi_registry.py`, read through `services/measure_store.py` and
`services/market_store.py` and built by `services/measure_builder.py` and
`services/market_builder.py` (decision 0066). The six kinds are drawn
by `components/answer/learning/` (the quiz, compare and the concept graph) and
`components/answer/insight/` (measures, market and GI, climate trends), with their rules in
`lib/quizView.ts`, `lib/compareView.ts`, `lib/conceptGraph.ts`, `lib/insightView.ts` and
`lib/climateView.ts` (decision 0068). The screens around the learning routes (decision 0069) are
`components/learn/` and `components/map/DistrictPanel.tsx` over `lib/learningApi.ts` and
`lib/lessonApi.ts`: follow-ups stream on top of the shown explainer through
`lib/explainerVersions.reduceAnswerEvent` (which wraps `reduceExplainer`), stored versions open at
`/ask?explainer=` (`components/ask/useExplainerLearning.ts`), and `/saved`, `/lessons`,
`/compare` and the district panel on `/map` read the rest; citation files are saved under the
server's file name (`lib/download.downloadApiFile`), lesson files and the report PDF through their
signed links (decision 0067). The notes behind `/saved` and the nav's unread badge are held for
the signed-in account only (`lib/notesStore.ts`, decision 0070).

The craft page (decision 0071) reads `GET /crafts/{slug}/page` and the region route, each parsed
by its contract shape and cross-checked at the boundary (`lib/craftPageContract.ts`,
`lib/craftRegion.ts` with `lib/regionView.ts`); its pure rules are `lib/craftPageView.ts` and
`lib/craftPlaces.ts`, and `components/craft/CraftReference.tsx` draws the tabs (Overview,
Process, Region, Shared science when `GET /crafts/{slug}/shared-science` names a shared concept
(decision 0070), Sources, and All evidence for researchers and above). One claim index
(`components/craft/CraftClaims.tsx`) and one citation numbering per page reach every chip through
`components/answer/CitationContext.tsx`; sentences and terms are the explainer's
(`ExplainerSentence`, `TermSheet`). `/map` draws craft places as pins and the environment
layers as district choropleths on `public/boundaries/district-shapes.json`, clipped to the
DataMeet outline, with no tile basemap (`components/map/`, decision 0019).

Voice (decision 0020) is a dock (`components/voice/`) over one controller, `lib/voiceCall.ts`,
which runs the consent, session, timer and client-tool checks and takes its transports
(`lib/voiceRelay.ts`, `lib/voiceAgent.ts`) and adapters as arguments: the voice routes
(`lib/voiceSession.ts`), ElevenLabs (`lib/elevenLabsAgent.ts`, the only module that loads the
SDK, on demand), and the microphone and speech player (`lib/voiceDevice.ts`). The CSP's
`connect-src` is `next.config.ts`.

Generated media (decision 0021) is one store per page, `lib/craftMedia.ts`, created by
`components/craft/useStageMedia.tsx`: it reads the media options, creates jobs with an
idempotency key per press, polls them, remembers their ids in session storage and renews expiring
URLs. Since decision 0071 no screen mounts it (the craft page offers no generator). Files reach the browser through `lib/download.ts`; the CSP's
`connect-src`, `img-src` and `media-src` name the media bucket's host. Pictures from the web are
drawn with no referrer (decision 0034); `img-src` adds `https:` on every page, because a
client-side move to `/ask` keeps the first page's policy (decision 0039); plain http stays refused.
The CSP's `frame-src` names only Google's sign-in frames: a generated explainer is a
`sandbox="allow-scripts"` `srcdoc` frame under its own policy, sized by a height message the page
bounds (`components/answer/play/`, `lib/sandboxFrame.ts`, decision 0059). The frame's first
script is the client's own guard: it removes the peer connection constructors and keeps the frame
from opening nested windows, because Chromium ignores the policy's `webrtc 'block'` (decision 0061).

## Checks

| Workflow | Runs |
|---|---|
| Backend checks | ruff, DB-free pytest, tools tests (hygiene, curation), hygiene check, the curation check of every dossier and the index (`tools/curation/check.py --check-index`, no network), offline migration render; then migrations, seeds and DB tests against PostGIS with pgvector, then the curated dossier import (decision 0053) |
| Frontend checks | typecheck, lint, unit specs, smoke specs |
| Hygiene | the hygiene check over the whole repository on every push to `main` and every pull request, whatever the paths, since Backend checks runs only for backend paths |
| Craft data | master-list sha1, lint and tests of `etl/crafts`; weekly regeneration |
| Geo ETL | `etl/geo` tests and the district statistics build |
| Deploy backend | after Backend checks succeed on a push to `main` of `cxacraftecosystem-ui/KalaVigyan` |
| E2E production | on dispatch only: Playwright against the deployed site at 1440, 834 and 390 px wide, every screen signed in as the E2E Researcher, and with `questions=true` three known-answer questions at Detailed depth: the mordant in English and Hindi, and Kachchh's water, which needs a region story with a traced river once `rivers_loaded` is set (decisions 0029 and 0050) |
