# Progress

Where work stands and what comes next. Update it in the same change that finishes or starts a
piece of work. The plan is `docs/PLAN.md` (section 0 overrides the rest); the build order is its
section 17.

Last updated: 2026-11-17.

## Done

- **Foundation (PLAN section 17, day 1).** Repository layout; FastAPI backend with the
  SQLAlchemy schema and the first migration; auth (password, Google with nonce, TOTP two-step),
  roles and capabilities, access roster, Manage users, consent and privacy notice; Settings hub
  (managed keys, model catalogue, per-task routing) and usage pages; AI router with ceilings and
  budgets; craft seed of the 455 master crafts with codes, spellings and aliases; seed claims;
  states and districts; the India map; the web client for sign-in, crafts, map, ask (verified
  answers from stored claims), settings and admin.
- **Data.** Craft data pipeline (`etl/crafts`: aliases, Wikidata links, seed claims) and the geo
  ETL (`etl/geo`: per-district soil, climate, land cover, forest, elevation, water, geology from
  open datasets).
- **Infrastructure.** EC2 box, CloudFront, private S3 bucket, Supabase project with RLS lockdown,
  blue/green deploy from `cxacraftecosystem-ui/KalaVigyan` `main` only (`docs/RUNBOOK.md`).
- **Practices.** The engineering, backend and frontend practice skills bind the repository, with
  KalaVigyan bindings; architecture, catalogue, decision log and debt register written; the
  hygiene check (import direction, encoding, no Python comments, ratcheted budgets) runs in
  Backend checks (decision 0001).
- **Research and answering contracts (decision 0002).** `backend/app/research/` holds the typed
  models, protocols and rules every later lane builds against: craft resolution, evidence items
  and the source-adapter protocol, the fetcher, retrieval plans and mode limits, composer output
  and its per-sentence post-checks, live-research write-back, and the answer stream with its
  60-second heartbeat (`docs/contracts/research.md`). `core/errors.py` is the shared error
  hierarchy (`ProviderError` and `RouterError` join it). The stored-answer route now validates
  every frame against the stream contract; `shared/answer-stream.golden.sse` is checked by the
  backend and frontend tests. No adapter, planner, composer or writer exists yet.

- **Craft sync from both portals (decision 0003).** `app/scripts/sync_portal_crafts` reads a
  signed craft feed from the designer and documentation portals, upserts crafts by slug with
  stable ids, keeps the master list as it is, records each craft's source portal, and adds
  portal names as `DR_SYNC` / `FR_SYNC` aliases and merges as redirects. It runs after the seeds
  on deploy and daily (`.github/workflows/craft-sync.yml`). The portals still have to ship the
  route (`docs/contracts/portal-craft-feed.md`); until then each run reports `not_found`.

- **Craft resolver (decision 0004).** The answer stream resolves the craft with
  `services/craft_resolver.DatabaseCraftResolver`: slugs, names, aliases, shared spellings and
  merge redirects matched exactly after Indic transliteration, rapidfuzz typos and family
  words, region hints from craft states and locations, and pgvector neighbours on craft
  name-and-alias embeddings when that leaves no clear winner; at most five ranked candidates
  with reasons. `AMBIGUOUS` now allows one candidate. Embeddings are filled by
  `app/scripts/embed_craft_descriptors.py` after the seeds on every release and first in the
  daily Coverage enrichment run (decision 0016).

- **Scholarly source adapters (decision 0005).** `app/sources/`: paced, cached HTTP with
  Retry-After handling and failure kinds; one `SourceAdapter` each for OpenAlex, Crossref,
  Semantic Scholar, CORE, Europe PMC, arXiv and DOAJ, dormant Elsevier and Springer Nature
  adapters, and an Unpaywall open-access locator (its title search is retired). Built by
  `sources.scholarly.registry.scholarly_sources` from the managed keys; tested on recorded
  responses. Called by the answering service and the coverage job.

- **Reference source adapters (decision 0006).** `app/sources/reference/`: Wikipedia (English
  and 25 Indian-language wikis, full article text, live licence and revision), Wikidata
  (search with label fallback, statements with labels and units through SPARQL, PubChem and
  CAS ids linked), PubChem (names and formulas, computed properties, GHS hazards attributed to
  their reporting source) and Wikimedia Commons file metadata with licence and attribution.
  Built by `sources.reference.registry.reference_sources`; tested on recorded responses.

- **Web search and the fetcher sandbox** (decision 0007): SearXNG with Brave fallback
  (`sources/web/`, one `WebSearch` the planner calls) and the separate `kv-fetcher` process
  (`app/fetcher/`): https only, address pinning with TLS checked for the named host, redirects
  and robots.txt re-checked, size and time caps, trafilatura and pypdf extraction, retrieved
  text cleaned and marked untrusted (`research/untrusted.py`). Tested with fixtures; not yet
  run on the box.

- **Stored-knowledge retrieval** (decision 0008): `retrieval/` searches a craft's claims (T1)
  and corpus chunks (T2) with Postgres full text and an exact pgvector scan fused by reciprocal
  rank fusion (k 60), scoped in SQL by craft, sub-category, mode levels, facets, sensitivity and
  chunk ACL; chunking and embedding fill for stored sources and claims
  (`python -m app.scripts.embed_knowledge`). Contract in `docs/contracts/research.md`. DB
  tests run on GitHub Actions.

- **Planner and tiered live research** (decision 0009): `app/planner/` drafts the plan with
  one `PLAN` call through the AI router (its routes, ceiling and degrade flag), checks stored
  coverage per facet (2 matching claims at the mode's level), searches every scholarly,
  reference and web source of the open facets in parallel within per-tier budgets, dedupes
  and ranks the evidence, reads the best documents through their adapters and the fetcher,
  and in deep mode reads open-access full text and follows cited DOIs; the result is an
  `EvidencePack` (`docs/contracts/research.md`). Tested with fake adapters.

- **Composer** (decision 0010): `app/composer/` turns an evidence pack into candidates (stored
  claims, and read documents whole when short or by their verified quotes), makes one `COMPOSE`
  call through the AI router (Claude Sonnet first, Gemini when there is no Anthropic key), and
  keeps only sentences that cite allowed sources with verbatim quoted spans and whose every
  number or formula is in one of those spans; failing sentences are regenerated once, then
  dropped; hypotheses become open questions; when nothing survives the answer lists what was
  searched. Retrieved text and model output reach the model only inside untrusted blocks.
  Tested with fake model replies, including injection attempts in sources and the question.

- **Claim write-back and coverage enrichment** (decision 0011): `store_live_research` keeps
  each read document as a `LIVE_RESEARCH` source with embedded chunks, turns composed sentences
  that cite live documents into claims (`PROVISIONAL` when quoted, `HYPOTHESIS` when inferred),
  deduped by derived ids, linked to the craft's concept or stage, with the question id and
  retrieval time on every citation (migration 0003). The daily **Coverage enrichment**
  workflow asks standard facet questions of the least covered crafts of every source within
  $2.50 a day. DB tests run on GitHub Actions.

- **The answer stream end to end** (decision 0012): `POST /api/answers/stream` runs the
  resolver, then for `HYBRID` and `DEEP` the planner, live research, the composer and the
  write-back, and streams `status` steps, cited sentences, sources, open questions, follow-ups
  or `not_enough_evidence`, and `done` as they are produced, with a heartbeat after 60 s of
  silence. `VERIFIED` answers from verified and reviewed claims with no model call. `DEEP` is
  for researchers and above; every model call runs as the asker, under the router's per-role
  daily cap and monthly ceiling. The web client shows each step, the cited answer with source
  chips and the source dialog (type, reliability, quote, locator, licence, link out), an empty
  state with "Research it live", and errors. Hand-written shared fixtures are produced byte for
  byte by the backend flow and parsed by the client.

- **Science, region, voice and media contracts** (decision 0014): typed models in
  `backend/app/schemas/` (`science.py`, `region.py`, `voice.py`, `voice_llm.py`, `media.py`) and
  matching client types with runtime shapes in `frontend/lib/` (`scienceContract.ts`,
  `regionContract.ts`, `voiceContract.ts`, `mediaContract.ts`, the shape kit `shape.ts`), pinned
  by hand-written golden files in `shared/` that the backend reproduces byte for byte and the
  client parses (`docs/contracts/science.md`, `region.md`, `voice.md`, `media.md`). `schemas`
  may now import `research`. Lanes 0015 to 0021 built the producers and screens against them.

- **Science engine** (decision 0015): `app/science/` parses formulas, balances reactions with
  the sympy integer null space (balanced only for one smallest positive solution; model
  coefficients are never read), normalises readings with pint and checks them against the PLAN 7
  stage envelopes, whose physical constants are cited claims quoting pinned Wikipedia
  revisions. Migration 0004 stores reaction citations, conditions and readings tied to one
  citation. The science seed (run by `seed_claims`) adds materials with kind and role for the
  six seeded crafts, compounds, the iron acetate, indigo and alizarin-lake reactions and the
  durations and concentration the seed claims state. `GET /api/crafts/{slug}/process` answers
  the contract and reproduces its golden file (DB test on GitHub Actions);
  `app/scripts/link_compounds` fills PubChem records through the existing adapter.

- **Region profile and map layers** (decision 0016): `GET /api/crafts/{slug}/region` answers a
  craft's cited district places (a point placed by the polygon that covers it) and states of
  practice with their stored environment: every district value with its grid and period, GLiM
  rock types by name, and for state places and districts without a polygon the state's
  area-weighted means, sums, minima and maxima with how many of its districts they cover (rock
  types and commodity counts absent from a district counted as zero). `GET /api/map/layers`
  lists the 21 registry layers that have values; `GET /api/map/layers/{layer}` sends district
  values, type 7 quantile classes and a content-hash ETag (304 on a match). Migration 0005 adds
  the per-row grid (now loaded by `etl/geo/load.py`), dataset links, rock names and a layer
  index, and fills the grid and rock names of rows loaded earlier. Everything answers before,
  during and after a geo load. The three golden files are reproduced from records and, on
  GitHub Actions, from stored rows; the layer file now carries the computed classes and version.
  The answer write-back now finishes when the learner leaves (`core/shielded`), and craft
  descriptor vectors are filled on every release and daily.

- **Craft page and region panel** (decision 0019): `/crafts/[slug]` has Overview, Region,
  Process, Materials and Sources. Process is a timeline of the process route's stages with their
  cited claims, materials, conditions (every reading with its citation, "Sources differ",
  "Outside usual range") and reactions in KaTeX mhchem (`trust:false`); Region shows the places
  on the India map with their districts and states filled, and per place the environment values
  with statistic, dataset, grid and period, the state-only and inherited wording and the dataset
  credits. `/map` adds a layer picker that draws the map layer routes as district choropleths on
  the existing shapes, with legend, caption and attribution. Evidence badges gained the scoped
  `evidence` ramp. Built against the golden files; the backend routes come from lanes 0015-0016.

- **Voice UI** (decision 0020): a voice dock on `/ask` (the mic in the ask box) and the craft page
  (Talk), shown only when the config's voice availability is on, at least 30 s remain and the
  browser can carry the transport. The voice notice is accepted before the first session; the
  call runs through `POST /api/voice/session` as `RELAY` (push to talk, the turn stream, the
  spoken reply) or `AGENT` (`@elevenlabs/client` 1.36.1 over WebRTC with the token only). Client
  tools are re-checked against what the page holds (the session's craft, drawn stages, answers
  in the transcript, media options) before they open the Region or Process tab or the sources;
  the transcript shows only our cited sentences with the answer view's chips and Sources list;
  ending, time up, refusals and dropped calls have their states. The CSP gains `connect-src`
  for the LiveKit host the SDK uses.

- **Media UI** (decision 0021): stages on the craft page's Process tab draw Image and Video exactly
  for what `GET /api/media/options` lists, with the units left today; a press creates a job with
  its own idempotency key (sent again unchanged when no answer came), polls it after the server's
  `pollAfterSeconds` with the ProgressBar, and shows the asset after the stage's evidence labelled
  "AI illustration" with model and day, the server's alt text and a Download saved under the
  server's file name. Expiring links are renewed, job ids survive a reload in session storage,
  and professors get the sharing step the asset lists once the governance lane serves it. The CSP
  names the media bucket for downloads, images and video.

- **Media backend** (decision 0018): `backend/app/media/` serves `docs/contracts/media.md`.
  `GET /api/media/options`, `POST /api/media/jobs` and `GET /api/media/jobs/{id}` derive each
  stage's claim set from stored rows (levels, quote checks, ACL, sensitivity, restricted sources,
  group words out), build the versioned prompt with the fixed bans and the filtered style hint,
  answer a shared asset with the same `promptHash` free and at once, hold units in the quota
  ledger and dollars through the router (media sub-cap and ceiling), and seal an HMAC bundle.
  `kv-worker` now ships (`app/worker.py`): it claims `Job` rows per queue (4 images, 2 videos),
  calls Gemini through the Interactions API with the router's fallback and settlement, checks the
  PNG or removes the clip's audio, names the file with `services/naming.py` (golden rows in
  `shared/naming-golden.json`), uploads it to the private bucket and labels the asset; failures
  retry twice within the 4-minute timeout and end with a refund. Migration 0008 adds
  `MediaJob.assetId` and `MediaAsset.model`. Unverified provider behaviour is listed in the
  decision; media stays hidden until `MEDIA_BUNDLE_HMAC_KEY` exists.

- **Voice backend** (decision 0017): `backend/app/voice/` serves the voice contract.
  `POST /api/voice/session` runs the contract's checks (capability, verified email, voice notice,
  craft, configuration, one live call, 30 s of `VOICE_SECONDS`, the platform's live calls) and
  answers `RELAY` (the default) or `AGENT` (an ElevenLabs conversation token whose conversation id
  is bound to the row by a server-held HMAC nonce). The custom LLM at
  `/api/voice/llm/v1/chat/completions` checks the bearer and the binding (every failure the same
  401), sends `end_call` at the call's length or turn cap, and speaks one turn: no
  planner, the craft's claim pack loaded at session start, stored claims (`VERIFIED`) or one
  checked `VOICE_TURN` compose (`HYBRID`), at most 60 words with spoken source labels, a filler
  after 0.7 s. Relay turns run speech to text, the same turn and text to speech, billing heard and
  spoken seconds. Transcripts are scrubbed of email addresses and phone numbers, Fernet-encrypted
  and purged after 30 days by the daily upkeep, which also reconciles agent calls. One ElevenLabs
  adapter (`providers/elevenlabs.py`), a resource-neutral quota ledger (`providers/quota.py`),
  migration 0006, `/answers/config` sends the availability block, and
  `app/scripts/provision_voice_agent.py` creates or updates the agent (not run). The spike has not
  run.

- **Answers in Indian languages** (decision 0023): English plus Hindi, Bengali, Tamil, Telugu,
  Marathi, Gujarati, Kannada, Malayalam, Odia, Punjabi, Assamese and Urdu, one line each in
  `research/vocabulary.ANSWER_LANGUAGE_SPECS`. Answers are composed and checked in English, then
  translated in one `TRANSLATE` call (Gemini first) with a post-check of numbers in any script,
  formulas, mhchem, units and script; a sentence failing twice stays English; citations are
  copied, quotes stay verbatim. Claim translations are cached per claim and language (migration
  0007, which also seeds the TRANSLATE routes and the `answerLanguage` preference). The planner
  adds native-language Wikipedia and Wikidata queries and an English rendering of the question;
  Wikidata and Commons fetch in the item's language. Ask has a language picker (Auto follows the
  question's script), answers carry `lang` and `dir` (Urdu right to left) in local Noto Sans
  faces, and a control shows the English original. The voice turn's entry point is
  `answer_translation.translated_sentences`.

- **Voice in every answer language** (decision 0025): the thirteen answer languages are offered for
  voice, derived in `voice/languages.py` from what `scribe_v3` and `eleven_v4_turbo` list on the
  ElevenLabs documentation (all thirteen); `/answers/config` sends them and the client keeps no list.
  A turn ranks with the English rendering of the question, composes and checks in English,
  translates the sentences it will speak through `translated_sentences` (cached per claim), caps 60
  words in the session language and leaves out a sentence that fails translation twice. Speech to
  text gets the session's Scribe code, speech its language code, and fillers and refusals come from
  one phrase table per language. The dock follows the Ask language preference, offers a picker
  between calls and draws the transcript with `lang` and `dir`. The agent lists the languages as
  presets (not provisioned).

- **Admin role** (decision 0024): `ADMIN` ranks 50, between Professor and Master admin, label
  "Admin". It holds everything a professor does plus inviting professors, changing roles and
  suspending accounts ranked below Admin, usage, the audit log and datasets; keys, routing,
  quotas, ceilings and anything done to an Admin or Master admin stay with the master admin.
  Two-step verification is required; daily allowances are 3600 voice seconds, 100 images, 20
  videos and $10 of AI spend. Every Manage users change now checks the target's rank, roster
  changes check the entry's role, and migration 0009 adds the enum value, the quota rows and the
  daily cap. The web client shows the settings hub and Usage to admins, offers only the actions
  each row allows, and checks its ranks and labels against `shared/roles.json`.
- **Yahoo sign-in** (decision 0026): "Continue with Yahoo" on the login page, drawn only when
  `NEXT_PUBLIC_YAHOO_CLIENT_ID` is set. DR's OpenID Connect module is ported for Yahoo and
  Microsoft (Microsoft off without keys): PKCE code flow through `/login/callback`, the code
  redeemed by the backend with `YAHOO_CLIENT_SECRET`, the ID token checked against Yahoo's issuer
  and keys with a single-use server nonce (`POST /auth/oidc/nonce`), a Yahoo-verified address
  required, admission through the access roster exactly as Google's, `authProvider` `YAHOO`, and
  two-step verification challenged as for every sign-in. Migration 0010 adds `MICROSOFT` and
  `YAHOO` to `AuthProvider` and `OIDC_SIGN_IN` to `AuthNoncePurpose`. `/auth/config` reports
  `yahooEnabled` and `microsoftEnabled`.
- **First password in Settings** (decision 0028): an account that signs in with Google,
  Microsoft or Yahoo adds a password after signing in again with its own provider. DR's provider
  proof is ported to `POST /auth/change-password`, with a fresh ID token for the account's address
  and a single-use `FIRST_PASSWORD` nonce bound to the account (`POST /auth/first-password/nonce`);
  migration 0011 adds the purpose.

- **Review fixes for lanes 0014 to 0021** (decision 0022): voice spend fails closed. A relay
  upload is measured before speech to text (a WAV by its own length, compressed audio by a byte
  ceiling of a minute at the dock's 32 kbit/s), claimed under the session row's lock with a
  minute held and one of its 40 turns used, and keeps at least its floor, so silence and noise
  are no longer free; relay turns and replays have per-user limits, and a reply is synthesised
  again only during the call or two minutes after, billed under its own key. An agent call holds
  its whole length at the start, reconciliation settles both ways, and an ended call keeps the
  user's slot until it is settled or 12 minutes pass (the user's ended calls are settled when the
  voice availability is read and at their next start). The style hint's banned words now match plurals and include the group words, the
  writing, people and override words, and the hint sits before the facts as a description with
  the bans last (`media-prompt/v2`). `CraftRegion` carries its places' sources, numbered on the
  Sources tab. One home each for HMAC keys (`core/security.secret_key`), India time
  (`core/clock`) and the first-citation walk; a frontend spec pins the client's vocabularies to
  the backend tuples, and Frontend checks now watch the backend files their specs read.

- **E2E production run** (decision 0029): **E2E production** (dispatch only) drives the deployed
  site with Playwright at 1440, 834 and 390 px wide as one Researcher account signed in through the
  login form, checks every screen (console, failed requests, sideways scroll, overflowing text,
  alerts, gap copy, the role's menu), screenshots it, and with `questions=true` asks the English and
  Hindi known-answer questions in Hybrid and checks them on the wire. `app.scripts.provision_e2e_account`
  creates or resets the account; `seed_admin` now shares its upsert (`services/password_accounts`).

- **Explainer contract** (decision 0030, phase A of `docs/plans/answer-experience.md`):
  `docs/contracts/explainer.md` and the typed models in `backend/app/research/` that the phase A
  lanes build against: the explainer document (ordered sections by discipline, each `READY` with
  blocks or `EMPTY` with what was searched), one block envelope with a version per kind for all 21
  kinds of the plan (prose, process ladder and images built; the rest declared with their fields
  and refused until built), term spans, glossary terms and pictures (`MediaRef`: inline only under
  an open licence with its author, else a credited link card), six stream events (`understood`,
  `trail`, `section_started`, `section_state`, `block`, `section_done`) beside today's, depth by
  role as data (Basic and Detailed over `HYBRID`, Expert over `DEEP`; Master Admin uncapped and
  never degraded), and stored knowledge pieces with topic-key normalisation, the reuse rule and
  staleness. Client types and runtime shapes in `frontend/lib/explainerContract.ts` and
  `explainerStream.ts`. Hand-written fixtures `shared/explainer.{document,piece,term}.golden.json`
  and `explainer.stream.golden.sse` for Kutch Ajrakh are built from the seed claims and sources,
  reproduced byte for byte by the backend and parsed by the client. The cited-sentence shapes and
  the first-citation walk now live in `research/citations.py`.

- **Asking screen** (decision 0036): `/ask` is a composer: the question box, dictation through the
  browser's Web Speech API in the answer language (interim words live, Stop, the mic drawn only
  where the browser has it and has not refused that language), and under it the craft (a
  searchable picker with Any craft, never required; after the `understood` event it reads
  "Kutch Ajrakh · detected", offers Any craft and the candidates one tap away), the depth (the
  config's Basic, Detailed, Expert starting at the role's default) and the answer language. The
  ask body sends `depth` (and `anyCraft` when chosen), never `mode`; changing the craft, depth or
  language re-asks the same question. The Mode choice, the live call from the ask box and the
  "Which craft?" stop are gone; the production E2E asks at Detailed.

- **Understanding and depth** (decision 0031): every answer starts with one understanding step,
  the craft resolver plus one `PLAN` call (Gemini Flash Lite first) that picks among ambiguous
  candidates, resolves crafts the question names, and lists the fields it touches and the experts
  to seat (kept on `Answer.understanding`, migration `0013_answer_understanding`, for the phase B
  panel). A craft is never required: the best match proceeds with the others offered, nothing
  found or `anyCraft` answers for any craft, and research, stored search, composition and claim
  write-back all run without a craft (shared concepts). `understood` is the first event. The
  request takes `depth` (role default otherwise, any depth for any known role; `mode` and
  `ASK_DEEP` are retired); Basic and Detailed run Hybrid with 2/5 and 4/10 queries and documents,
  Expert Deep with 8/20. Per-answer caps per depth live in the AI budget (`answerCapUsd`, $0.25,
  $0.50, $1.00 to start); Master Admins have no caps of any kind and are never degraded, and
  their spend still records on Usage. A spend refusal while understanding answers from the
  craft's stored findings.

- **Pictures and terms** (decision 0034): Wikimedia Commons, Openverse (open licences with a
  creator only) and SearXNG image results are image sources, each the image method of its
  service's one adapter; a section's pictures are chosen by the words they share with the claims
  its blocks cite, inline under an open licence with the author, otherwise credited link cards
  whose thumbnail the page's own site serves, and stored once as `MediaRef` rows with their
  claims (`services/section_images`). The `Term` glossary (542 terms from the seed data: craft
  names with aliases and matched Wikidata labels, local names whose meaning the seed states, and
  compounds) is seeded by `seed_claims`; `research/term_marking` marks term spans on the server.
  `GET /api/terms/{key}?language=` answers a cited summary: the defining stored claims, else the
  Wikipedia lead of the term's item, else one web search and a checked `SUMMARISE` call (Gemini
  Flash Lite first), kept as quoted claims and cached per term and language. Migration
  `0012_images_and_terms` adds six tables and the `SUMMARISE` routes; pictures load with no
  referrer. The answer stream calls both since decision 0039 (below).

- **Explainer view** (decision 0037): `/ask` draws the answer as an explainer from the explainer
  stream (`lib/explainerStream.streamExplainer`, one reducer `lib/explainerState.reduceExplainer`;
  the old answer reducer and view are gone). It shows the understood line ("Answering for Kutch
  Ajrakh · Expert · in English", each part a button to its control), the research trail (live,
  then counts with Replay the trail), a section bar, and sections that build as blocks arrive with
  their working state: prose with citation chips, Verified and Reviewed badges and underlined
  terms that open a cited summary (`GET /terms/{key}`), the process ladder that fills as the reader
  scrolls (filled under reduced motion), the picture strip (credited inline pictures and link
  cards), the "From earlier research" mark, and an `EMPTY` section's note of what was searched.
  Listen's client (a dock that plays tracks per block and highlights the sentence and word being
  read) is drawn once the config lists the answer's language; its route is lane 0035's
  (`docs/contracts/explainer.md`, Listen). The production E2E reads the explainer events.

- **Listen, and the live call switched off** (decision 0035): `GET /api/answers/{answerId}/listen`
  reads the reader's own explainer (or one section) aloud through ElevenLabs
  (`/v1/text-to-speech/{voice}/with-timestamps`, `eleven_v4`): each block's cited sentences, each
  in its own language, in parts of at most 2,000 characters, with word timings for highlighting.
  Audio is cached per piece content hash, model, voice and language under `media/narration/` in
  the private bucket and served by one-hour presigned links, so a second listener costs nothing;
  misses are held and settled in `VOICE_SECONDS` (Master Admins never refused). `/answers/config`
  lists `listen.languages` only when the bucket, the key and ElevenLabs answer. The live call is
  off: `VOICE_CALL_ENABLED` (default false) makes every `/api/voice` route 404 and hides voice in
  the config; nothing is deleted. Listen reads the explainer sectioned composition (0032) keeps
  under `Answer.payload.explainer`.

- **Sectioned composition** (decision 0032): an answer is an explainer of sections, one per
  field the question touches (at most the depth's number), researched and composed in parallel:
  each section plans for its field and experts within its share of the depth's budget, streams
  its sources to the trail as they are found, read and quoted, and is composed by Claude Sonnet
  first, Gemini next. The server builds the blocks: a `process_ladder` from the stored process
  rows of the stages the model chose (refused unless every stage, sentence, material, condition
  and reaction is a stored row), and a `prose` block refused whole when a sentence is uncited or
  states a figure no cited claim or quote holds; a section left empty says what it searched, and
  one whose stored claims composed nothing researches live once more (finding 8a.2). Each checked
  block is translated on its own. Every structured-output schema now keeps to the keywords
  Anthropic accepts, and a refused format moves to the next route instead of free text (finding
  8a.1). The stored-only answer streams the same events. The plans of every section are kept on
  `Answer.plan` (migration `0014_sectioned_answer_plans`) and the explainer on
  `Answer.payload.explainer`.

- **Stored knowledge pieces and reuse** (decision 0033): every checked English block of a
  researched section (prose, process ladder) is kept as a `KnowledgePiece` with its craft, facet,
  topic key, depth, claims, sources, content hash and vector (migration `0015_knowledge_pieces`).
  Before planning, each section whose facet and topic (the glossary terms the question names,
  else the craft's districts for place fields, else the craft) hold a deep enough piece set whose
  claims are still visible as cited streams first, marked "From earlier research" with its date,
  and is not researched; the rest share the depth's budget. Research again (`fresh`) bypasses
  reuse and replaces what it bypassed. A trigger on `Claim` marks pieces stale when a claim they
  rest on is retracted, hidden, deleted or changes level or text, so the next answer rebuilds
  them; the Coverage enrichment run now rebuilds the stale pieces of the 10 most-asked crafts
  first, within its daily budget (`app.scripts.rebuild_pieces`). Stage concepts a process section
  cites stay concepts: no answer writes process rows (decision 0038).

- **Phase A review fixes** (decision 0038): Master Admins are no longer throttled when asking (30
  asks in 10 minutes for everyone else), and the term route shares `is_uncapped`. A failed craft
  lookup never blocks a question: without a chosen craft the question proceeds and the model's
  reply decides (any craft when nothing is found); only a spend refusal or a failed lookup of a
  chosen craft stops it, and no message tells the reader to name a craft. Reader-facing notes no
  longer name modes ("No live research ran.", "Research failed just now. Try again."). The
  OpenAI-compatible adapter now treats a refused `response_format` as a provider failure that
  moves to the next route, never free text, through one `providers/base.format_refused` shared
  with Anthropic and Gemini. Answers no longer write process rows ordered by the model. The trail's
  key prefixes and lengths have one home in `research/explainer.py`. No page's CSP lets web
  pictures in until the stream sends them. The production audit skips KaTeX's hidden MathML copy
  (finding 8a.4), checked in a browser by a unit spec, so Frontend checks install Chromium for the
  unit specs. Decision 0035 and the voice contract now say that enabling the call brings back the
  craft page's Talk dock only.

- **Pictures and terms in the stream** (decision 0039, plan 2.3 step 7): every English sentence
  of a section's prose and ladder is marked with the answer's glossary terms before translation,
  and stored pieces keep the marked blocks; a translated sentence keeps the spans whose text it
  still shows. Each section with blocks, researched or reused, searches its pictures from the
  claims its blocks cite while those blocks are sent and streams an `images` block after them
  (each image service 6 s, the step 8 s; a failure, a timeout or nothing relevant sends none and
  the section stays ready); pictures are never stored as pieces. An answer made only of reused
  sections offers the stored follow-ups. Every page's CSP `img-src` adds `https:`, so a move to
  `/ask` inside the app still shows pictures. The research golden now carries spans and pictures,
  and a unit spec draws them through the whole explainer view.
- **No connection held across a model call** (decision 0040): phase A's first production run
  (3b5cc6e, E2E run 43993673874) failed both questions on a pool deadlock, four parallel sections
  each holding a connection while the router waited for another. Stored search embeds first, and
  writing vectors and the craft resolver release their connection before embedding. The E2E now
  bounds a craft tab click at 30 s and records why it was refused.
- **One Gemini content per embedded text** (decision 0041): google-genai folded a list of texts
  into one content for `gemini-embedding-2`, so every multi-text embed returned one vector and all
  1,919 claims were stored without vectors (stored search ran lexical only). Each text is now its
  own content; the vectors are filled once on the box after the deploy.
- **Phone Process layout** (plan finding 8a.3): the reactions grid's implicit column grew to a long
  KaTeX equation and the Process page scrolled 114 px sideways at 390 px; the reaction, answer
  reaction and material grids are `grid-cols-1`, so each card holds the screen's width and the
  equation scrolls inside it.
- **Production proof of phase A (2026-11-17):** E2E run 44001978530 passes every screen at desktop,
  tablet and phone; both known-answer questions pass (27 cited sentences, 52 citations); the Hindi
  answer reused all five stored blocks of the English one; every section carried pictures. Claude
  Sonnet is COMPOSE route 1 again (Gemini 2, GPT 3) and composed 36 enrichment sections with no
  refusal. All 1,958 claims and the five pieces have vectors.
- **Enrichment fixes (2026-11-17, run 44001067308):** 10 of 12 crafts succeeded within the $2.50
  day. Two failed because a merged search result was fetched through the source that found it
  first rather than the source of the kept item (`'openalex:W…' is not an id of the crossref
  adapter`); the kept item's own source now leads `found_by`. CORE failed every search because
  `/v3/search/works` answers 301 to the trailing-slash path and source HTTP follows no redirects;
  the adapter now asks the slash path. Semantic Scholar is rate-limited until its key is added.
- **Craft sync from both portals is live (2026-11-17, run 44024826347):** the portals' release
  0.0.7 serves the signed craft feed with the flag on; the first sync verified both signatures
  (designer 459 crafts, documentation 462), synced 462, created none, merged one and found no
  name conflicts. It runs daily at 21:37 UTC.

## Next

1. Close phase A of the answer experience (`docs/plans/answer-experience.md`, phase A status):
   the E2E run at three widths after the phone layout fix (finding 8a.3), and Listen once the
   server's Elastic IP is on the ElevenLabs key's allow-list (the key answers `ip_not_allowed`).
2. The first live media jobs to confirm decision 0018's unverified items; the ElevenLabs spike of
   PLAN 10.1 on GitHub Actions (lane 0017's open item), which also records a relay turn's real
   billing; the governance lane serves the sharing route of `docs/contracts/media.md`. Science
   engine follow-ups are in `docs/TECH_DEBT.md` (decision 0015).
3. Run the known-answer questions with **E2E production** (`questions=true`) once deployed (PLAN
   section 0, decision 0029), and clear the answer stream gaps in `docs/TECH_DEBT.md` (answer and trace rows, researcher
   chunk access).
4. The `WEB_READ` reader for long documents.
5. Clear debt as files are touched (`docs/TECH_DEBT.md`), lowering the hygiene baseline.

## Waiting on the owner

- E2E production run: after the next backend deploy, run `app.scripts.provision_e2e_account` on the
  box, set `E2E_EMAIL` (`e2e-researcher@kalavigyan.example`) and `E2E_PASSWORD` as GitHub secrets,
  then dispatch **E2E production** (`docs/RUNBOOK.md`, E2E production run).

- Free OpenAlex, Semantic Scholar and Springer Nature API keys (Settings, API keys); without
  them OpenAlex shares a small daily allowance per IP, Semantic Scholar's shared pool answers
  429 often, and Springer Nature stays off. An Elsevier institution token lets Elsevier return
  abstracts.

- Media (lane 0018): re-run `infra/scripts/seed_secrets.py` once so it generates
  `MEDIA_BUNDLE_HMAC_KEY` (with the voice keys below); media stays hidden until it exists.

- Voice (lane 0017): re-run `infra/scripts/seed_secrets.py` once so it generates
  `VOICE_LLM_BEARER`, `VOICE_SESSION_HMAC_KEY` and `TRANSCRIPT_ENCRYPTION_KEY`; voice stays hidden
  until `TRANSCRIPT_ENCRYPTION_KEY` and `ELEVENLABS_API_KEY` exist. For `AGENT`: run
  `python -m app.scripts.provision_voice_agent` on the box, store the printed agent id as
  `ELEVENLABS_AGENT_ID`, run the spike, and set `AppSetting` `voice.transport` to `AGENT` only if
  the custom-LLM request proves to carry the conversation id (`docs/contracts/voice.md`); it stays
  `RELAY` otherwise.

- Yahoo sign-in: register the Yahoo app with the redirect URI
  `https://kalavigyan.vercel.app/login/callback`, set `YAHOO_CLIENT_ID` and `YAHOO_CLIENT_SECRET` as
  GitHub secrets and deploy the backend, then set `NEXT_PUBLIC_YAHOO_CLIENT_ID` in Vercel
  (`docs/RUNBOOK.md`, Yahoo sign-in).

- Cloudflare Turnstile widget for `kalavigyan.vercel.app` (email sign-up is Google-only in
  production until then).
