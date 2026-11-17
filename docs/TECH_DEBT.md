# Technical debt register

What is knowingly below standard, why it was left, and what clears it. Add an entry in the same
change that takes the shortcut; delete it in the change that clears it.

Last reviewed: 2026-11-17.

## Infrastructure

### CloudFront to origin is plain HTTP

- **What:** CloudFront reaches nginx on the EC2 box over HTTP on port 80 (`docs/RUNBOOK.md`,
  `infra/terraform/cloudfront.tf`). The origin is protected by the CloudFront-only security
  group and the `X-Origin-Verify` header, but the hop between CloudFront and the box is not
  encrypted. The designer and documentation portals use the same pattern.
- **Why left:** TLS ends at CloudFront; there is no custom domain or origin certificate yet, and
  the pattern matches the portals so they can be changed together.
- **Clears it:** an origin certificate (custom domain with certbot, already installed and
  unused on the box) and `https-only` origin protocol, done for all three portals in one change.

### Turnstile keys pending

- **What:** `TURNSTILE_SECRET_KEY` (GitHub secret) and `TURNSTILE_SITE_KEY` (GitHub variable) are
  not yet issued for `kalavigyan.vercel.app`. With `APP_ENV=production` and either missing,
  email sign-up answers 503 and the sign-up page offers Google only
  (`docs/contracts/infra.md`, `backend/app/services/turnstile.py`).
- **Why left:** the Cloudflare widget has to be created by the owner.
- **Clears it:** create the widget, set both values; Deploy backend copies them to Parameter
  Store.

## Backend structure

### Python code over budget

- **What:** recorded in `tools/hygiene_baseline.json` on 2026-11-16: 12 files over 400 lines, 54
  functions over 40 lines, 9 functions with more than 5 positional parameters. The largest files:
  `backend/migrations/versions/0001_initial_schema.py` (2853), `etl/crafts/wikidata_link.py`
  (1121), `backend/app/api/routes/auth.py` (784), `backend/app/services/two_factor.py` (703),
  `etl/crafts/seed_claims.py` (642), `backend/app/providers/router.py` (566),
  `etl/crafts/aliases.py` (543),
  `backend/tests/db/test_db_flows.py` (464), `backend/app/services/knowledge_view.py` (502),
  `backend/app/services/managed_secrets.py` (496), `backend/app/services/ai_providers.py` (454),
  `backend/app/data/craft_master_loader.py` (433).
- **Why left:** most were ported from the designer portal with the same shapes so the portals
  stay mergeable; splitting them is a separate restructuring change.
- **Clears it:** split along responsibilities when a file is next changed; run
  `tools/hygiene_check.py --update-baseline` after each clean-up. The initial migration stays
  one file (migrations are not rewritten).

### Answer stream: gaps left on 2026-11-16 (decision 0012)

- **What:** (1) Cleared by decision 0016: the write-back runs as shielded work and finishes
  when the learner leaves; only a write-back still running 8 s into a shutdown is lost (logged).
  (2) `AnswerSentence`, `AnswerCitation`, `AnswerTrace` and `LiveCandidate` rows are not
  written; the `Answer` row has the plan, tiers and cited claim ids but no `costUsd`,
  `latencyMs` or `payload`. `VERIFIED` answers write no `Answer` row (`answerId` null).
  (3) The planner's stored search reads `PUBLIC` chunks only; the `RESEARCHER` ACL of
  researchers is not passed through. (4) `Citation.context` is always null (the passage around
  a quote is not stored with the citation). (5) The resolver holds its session while it embeds
  the question for the semantic step. (6) A researched answer is shown only after write-back,
  so the learner waits for the whole pipeline before the first sentence.
- **Why left:** the trace and answer-sentence tables, cost settlement per answer and chunk
  citations each widen the contract; this change wires the flow first.
- **Clears it:** write the answer rows and trace from the events already produced, with spend from the
  request id's `UsageEvent` rows; pass `RESEARCHER` to the stored search when the asker may
  read it; store the quote's surrounding passage on `ClaimSource`; embed before opening the
  resolver's session; send stored-claim sentences before write-back once the client can
  replace a sentence's citations.

### Figure post-check covers digits and formulas only

- **What:** `research/quotes.unsupported_figures` checks numbers written in digits and
  formula-like tokens with a digit. Number words ("three"), units (a sentence may say °F where
  the quote says °C), unit conversions and element-only formulas (`NaCl`) are not compared.
  PLAN 3.1 asks for numbers, units and formulas.
- **Why left:** the contract needed a deterministic rule before the composer lanes start; unit
  handling belongs with the pint normalisation of PLAN 3.1 step 5.
- **Clears it:** parse quantities with pint on both sides and compare values and dimensions;
  match number words; treat element-symbol sequences as formulas.

### Model catalogue sits in services, used by providers

- **What:** `providers/budget.py` and `providers/router.py` import `services/ai_providers.py`,
  `services/app_settings.py` and `services/managed_secrets.py`, so the adapter layer sits above
  services (decision 0001). `providers/budget.py` also imports `app_settings` inside a function.
- **Clears it:** move the catalogue into `providers/` (kept in the designer portal's shape) and
  pass settings and keys in from the caller.

### Provider calls outside the adapters

- **What:** `services/managed_secrets.py` probes provider endpoints over HTTP itself to test a
  key, and `services/ai_providers.py` still holds `ModelDeclined` and `gemini_reply_text`, which
  nothing calls. One adapter per external service is the rule.
- **Clears it:** give each adapter a key-test call used by `test_secret`, and delete the unused
  Gemini helpers.

### Rate limits are per process

- **What:** `core/rate_limit.py` keeps its windows in module-level memory, so each API colour
  and worker counts separately and a restart resets them. The same holds for the scholarly
  adapters' pacing, Retry-After pauses and response cache (`sources/http.SourceHttp`): each
  process that builds `scholarly_sources` paces itself, so two workers can together exceed a
  service's interval.
- **Clears it:** a shared store (Redis is on the box) behind the same functions.

### Craft descriptor embeddings are not filled

- **What:** `app/scripts/embed_craft_descriptors.py` now runs after the seeds and the craft sync
  on every release and first in the daily Coverage enrichment run (decision 0016), but it fills
  only missing vectors, so a craft whose aliases change later (portal sync, enrichment) keeps
  its old vector.
- **Why left:** detecting a changed descriptor needs a stored hash per craft, a schema change.
- **Clears it:** store a hash of `descriptor_text` per craft and embed again when it differs.

### Craft matching has no evaluation set

- **What:** PLAN 5.2's gate (300 match cases, top-1 at least 95%, in CI on seeded fixtures) does
  not exist. The resolver's weights, `FUZZY_MIN_SIMILARITY` 0.85, `SEMANTIC_MIN_SIMILARITY` 0.6
  and the hand list `GENERIC_TOKENS` were set from about 30 questions tried by hand against the
  master list (decision 0004). The model choice among the top 5 (PLAN 5.2 step 6) is now the
  understanding step's `PLAN` call (decision 0031), unmeasured as well.
- **Why left:** the cases have to be written from real questions in several scripts; owner
  direction is 1-2 known-answer checks at a time, not a large suite on every change.
- **Clears it:** collect the cases as answers are corrected, run them in Backend checks, and tune
  the constants and the understanding prompt against them.

### Scholarly adapters: gaps left on 2026-11-16 (decision 0005)

- **What:**
  - The answering service and the coverage job call `scholarly_sources` through
    `live_sources`; the API rebuilds them every 600 s (`LiveSourcesStore`), which resets each
    adapter's pacing and cache.
  - Two fixtures are not plain recordings. Semantic Scholar's search answered 429 to every
    unauthenticated try, so `tests/sources/fixtures/semantic_scholar_search.json` wraps two
    recorded paper records in the search envelope; and no `SPRINGER_NATURE_API_KEY` exists, so
    `springer_nature_search.synthetic.json` is hand-written from the documented shape (only its
    401 is recorded).
  - The configured `ELSEVIER_API_KEY` may search Scopus but not read abstracts (the abstract
    record has no `dc:description`, and `view=META_ABS` answers 401), so `elsevier` fetch is
    `not_found` for every record until an institutional token is set.
  - Publisher full text (Elsevier article, Springer Nature JATS, Wiley TDM) for DOIs Unpaywall
    reports closed (PLAN 17.1a) is not built; nor are the Zenodo adapter (PLAN 17.1) and
    Europe PMC full text.
  - OpenAlex without a key shares $0.10 a day per IP; the box will exhaust it quickly.
- **Why left:** keys, an institution token and the callers do not exist yet.
- **Clears it:** the owner sets `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` and
  `SPRINGER_NATURE_API_KEY` (and an Elsevier institution token); record the missing fixtures
  then; add the publisher full-text adapters behind the Unpaywall `CLOSED` check.

### Reference adapters: gaps left on 2026-11-16 (decision 0006)

- **What:**
  - The per-process pacing above applies to `reference_sources` too.
  - Wikidata time values coarser than a year (decade, century) are left out of the item text,
    and the Commons `published` date is empty unless the original date is ISO.
  - PubChem hazards keep at most three reporting sources; the ECHA terms allow non-commercial
    reuse only, which suits the IIT research use but would need review for any commercial use.
  - Commons media use `SourceKind` `OTHER`: the enum has no image or media kind.
  - `WIKIPEDIA_LANGUAGES` is English and Indian languages only; a learner writing in another
    language gets `InvalidInput` from the Wikipedia adapter.
- **Why left:** no caller yet needs other wikis; a media source kind needs a migration of the
  `SourceKind` enum.
- **Clears it:** add a `MEDIA` source kind with its migration when the media lane stores Commons
  files; widen the language list when the planner asks for it.

### Web search and fetcher: gaps left on 2026-11-16 (decision 0007)

- **What:**
  - Parsing runs in a worker thread; when the time limit fires, the fetch is refused at once but
    the thread keeps parsing until it ends. A hostile document can hold a thread and memory
    past 10 seconds (bounded by the 3 MiB body, pypdf's limits and the unit's 768 MB cap).
  - robots.txt is read with the standard library parser, which applies the first matching rule
    rather than RFC 9309's longest match. It can refuse a page an `Allow` line permits (fails
    closed, never the reverse for one agent group).
  - The PDF decompression cap counts page content streams only; images and fonts are left to
    pypdf's own limits.
  - Every web page is trust `C`; a government, museum or university site is not yet ranked
    higher.
  - Search hits on plain http and URLs longer than about 490 characters are left out (ids are
    the URL and at most 500 characters).
  - The SearXNG and Brave fixtures are hand-written to the documented response shapes, not
    recordings: SearXNG runs only on the box and no Brave key was available on the laptop.
  - Only the planner calls the web search and the fetcher; `WebFetch` rows are not written;
    the fetcher service has not run on the box.
  - Each hop opens a fresh client (no connection reuse), which costs one TLS handshake per hop.
- **Why left:** no caller yet; a kill-able parser needs a subprocess pool; ranking by domain
  needs a reviewed list; recording needs the box or a key.
- **Clears it:** run the parsers in a process pool that can be killed on timeout; switch to a
  longest-match robots parser; record SearXNG and Brave fixtures from the box; add a reviewed
  domain trust list; write `WebFetch` rows from the answering service; smoke-test
  `kv-fetcher` on the box after the next deploy.

### Stored-knowledge retrieval: gaps left on 2026-11-16 (decision 0008)

- **What:** (1) Stored claim and chunk vectors carry no model or prompt stamp: if the `EMBED`
  route changes model, old vectors and new question vectors are no longer comparable and the
  vector ranking silently degrades. (2) Seeded and imported rows get vectors only from the daily
  Coverage enrichment workflow, which runs `embed_knowledge` before it enriches; until its first
  run after a seed, T1/T2 rank those rows by full text only. Each write-back embeds only the
  claims and chunks it wrote (`embed_written`, decision 0013); when that embedding fails, the
  rows wait for the next scheduled run. (3) The corpus imports (Wood Handbook,
  immersive-episteme sources) do not store chunks yet; write-back does
  (`live_source_store.keep_document`). (4) A claim whose text changes in place keeps its old
  vector. (5) Full-text ranking reads Latin-script words only; answers search with an English
  rendering of the question (decision 0023), but a direct caller of `StoredKnowledgeSearch` with
  Indic text is ranked by the vector alone. (6) The HNSW indexes on `Claim.embedding` and `Chunk.embedding`
  are unused by the exact craft-scoped scan.
- **Why left:** the stamp needs a migration; the corpus imports are their own lane.
- **Clears it:** add `embeddingModel` to `Claim` and `Chunk` (and `Craft`), filter the vector
  ranking on the route's current model and re-embed on change; also run `embed_knowledge` after
  the seeds in Deploy backend; store chunks from the corpus imports; clear `embedding` when a
  claim's text changes; add a transliterated or translated text query for Indic questions; drop
  or use the HNSW indexes once a scope is large enough to need them.

## Checks not automated yet

- **Nesting depth** (budget 3) is not measured by the hygiene check.
- **Frontend size budget** (about 150 lines per component file): 33 `.tsx` files are over it on
  2026-11-16, the largest `components/ui/SearchableSelect.tsx` (1243),
  `app/(protected)/admin/access/page.tsx` (813), `components/forms/DateTimeField.tsx` (743).
  Many are ports from the designer portal.
- **Frontend import boundaries** are not linted.
- **Geo ETL tests** (`etl/geo/tests`) do not run in any workflow; `geo-etl.yml` only extracts and
  loads.
- Clears it: a lint rule set for size and boundaries with a baseline for the existing files, a
  nesting count in `tools/hygiene/budgets.py`, and a test job in `geo-etl.yml`.

### Planner and tiered research: gaps left on 2026-11-16 (decision 0009)

- **What:** (1) `LiveCandidate`, `WebFetch` and
  `AnswerTrace` rows (queries and providers per answer, PLAN section 6) are not written; the
  answering service (`services/answering.py`) stores only the `Answer` row and its claims.
  (2) The pack holds documents, not quotes: the `WEB_READ` reader that extracts verbatim quotes
  for the composer is not built. (3) Coverage runs one stored search per facet, each embedding
  its target (up to eight embedding calls per question). (4) References are followed only as
  DOIs written in the text, through Crossref, which returns abstracts only; links in pages and
  reference lists without DOIs are not followed. (5) Facet coverage counts claims that share a
  word with the target; it does not judge whether they answer it. (6) Every query runs on every
  source of its tier, including Commons and PubChem for questions they cannot serve (each
  answers quickly with no hits).
- **Why left:** the `WEB_READ` reader and the trace tables are the next lanes; a better coverage
  judgement needs the known-answer checks to calibrate against.
- **Clears it:** the answering service writes the trace and candidate rows; the reader turns
  documents into quoted evidence; embed the facet targets in
  one batch; follow reference lists through OpenAlex `referenced_works` when that adapter
  exposes them; route facet types to the sources that can serve them once the checks show
  which do.

### Composer: gaps left on 2026-11-16 (decision 0010)

- **What:** (1) A read document longer than 4,000 characters gives the composer nothing until the
  `WEB_READ` reader fills its item's quotes. (2) Stored passages (T2 `ChunkHit`) are not composer
  candidates: a sentence can cite a claim or live evidence, and the stream's `Citation` names a
  claim. (3) A stored claim is offered as its text alone; its citations' quotes and sources are
  not in `ClaimHit`, so the model cannot quote the source behind a claim and the label says only
  "stored claim". (4) `ResearchSummary.services` lists searchers that returned evidence or
  failed, not every searcher asked.
- **Why left:** the reader and the answering service are separate lanes; chunk citations and
  claim sources need the stream and retrieval contracts to grow together.
- **Clears it:** the reader fills quotes for long documents; the answering service builds
  `compose_request` from the pack, joins each claim's sources and quotes from the database into
  its candidate, and records which searchers ran in the pack; add a chunk candidate kind with a
  source-only citation when the stream allows one.

## Live research write-back (decision 0011)

### The quote overlap reads English passages only (decisions 0013, 0023)

- **What:** answers are composed and checked in English and translated afterwards (decision
  0023), so the overlap holds for English sources. `UNRELATED_QUOTE` still compares the sentence's
  English content words with its quotes' words (`backend/app/research/quotes.py`,
  `quote_overlap`), so a sentence resting only on a Hindi Wikipedia or Wikidata passage, found by
  a native-language query, is dropped; such passages count only beside an English passage that
  carries the wording.
- **Why left:** the owner kept every existing check unchanged; a cross-language overlap needs a
  checked translation of the quote first.
- **Clears it:** translate a non-English quote into English with the TRANSLATE route, check it
  with `translation_problems`, and compute the overlap against that rendering while the citation
  keeps the verbatim quote.

### Licence allow-list is by string

- **What:** `open_licence` matches licence names and canonical URLs; national ports of CC
  licences (for example `CC BY 2.5 IN`) and licences named only in prose are closed, so their
  full text is stored for researchers only (`backend/app/research/licences.py`).
- **Why left:** closed is the safe side; the common spellings from the adapters are covered.
- **Clears it:** add each further spelling with a test when a source shows it.

### A re-chunked source can move a citation's chunk

- **What:** `ClaimSource.chunkId` points at the chunk that held the quote when it was written.
  When a live source is read again with different text, `replace_source_chunks` updates chunks
  by ordinal, so an older citation's `chunkId` may then point at a chunk that no longer holds
  its quote (`backend/app/services/live_source_store.py`). The quote and source stay correct.
- **Why left:** nothing reads `chunkId` yet; the quote is the citation.
- **Clears it:** re-point citations of a re-chunked source with `chunk_for_quote` in the same
  transaction, or clear `chunkId` for chunks whose text changed.

### Coverage counts only a craft's own concepts

- **What:** `least_covered_crafts` and the open-facet test count claims on concepts whose
  `craftId` is the craft; claims on the sub-category's shared concepts, which stored retrieval
  also reads, do not count (`backend/app/services/coverage_selection.py`).
- **Why left:** shared family claims are general; the job's purpose is craft-specific coverage.
- **Clears it:** weight shared claims (for example half) once family pages exist.

### The coverage job has no per-call spend cap

- **What:** the daily budget is checked before each question; a single question's planner,
  reading and composer calls are not capped, so a run can pass the day's budget by one question
  (`ENRICHMENT_QUESTION_RESERVE_USD` $0.25 is the assumed size). `router_structured_model` has
  no `request_budget_usd` parameter (`backend/app/providers/structured.py`).
- **Why left:** the monthly ceiling still holds; the overshoot is bounded and small.
- **Clears it:** pass the remaining day budget as `request_budget_usd` through
  `router_structured_model` and `router_embedder`.

## Science, region, voice and media contracts (decision 0014)

### Contracts ahead of their producers

- **What:** the models, golden files and contract tests exist; the process (decision 0015),
  region (decision 0016), voice (decision 0017) and media (decision 0018) routes produce theirs,
  and `services/naming.py` with `shared/naming-golden.json` names media files. The media
  sharing route is still unserved.
- **Why left:** decision 0014 is the contract lane; sharing belongs to the governance lane.
- **Clears it:** the governance lane serves `POST /api/media/assets/{id}/sharing`.

### ElevenLabs behaviour not yet verified

- **What:** the voice binding rests on `custom_llm.request_headers` substituting
  `{{system__conversation_id}}` and on `custom_llm.api_key` arriving as a bearer, neither on
  ElevenLabs' official pages; also unverified are the URL suffix, custom-LLM tool calls reaching
  `end_call` and client tools, Hindi in agents, CSP hosts and the plan's retention minimum
  (`docs/contracts/voice.md`). Relay text to speech cannot run with zero retention
  (`enable_logging=false` is enterprise only).
- **Why left:** only a recorded round trip against a test agent can settle them (PLAN 10.1). Lane
  0017 built the agent path on the contract's assumptions (`custom_llm.url` ending `/api/voice/llm/v1`,
  the bearer, the header template) and its adapter tests on the documented response shapes; the
  spike workflow is not written, because it calls the real account.
- **Clears it:** the spike on GitHub Actions with a test agent made by
  `app/scripts/provision_voice_agent.py`, replacing the fixtures in `backend/tests/voice/fixtures`
  with recorded responses; `voice.transport` stays `RELAY` until it passes. Retention: an
  enterprise plan, or the Gemini voice for relay speech.

### Contract tests read files their workflow does not watch

- **What:** `backend/tests/contracts` reads `etl/geo/geo_etl/catalog.py`, `infra/terraform/*` and
  `docs/PLAN.md`, but Backend checks do not run on a push that changes only those. Adding them to
  the push filter would make such a push deploy the backend. The frontend side is closed: Frontend
  checks (which deploy nothing) watch `backend/app/models/enums.py`, `backend/app/schemas/**`,
  `backend/app/core/roles.py`, `shared/roles.json` and `infra/terraform/variables.tf`, the files
  its unit specs read (decision 0022).
- **Clears it:** a separate contract-check job (or a paths filter on pull requests only) that runs
  `tests/contracts` when those files change.

### Region golden values are hand-written

- **What:** the district numbers in `shared/region.craft.golden.json` and
  `shared/region.layer.golden.json` are illustrative shapes for tests, not ETL output; only the
  dataset rows are real, and the layer's classes and version are computed from the hand-written
  numbers (decision 0016).
- **Clears it:** when the full `geo-etl` load exists, regenerate the layer fixture's values from
  it in a reviewed change.


## Region profile and map layers (decision 0016)

### A district place carries every stored value

- **What:** `GET /crafts/{slug}/region` sends every stored value of a district (about 300 with
  the full load: monthly normals, yearly forest loss, percentiles and uncertainty bounds) and
  every aggregable series of a state, and a craft practised in many states sends one such place
  per state. The panel lists them all.
- **Why left:** the contract (decision 0014) asks for every row; choosing a headline set is a
  product decision.
- **Clears it:** a curated set of headline variables per facet in the contract (the layer
  registry is a start), with the rest behind a "More" view or left to the map.

### State aggregates are computed per request

- **What:** each region request groups the state's district rows in Postgres (one grouped query
  per request over the states it shows); nothing is cached.
- **Why left:** correct and fast enough for a handful of states; a cache needs invalidation on
  every geo load.
- **Clears it:** a `StateEnvValue` table filled by `etl/geo/load.py` after each load, or a
  materialised view refreshed by it.

### Two region rules mirror how the geo ETL writes rows

- **What:** `geo/records.LITHOLOGY_TWIN_PREFIX` assumes GLiM writes each class share both as
  `lithology_<code>` and as a `DistrictGeology` row, and `geo/aggregation.ABSENT_MEANS_ZERO`
  that GLiM shares and MRDS per-commodity counts exist only where present. Migration 0005 also
  copies the GLiM legend (`geo_etl/layers/geology.GLIM_CLASSES`) to name rows loaded earlier.
  No test reads the ETL to keep them in step.
- **Clears it:** have the ETL write the share once with its name and write zero rows (or a
  coverage row per dataset), then drop both rules; or a contract test that runs the GLiM and
  MRDS row builders on a fixture.

### Dataset links of rows loaded before migration 0005

- **What:** `EnvDataset.url` is filled only by a geo load after the migration, so until the next
  `geo-etl` run with `load` the region and layer answers send `url: null` for every dataset.
- **Clears it:** the next Geo ETL run with `load` (any dataset), which upserts every dataset row.

### States of practice are matched in two places

- **What:** `geo/places.practice_states` and `services/knowledge_view.craft_locations` both
  match `Craft.stateOfPractice` to `AdminState.name` case-insensitively; only the region skips
  `All India` explicitly and logs other unmatched names.
- **Clears it:** have the profile use `practice_states` (or an `AdminState` lookup in one service)
  the next time `knowledge_view.py` is split.

## Geo ETL state gaps (decision 0027)

### An unreachable tile reads as an absent one

- **What:** `etl/geo/geo_etl/raster.exists` turns any open error, a timeout or a server error as
  much as a 404, into "no such file", caches that answer for the process, and `raster.read`
  mosaics only the tiles it found. A WorldCover, Hansen or Copernicus DEM district whose tile did
  not answer is computed from the tiles that did, with no failure listed; when the tiles under its
  polygon did not answer but another tile in its padded bounds did, it comes back without valid
  cells and, since the addendum to 0027, counts as accounted for, even as a state's only district
  (when no tile answers, the read fails); a CHELSA or CHIRPS file
  that did not answer fails its step for the whole shard (which now fails the part). After the
  CHIRPS year lookup, file reads still rely on GDAL's own retries (7 tries of up to 120 s per
  request in the workflow), so a stalled server can still hold a job for hours.
- **Why left:** run 43884310432's gaps all came from the district shapes; telling an ocean tile
  from an unreachable one needs each layer's tile index, a change to every tiled layer.
- **Clears it:** probe tiles over HTTP as the CHIRPS lookup does (only 404 means absent, other
  errors retried then raised), or list each dataset's tiles once and treat a listed tile that
  cannot be read as a failure; cap GDAL's retries with an overall deadline per file.

### A grid read as nodata everywhere counts as "no valid cells"

- **What:** since the addendum to 0027, `coverage_of` trusts `Result.districts_without_cells`. A
  read that returns a grid of nodata (a SoilGrids WCS answer of masked cells for a whole state, a
  grid registered in the wrong place) lists every district without cells, accounts for every
  state, and the part passes with no rows. Before, it lost those states and failed.
- **Why left:** telling such a read from a real gap (Lakshadweep in GLiM, Mumbai in SoilGrids)
  needs a reference the layers do not have; a guard on "no valid cell in the whole grid" would also
  fail a run that selects only Lakshadweep.
- **Clears it:** fail a step whose grid holds no valid cell at all while the selection has land
  cells in an independent mask (for example the Copernicus DEM or WorldCover land fraction), or
  keep a reviewed list of districts expected without cells per dataset and fail any other.

### A silent district does not fail the part when its state has another district accounted for

- **What:** a selected district with no row, no no-cells listing and no failure is listed only
  under `districtsWithoutValues`; its state is lost only when none of its districts is accounted
  for. That includes a state with no rows at all where one district is listed without cells and
  another is silent, which the rule before the addendum failed. Every raster path now lists its no-cells districts, so such a district means a defect, and
  can only be found as `districtsWithoutValues` minus `districtsWithoutCells` minus the failed
  districts.
- **Why left:** the addendum to 0027 keeps the state-level rule the owner asked for; failing on a
  single silent district is a stricter rule not yet agreed.
- **Clears it:** list such districts under their own key in the part JSON and fail the part when
  it is not empty, or at least lose a state without rows unless every one of its districts is
  listed without cells.

### Each shard resolves the CHIRPS period on its own

- **What:** every CHIRPS extract job calls `latest_year` itself. Should CHC publish a new annual
  file while a run is going, shards could end on different years, and the combined table would
  hold two periods for one dataset; `combine` keeps the last dataset row it reads.
- **Why left:** CHC publishes once a year and a run takes under an hour.
- **Clears it:** resolve the year once in the workflow's plan job, pass it to every shard
  (a `--chirps-last-year` option), and have `combine` refuse parts of one dataset whose rows
  differ.

## Craft page and region panel (decision 0019)

### The profile still sends stages and science the page no longer reads

- **What:** `GET /crafts/{slug}/profile` (`services/knowledge_view.craft_profile`) still returns
  `stages` (with the uncited `durationText`) and an always-empty `science`; the craft page now
  reads the process route instead, and uses `stages` only to keep the profile's citation numbers.
- **Why left:** lane 0019 does not edit backend files.
- **Clears it:** drop both fields from the profile route and `CraftProfile` in one change, and
  number sources from the overview, materials and the process route.

### Map layer values carry no district names

- **What:** `MapLayer.values` is keyed by LGD code only and the client holds no district names, so
  hovering or tapping a district on `/map` shows its value and not its name
  (`components/map/MapLayerView.tsx`).
- **Why left:** the region contract (decision 0014) fixes the layer body, and the backend is
  another lane's.
- **Clears it:** add district names to `MapLayer` (or a cached districts route) with the contract,
  golden file and both tests, then show "Kachchh · pH 8.1".

### Craft page and map layers not yet seen running

- **What:** the timeline, region panel and choropleths are checked by typecheck, lint and unit
  specs of their pure rules, not in a browser: there is no React renderer in the unit project and
  nothing runs on the laptop. Their contrast, wrapping at phone width and the KaTeX rendering of
  real reactions are unverified.
- **Clears it:** the Production build job, then a signed-in smoke spec (craft page tabs, `/map`
  with `?layer=`) with route fixtures from `shared/` at desktop and phone widths, and screenshots
  once the 0015-0016 routes are deployed.

### The boundary caption has two homes

- **What:** maps drawn without the layer list (the craft page) print the caption from
  `components/map/MapAttribution.tsx`; `/map` prints the server's `boundary.caption`
  (`schemas/region.BOUNDARY_CAPTION`). The two are equal today.
- **Clears it:** have the craft page read the caption from `GET /map/layers` (or a shared
  boundary route) and delete the client constants.

## Voice backend (decision 0017)

### Voice in other languages is checked by text only (decision 0025)

- **What:** voice offers all thirteen answer languages from the ElevenLabs documentation, not from
  calls. Scribe's published accuracy is Scribe v2's, and Urdu's band is moderate (25-50% word error),
  so an Urdu question may often be misheard. The fixed spoken phrases in `voice/phrases.py` were
  written by the lane and not read by native speakers. In `AGENT` nothing yet tells the agent a
  session's language: the token takes none and client overrides are off, so the agent hears in its
  own language until `language_detection` switches; the presets are not provisioned.
- **Why left:** no provider call with a real key from the laptop, and no native reviewers in reach.
- **Clears it:** the spike records one relay turn per language and one agent call in Hindi; a
  native reader per language signs off the phrase table; if Urdu misses too often, drop `ur` from
  `STT_LANGUAGE_CODES` (voice then stops offering it) or try `scribe_v3` with Hindi as a
  `secondary_language_codes` hint; the spike decides whether the agent gets an `agent.language`
  override or one agent per language.

### The voice pack is claims only, ranked by words

- **What:** PLAN 10.3 asks for the T0/T1 pack with embeddings plus T2 passages; the pack is the
  craft's visible claims ranked by shared word stems (`voice/pack.ranked_claims`), without vectors
  or corpus chunks.
- **Why left:** a query embedding per turn is a second model call before the first sentence.
- **Clears it:** prefetch the claim vectors with the pack and embed the question in parallel with
  the filler; add T2 chunks as `EVIDENCE` candidates with their verified quotes.

### Voice upkeep rides the daily Coverage enrichment run

- **What:** purging transcripts after 30 days, closing calls left open and reconciling agent calls
  run as the first module of the daily box job in `coverage-enrichment.yml`; `kv-worker`
  (`app/worker.py`, decision 0018) runs only the media queue.
- **Why left:** the worker arrived with the media lane, which did not take on voice scheduling.
- **Clears it:** move `app.scripts.voice_upkeep` into the worker's schedule.

### Voice billing approximations

- **What:** a relay upload's floor is its bytes at 5 000 a second; compressed audio is not decoded,
  so a client encoding below the dock's 32 kbit/s (Opus goes down to 6 kbit/s) gets up to about
  6.7 times the floor's seconds of speech to text inside the 300 000-byte ceiling, still within
  the day's seconds. Parallel uploads are allowed; each holds its own minute under the row lock,
  so they cannot pass the day's seconds. An agent call cannot be hung up from our side: after its
  row ends the ElevenLabs call can run to the agent's 600 s, which reconciliation charges (the user
  may go below zero for that day). Refund and settle rows count on the day they are written, not
  the call's day.
- **Why left:** decoding needs ffmpeg on the box; ending a call needs an ElevenLabs endpoint the
  spike has not confirmed. Each is bounded by the day's seconds, the turn and replay limits and
  the 40-turn cap (decision 0022).
- **Clears it:** decode the upload's duration (ffprobe) before speech to text and bill that; end
  the ElevenLabs conversation when the row ends, once the spike shows how; date settlement rows to
  the call's day.

### Voice state held per process

- **What:** claim packs (10 minutes), relay reply audio (15 minutes, 32 replies) and the ElevenLabs
  reachability (1 minute) are held per API process. A reply missing from that process's cache
  (another worker, a handover, eviction) is synthesised again, only while the call is live or two
  minutes after it ended, billed under its own key and limited to 60 replays in 10 minutes
  (decision 0022).
- **Clears it:** keep reply audio in the media bucket under a short lifecycle rule, so a cache miss
  never calls text to speech.

### Voice settings have no screen

- **What:** `voice.transport`, `voice.max_live_sessions` and `voice.voice_id` are `AppSetting` rows set
  in SQL (`docs/RUNBOOK.md`); `voice.max_live_sessions` defaults to 5, an assumption about the bought
  plan's concurrent-call limit.
- **Clears it:** a master-admin voice block in Settings, and the limit from the plan once bought.

### A hand-written multipart reader

- **What:** relay uploads are read by `api/multipart_form.py` rather than `python-multipart`.
- **Why left:** the lockfile cannot be regenerated on this machine (no `uv`), and one field is
  enough.
- **Clears it:** add `python-multipart` with `uv add` where `uv` runs and read the form with
  Starlette's limits.

## Voice UI (decision 0020)

### The voice dock has not run in a browser

- **What:** the dock, orb, microphone recording, speech playback and the ElevenLabs WebRTC call
  are checked by typecheck, lint and unit specs that drive `VoiceCall` with fakes; no browser has
  recorded, played or joined a LiveKit room, and the dock's layout above the bottom island, its
  contrast in both themes and the transcript at phone width are unverified. The `AGENT` path also
  assumes the server writes each turn to the transcript as it is spoken.
- **Clears it:** after lane 0017 deploys, a signed-in smoke spec with a fake microphone
  (`--use-fake-device-for-media-stream`) on `RELAY`, route fixtures from `shared/` at desktop and
  phone widths, then one real `AGENT` call once the spike passes.

### The dock asks for a bit rate it cannot enforce

- **What:** the relay recorder asks `MediaRecorder` for the session's `audioBitsPerSecond`
  (32 kbit/s) and sends a turn at nine tenths of `maxAudioBytes`; a browser that ignores the asked
  rate (Safari's AAC is the likely case, unverified) sends shorter turns than a minute.
- **Clears it:** measure the recorded rate per browser in the smoke spec; if one ignores it, raise
  that type's byte ceiling in the contract with its measured rate.

### Audio worklets need `blob:` scripts

- **What:** `@elevenlabs/client` loads its AudioWorklet processors from `blob:` and `data:` URLs.
  The CSP has no `script-src` yet, so they load; the strict CSP of PLAN 15 would block them.
- **Clears it:** copy `node_modules/@elevenlabs/client/worklets/*` into `public/` at build time
  and pass `workletPaths` from `lib/elevenLabsAgent.ts`, in the change that adds `script-src`.

## Media UI (decision 0021)

### Sharing waits for the governance lane

- **What:** the client draws Share, Withdraw and Stop sharing only when an asset carries
  `sharing` (`docs/contracts/media.md`, Sharing), which no backend sends, and calls
  `POST /api/media/assets/{id}/sharing`, which no route serves. A second professor cannot reach
  an asset awaiting sign-off, because a job is visible to its requester only.
- **Why left:** lane 0021 does not edit backend files; the contract gave the route to the
  governance lane.
- **Clears it:** the governance lane adds `sharing` to `MediaAssetView` for `SHARE_MEDIA` holders,
  serves the route with the rules of the contract, adds the second professor's queue, and adds a
  golden asset with `sharing` that both contract tests read.

### Shared illustrations reach other readers only through the cache

- **What:** a `CRAFT_SHARED` asset is shown to another reader only when they press Image on the
  same stage and the prompt hash matches; no route lists a craft's shared assets, so the stage
  does not show them on arrival.
- **Clears it:** a route listing the shared assets of a craft's stages (with fresh URLs), read
  by the media store and drawn by `components/craft/StageMedia.tsx` before the buttons.

### The client's wait limit restates backend constants

- **What:** `MEDIA_WAIT_LIMIT_SECONDS` (900, `frontend/lib/mediaView.ts`) is three attempts of
  `JOB_TIMEOUT_SECONDS` (240) plus a queue's wait; a change to the backend's timeout or retries
  does not move it.
- **Clears it:** a deadline on the job view (for example `giveUpAt`) that the client reads
  instead, with the contract, golden file and both tests.

### No style hint

- **What:** `MediaJobRequest.styleHint` is always sent as `null`; the UI has no field for it.
- **Clears it:** a short field on the stage's media row (filtered with the contract's banned
  words, refusals shown beside it) when the owner asks for one.

### Media UI not yet seen running

- **What:** the buttons, progress, figure, downloads and sharing steps are checked by typecheck,
  lint and unit specs that drive the store with fakes and test the rules on the golden files; no
  browser has drawn an asset, played a video, saved a blob from the bucket (its CORS allows
  `https://kalavigyan.vercel.app`) or loaded every page under the new `img-src` and `media-src`.
- **Clears it:** after lane 0018 deploys, a signed-in smoke spec with route fixtures from
  `shared/` at desktop and phone widths (press, progress, figure, download name), and a pass over
  every page with the CSP report in the console.

## Science engine (decision 0015)

### Reactions and readings cover three crafts

- **What:** the science seed has reactions and condition readings for Kutch Ajrakh, Bagh and
  Machilipatnam only; Bagru, Sanganeri and Akola stages get materials but no reactions or
  readings. Nothing proposes species for new claims (no researcher form, no enrichment step),
  so reactions grow only through `app/data/science_seed.json`. Kaolinite dehydroxylation has
  no reaction: the terracotta seed is sub-category mechanism chains, not a craft process with
  a `FIRE` stage. Stage concepts without an upstream ordinal (Akola mud soaking and paste
  preparation, Machilipatnam and Sanganeri block carving) get no stage, although `PRECEDES`
  edges could place them. No seed claim states a temperature or pH, so no seeded reading is
  checked against an envelope yet.
- **Why left:** each reaction and reading is curated against its quote; a model proposal path
  needs the review queue and a writer that calls `science/reactions.check_reaction`.
- **Clears it:** a writer for proposed species (researcher form and enrichment), balanced only
  through `check_reaction`; a terracotta craft process; ordering stages by `PRECEDES`.

### Out-of-envelope readings are not in a review queue

- **What:** the contract lists every `OUTSIDE` reading in the review queue; no review queue
  exists, so they are only shown with their status.
- **Clears it:** the review-queue lane lists readings whose `envelope_check` is `OUTSIDE`.

### Compound lookup is not scheduled

- **What:** `app/scripts/link_compounds` fills PubChem CIDs, properties and sources for seeded
  compounds, but no workflow runs it, so compounds show name and formula only.
- **Why left:** changing the deploy or a scheduled workflow was outside the lane.
- **Clears it:** run it after the seeds in Deploy backend or in the daily Coverage enrichment.

### The science seed never deletes

- **What:** science rows are upserted by derived id, so a reaction, condition or reading removed
  from `science_seed.json` stays in the database.
- **Clears it:** delete seeded science rows whose derived id is no longer in the plan, in the
  same transaction as the upsert.

### One kind and role per material

- **What:** a seeded material has one curated `MaterialKind` and one `MaterialRole` for every
  stage that uses it, and tools (`TOOL` concepts) are not stage materials.
- **Clears it:** take the role per stage from the source when a stage uses a material
  differently, and show tools once the contract has a place for them.

### Kaolinite constant differs from PLAN 7

- **What:** PLAN 7 gives kaolinite dehydroxylation as 450–600 °C; the cited revision says it
  begins at 550–600 °C, which is the constant.
- **Clears it:** cite a scholarly thermal-analysis source and set the constant to what it says.

## Answers in Indian languages (decision 0023)

### Translations are checked for figures, not for meaning

- **What:** `research/translation.translation_problems` proves that numbers, formulas, mhchem,
  units and the script survive a translation and that no link or personal data was added; it does
  not prove the sentence still says the same thing. A unit or number written in words in the
  target language fails the check and the sentence falls back to English.
- **Why left:** a meaning check needs a second model call per answer and a judge to calibrate.
- **Clears it:** run the known-answer questions of PLAN 0 in Hindi and Tamil on the box, have a
  speaker of each read the answers, and add a back-translation check if they find drift.

### Verified headings and follow-ups stay English

- **What:** a Verified answer in another language translates only its claim sentences; the
  section headings and the templated follow-ups are the app's English labels, and the
  not-enough-evidence message, errors and status lines are English in every mode.
- **Why left:** translating them would cost a model call on every Verified answer, including one
  whose claims are all cached; UI strings stay English.
- **Clears it:** keep translated labels per language as reviewed data (not model output) and send
  them with the stream.

### Multilingual answers not yet seen running

- **What:** the language picker, the Noto Sans faces, right-to-left Urdu and the English toggle are
  checked by typecheck, lint and unit specs; no browser has drawn them, and no TRANSLATE call has
  run against a provider. Migration 0007 seeds the TRANSLATE routes and has run only offline.
- **Why left:** nothing runs on the laptop; the batch deploys once.
- **Clears it:** after the deploy, ask one Hindi and one Urdu question in each mode and look at the
  answer on a phone and a laptop.

## Media backend (decision 0018)

### Gemini media behaviour not yet seen live

- **What:** how a safety block reads on the Interactions API, the image output type when none is
  asked for (PNG assumed), `DELETE /v1beta/interactions/{id}`, the clip's exact duration and the
  interaction id alphabet are unverified; the fixtures in `backend/tests/media/fixtures/` follow
  the documented shapes, not captured traffic.
- **Why left:** no paid call runs from the laptop and nothing is deployed yet.
- **Clears it:** after the deploy, make one image and one video, read the `UsageEvent` and the
  worker logs, replace the fixtures with the recorded answers (key-free) and adjust
  `providers/gemini_media.py` where the shapes differ.

### Video without the stage image as its first frame

- **What:** PLAN 11 allows the generated stage image as the only reference; videos are
  `text_to_video` only.
- **Why left:** it needs an S3 read and an image input in the request, which the first live runs
  should shape.
- **Clears it:** pass the requester's image asset of the same stage as an `image` input with
  `video_config.task` `image_to_video`, read through `services/object_store`.

### Community and caste names caught by group words only

- **What:** a claim, stage name or style hint is kept out of a prompt when it uses a group word in
  the singular or plural (`schemas/media.NAMED_GROUP_WORDS`, decision 0022); a community named
  without one (a surname or cluster name alone) still passes, and
  `depictsNamedCluster` compares only the craft's located place names.
- **Why left:** no register of community and caste names exists; PLAN 13a names them only from
  cited sources.
- **Clears it:** the governance lane keeps the named practitioners per craft as data; the claim
  set and the named-cluster flag check against it.

### The KalaVigyan token is not in the cross-portal naming document

- **What:** PLAN 14.3 adds `KalaVigyan` and its entities to
  `C:/dev/IIT/docs/conventions/NAMING_2026-10-18.md`; only this repository's helper and golden
  rows know them.
- **Why left:** that document is outside this repository and shared with both portals.
- **Clears it:** add the token, the `Generated-Image` and `Generated-Video` entities and the
  `Step-NN` sequence there at the portals' next release.

### India time is written again outside the backend package

- **What:** `core/clock.INDIA_TZ` is the backend's one home (decision 0022), but the geo ETL keeps
  its own `IST` offset for its run date (`etl/geo/geo_etl/__main__.py`) and `Craft`'s
  `recordedTimezone` default names `Asia/Kolkata` in the model, which may import nothing.
- **Clears it:** let the ETL import the backend's clock when it gains a dependency on the backend
  package, and move the model default into the migration that next touches the column.

### Media spend and units approximations

- **What:** a refund row counts on the day it is written, so a job failing after midnight IST
  returns a unit to the new day; the creation hold stops counting after 15 minutes
  (`RESERVATION_TTL`) while a job waits; `MediaJob.costUsd` holds the successful call only (failed
  and abandoned calls stay in `UsageEvent`); text and thinking tokens are priced at the media
  output rate, which overstates cost slightly.
- **Why left:** each is bounded and small next to the daily allowance and the monthly cap.
- **Clears it:** date refunds to their job's day, renew holds while queued, and price output by
  modality once the token breakdown is seen live.

### No signal that the worker is running

- **What:** the options route cannot tell whether `kv-worker` is up; if it is stopped, jobs queue
  and the client stops polling after 15 minutes.
- **Why left:** the watchdog covers the API only and the unit restarts itself.
- **Clears it:** a worker heartbeat (Redis or `AppSetting`) that options read, and the watchdog
  checking the unit.

## Admin role (decision 0024)

### The roster screen judges an entry by its own role

- **What:** `accessEntryOffers` (`frontend/lib/accessRoster.ts`) hides roster actions by the
  entry's `admitRole`; the server also refuses when the account at that address holds a role at
  or above the viewer's, so such a row can show an action that answers 403 with a sentence.
- **Why left:** the roster row does not carry the account's role, and adding it means a second
  query per page.
- **Clears it:** the roster list sends the actions the viewer may take on each row, computed with
  the same guards as the routes, and the screen draws exactly those.

### Sorting users by role follows the enum, not the rank

- **What:** `UserRole` lists `ADMIN` last (Postgres appends a new value), so
  `GET /users?sort=role` puts admins after students.
- **Why left:** the web client never sends that sort, and moving the value means recreating the
  type.
- **Clears it:** order that sort by `ROLE_RANK` with a `CASE` expression.

### A partial role-cap update drops the other roles to the student cap

- **What:** `PUT /settings/ai-budget` replaces the whole `roleDailyUsd` map; a role it leaves out
  falls back to the student's $0.50 in `providers/budget.evaluate` and shows no cap in
  `/usage/me`.
- **Why left:** older than the admin role; the master admin sends the whole map today.
- **Clears it:** merge the sent roles into the stored map, or refuse a map that does not name
  every role.

### Admin role not yet seen running

- **What:** migration 0009 has been rendered offline only; the admin DB tests
  (`backend/tests/db/test_admin_role_db.py`) run on GitHub Actions, and no browser has drawn the
  hub, Manage users or the roster as an admin.
- **Why left:** nothing runs on the laptop; the batch deploys once.
- **Clears it:** Backend checks green on the batch, then sign in as an admin after the deploy and
  walk the hub, Usage, Manage users and the roster.

## Yahoo sign-in (decision 0026)

### Yahoo sign-in not yet seen running

- **What:** migration 0010 has been rendered offline only; the Yahoo DB tests
  (`backend/tests/db/test_oidc_sign_in_db.py`) run on GitHub Actions, and no real Yahoo account
  has signed in: the token endpoint's acceptance of the secret in the form body and of the PKCE
  parameters is taken from DR, where it has run since 2026-10-10.
- **Why left:** the Yahoo app is not registered yet and nothing runs on the laptop.
- **Clears it:** register the app (`docs/RUNBOOK.md`, Yahoo sign-in), deploy, and sign in once
  with a rostered Yahoo address.

## First-password proof (decision 0028)

### A recovery code is offered for a first password but not taken

- **What:** the Settings card's two-step entry (`ChangePasswordCard.tsx`, `allowRecovery`) lets an
  account with two-step on type a recovery code before its first password, but
  `POST /auth/change-password` checks the code with `two_factor.step_up`, which takes only an
  authenticator code, so a recovery code is refused as a wrong code. DR accepts one there.
- **Why left:** older than decision 0028, and whether a recovery code may add a password is a
  security choice for the owner.
- **Clears it:** either check the first-password code with `check_second_factor(...,
  allow_recovery=True)` and answer its lock as 429, or drop `allowRecovery` from the card.

### First-password proof not yet seen running

- **What:** migration 0011 has been rendered offline only; the route tests
  (`backend/tests/db/test_first_password_db.py`) run on GitHub Actions, and no browser has added a
  password through the Google or Yahoo round trip.
- **Why left:** nothing runs on the laptop, and Yahoo is not registered yet.
- **Clears it:** Backend checks green on the batch, then after the deploy add a password in
  Settings from a Google-only account (and a Yahoo one once Yahoo is registered).

## Explainer contract (decision 0030)

### The answer stream re-exports the citation shapes

- **What:** `SourceRef`, `Citation` and `AnswerSentence` live in `research/citations.py`;
  `research/stream.py` re-exports them so `geo/`, `science/records.py`, `schemas/region.py`,
  `schemas/voice.py`, `services/craft_process.py`, `services/region_records.py` and two test
  helpers keep importing them from the stream: two import paths for one home.
- **Why left:** those files belong to other lanes working in the tree at the same time; the move
  was needed only to break the stream-to-explainer cycle.
- **Clears it:** switch each importer to `research.citations` when it is next touched, then drop
  the three names from `stream.__all__`.

### Declared block kinds check only what `research` can see

- **What:** the later kinds' models refuse what `research` can check (uncited blocks, orders,
  coordinates without Wikidata, personal data in artisan quotes), but not rules that live in
  `schemas/`: a region story's or map layer's `boundaryCaption` is not compared with
  `schemas.region.BOUNDARY_CAPTION`, and a reaction step's equation not rebuilt with
  `schemas.science.mhchem_equation`. The simulation's static check (plan 2.6) does not exist.
- **Why left:** `research` may not import `schemas`, and those kinds are built in phases B and C.
- **Clears it:** the phase that builds each kind checks it in its producer and adds a contract
  test; moving `BOUNDARY_CAPTION` into `research` would let the model check it.

## Understanding and depth (decision 0031)

### Comparison questions answer for one craft

- **What:** the understanding step chooses at most one craft; a second craft a comparison
  question names is only offered, so `understood.crafts` never holds two and the answer covers the
  first craft.
- **Why left:** researching and composing two crafts side by side is the `compare` block of phase
  D.
- **Clears it:** phase D lets the understanding choose several crafts for a comparison and runs
  research per craft into a `compare` block.

### Any-craft claims are read only by any-craft questions

- **What:** research for any craft writes its claims on shared concepts (no craft, no
  sub-category). A later question about a particular craft does not read them, because the craft
  scope reads the craft's and its family's concepts only.
- **Why left:** which shared findings apply to which craft is a curation choice; reading all of
  them in every craft answer would mix crafts.
- **Clears it:** link shared concepts to the crafts they concern (through the concept graph of
  feature 7 or a reviewer's link), and let the craft scope read linked shared concepts.

### The answer cap follows the asked depth

- **What:** `AnswerSpend` is made for the depth the reader asked for; when the understanding step
  degrades Expert to Detailed past the degrade mark, the answer is still held to Expert's cap.
- **Why left:** the pipeline is built before the understanding runs; a degraded answer plans
  Hybrid and spends less anyway.
- **Clears it:** let the understanding step set the effective depth on the answer's
  `AnswerSpend` before research starts.

### A hold is not released when a call raises something unexpected

- **What:** the router releases an answer's hold on every provider failure, but an exception
  outside `ProviderError` (a bug, a cancellation) leaves the estimate held, so that answer has
  less room under its cap; the `UsageEvent` stays `RESERVED` and stops counting after the
  15-minute reservation window, as before.
- **Why left:** the call loop of `router.run` (181 lines, in the baseline) needs splitting before
  a `finally` can be added cleanly.
- **Clears it:** split `router.run` into reserve, call and settle steps and release the hold in a
  `finally`.

### Retired stream vocabulary still listed

- **What:** the answering flow no longer sends the `RESOLVING` status or the `match`, `section`
  and `sentence` events; all four stay in `research/stream.py` (and `RESOLVING` in the client's
  `lib/answerShapes.answerStatusShape`) for the contract golden `shared/answer-stream.golden.sse`,
  which only the backend reads now that the web client reads the explainer stream (decision 0037).
- **Why left:** dead vocabulary, harmless to readers; removing it rewrites the golden and its
  tests, outside the review fixes of 0038.
- **Clears it:** drop `RESOLVING`, `match`, `section`, `sentence` and their golden from
  `research/stream.py` and `answerStatusShape`.

### Per-answer caps are starting values, edited only through the API

- **What:** `AI_ANSWER_CAP_USD` starts at $0.25 Basic, $0.50 Detailed and $1.00 Expert, set
  before any Expert answer was measured; the Settings hub has no AI budget screen, so a Master
  Admin changes the caps (like the ceilings) only through `PUT /settings/ai-budget`.
- **Why left:** owner O3: start modest and raise once phase A measures real costs; the budget
  screen was never built.
- **Clears it:** after the first Expert answers in production, set the caps from their measured
  spend (Usage, by request id), and add the AI budget to the Settings hub.

### The understanding call shares the PLAN route

- **What:** the understanding call runs on the `PLAN` route, so Usage counts it as planning and
  the Settings hub cannot route it apart from the plan call.
- **Why left:** the `PLAN` route is already "Plan and craft choice" with Gemini Flash Lite first,
  as the plan asks; a separate task needs an `AiTask` value, a migration and its routes.
- **Clears it:** add an `UNDERSTAND` task if the owner wants it routed or reported apart.

## Asking screen (decision 0036)

### Dictation languages not yet tried on each browser

- **What:** the plan (2.5) asks for each answer language to be checked on each target browser
  before it is offered. The screen offers dictation in all 13 answer languages (`<code>-IN`
  locales, `lib/dictation.ts`) wherever the browser has the Web Speech API, hides a language the
  browser reports unavailable (`SpeechRecognition.available`) or refuses
  (`language-not-supported`), but nobody has yet dictated in Odia, Punjabi, Assamese or Urdu on
  Chrome, Edge and Safari, or checked Android Chrome's continuous mode, which is known to repeat
  final words.
- **Why left:** nothing runs on the laptop, and the production E2E drives a headless browser with
  no microphone.
- **Clears it:** after the deploy, dictate one sentence per language on Chrome, Edge and Safari
  (desktop and Android Chrome) and record what each does here; switch Android Chrome to
  single-utterance mode if its repeats show.

## Pictures and terms (decision 0034)

### Relevance is by text only

- **What:** plan 2.7 asks for one cheap vision call on the top candidates; every picture is
  chosen by its words against the claim text (`relevance: TEXT`), so a picture whose title and
  description happen to share two words with a claim is shown even if it depicts something else.
- **Why left:** the vision call needs an image route and per-answer spend; text relevance came
  first.
- **Clears it:** a `CAPTION` route call on the top two candidates per section, recorded as
  `VISION` on `MediaRefClaim`, dropping a picture the model says does not show the claim.

### Link cards need the page's own site to serve the picture

- **What:** a SearXNG image result is kept only when its image and page share a registrable name
  (`research/images.same_site`), judged by a short list of second-level labels (`ac`, `co`,
  `gov`, `org`, ...) instead of the Public Suffix List. Sites that serve pictures from a CDN on
  another name are left out, and a public suffix outside the list could pair two unrelated sites.
- **Why left:** owner O2 asks for the thumbnail from the source site; no dependency carries the
  Public Suffix List today.
- **Clears it:** vendor the Public Suffix List (or `tldextract` with a pinned snapshot) and use it
  in `site_of`.

### Brave image results are not used

- **What:** web image results come from SearXNG only; plan section 7 names Brave for image results
  too, and the Brave key already backs web search.
- **Why left:** one image search per service was enough for phase A.
- **Clears it:** an `images` method on `BraveAdapter` (`/res/v1/images/search`) used when SearXNG
  answers fewer than two link cards.

### Local words without a stated meaning are not terms

- **What:** the glossary takes a seed concept's local word only when the concept's name states
  what it means (`Kut (iron-water black paste)`, `Alum (fatakdi)`). Local words listed beside
  other names (`lokhand`, `gud`, `datla`, `mavi`, `gudh`) are not terms, and two spellings of
  one word become one term only when they are at least 80 % alike (`harde`, `harda`).
- **Why left:** the seed records those words without their meaning, and a guessed meaning would
  be an uncited fact.
- **Clears it:** a curated `localTerms` meaning in `etl/crafts` (or claims that define them), then
  the glossary plan reads it.

### The glossary seed never removes a term or link

- **What:** `seed_terms` upserts terms by key and adds craft and concept links; a term or link
  that a later seed no longer produces stays.
- **Why left:** the claim and science seeds behave the same way (see "The science seed never
  deletes"); no removal has been needed yet.
- **Clears it:** a seed step that deletes links the plan no longer has, and terms with no links
  and no cached summary.

### Term summaries and pictures written back are not embedded at once

- **What:** claims and sources kept by a term summary are stored without vectors; they get them
  from `app/scripts/embed_knowledge` (run by the daily Coverage enrichment workflow), so up to a
  day passes before semantic retrieval finds them.
- **Why left:** the term route has no embedder in its request path and the summary is already
  cached for the reader.
- **Clears it:** pass `router_embedder(principal)` into `SqlTermStore` and call `embed_written`
  after the write-back, as `store_live_research` does.

### Term summaries never expire while their claims stand

- **What:** a cached `TermSummary` is served until a claim it rests on is hidden, retracted or
  rejected; a better stored claim, or a newer Wikipedia revision, does not replace it.
- **Why left:** plan 2.8 asks for a cache per term and language; claim visibility is the guard
  that matters for accuracy.
- **Clears it:** an age limit (or a stored claim newer than `checkedAt`) after which the next tap
  builds the summary again.

### Image and term enums are check constraints

- **What:** `MediaRef.display`, `MediaRefClaim.relevance` and `TermSummary.basis` are strings with
  `CHECK` constraints built from `models/enums.py`, not Postgres enum types like the other
  vocabularies.
- **Why left:** the schema tests only know enum types the first migration declares, and lanes
  adding tables in the same batch would each have had to change that test machinery.
- **Clears it:** once the tests accept enum types created by later migrations, turn the three
  columns into `pg_enum` types in one migration.

## Pictures and terms in the stream (decision 0039)

### Translated sentences lose the spans the translation rewrites

- **What:** a translated sentence keeps a span only where the English span's text survives
  (`research/terms.spans_still_shown`). A term the translation renders in its own script (alum as
  फिटकरी) is not underlined, although the glossary may hold that local name.
- **Why left:** marking translated text needs word boundaries that hold in Indian scripts (their
  vowel signs are not word characters to Python's `re`) and a check that the local name is the
  translation's word for that term.
- **Clears it:** after translation, mark the glossary's local names in the answer's script with
  grapheme-aware boundaries, next to the spans kept, and check them like English spans.

### Reused sections search for pictures again

- **What:** each reuse of a stored section searches the image services anew, although the
  pictures chosen for the same claims are already stored as `MediaRef` rows with `MediaRefClaim`
  links.
- **Why left:** reading stored pictures needs a lookup by claim and a rule for when a stored
  picture is still current; a search costs no AI spend and is bounded by the 8 s wait.
- **Clears it:** read the `MediaRefClaim` rows of the cited claims first and search only when none
  are stored.

### The stored-only answer shows no pictures or terms

- **What:** when spend is refused, `services/stored_explainer` streams prose blocks with no spans
  and no `images` block.
- **Why left:** step 7 was wired into the sectioned flow; the stored-only answer is its fallback.
- **Clears it:** pass the answer's `Enrichment` to `stream_stored_answer` and mark and search as
  the sectioned flow does.

### The nightly rebuild searches pictures nobody sees

- **What:** `app/scripts/rebuild_pieces` answers through `build_answer_pipeline`, so each rebuilt
  section also searches pictures and stores them as `MediaRef` rows, though its stream is
  discarded.
- **Why left:** the rebuild needs the same term marking so its pieces carry spans; pictures cost
  no AI spend and stored ones serve the craft page later.
- **Clears it:** build the rebuild's pipeline with enrichment tools whose picture step answers
  nothing.

### Pictures and terms in the stream not yet seen running

- **What:** production answers stream pictures (each researched or reused section of the Kutch
  Ajrakh known-answer questions carried an `images` block on 2026-11-17); no browser has yet shown
  the credits, the underlined terms or the term sheet.
- **Why left:** nothing runs on the laptop.
- **Clears it:** after the deploy, load `/ask`, ask the Kutch Ajrakh known-answer questions and
  see each section's pictures with their credits and underlined terms that open their summary.

## Explainer view (decision 0037)

### Listen re-renders every sentence on each time update

- **What:** the word being read travels through the reading context, so each `timeupdate`
  (about four a second) re-renders every sentence of the explainer.
- **Why left:** not measured as slow on an Expert answer; memoising every sentence first would be
  a guess.
- **Clears it:** measure on a long answer on a phone; if it drops frames, give each sentence a
  selector on the mark (only the sentence being read re-renders).

### The understood line finds its controls by id

- **What:** a part of the understood line moves focus to its control under the question box
  through element ids (`components/ask/AskOptions.focusAskOption`), not refs.
- **Why left:** the controls live in the asking screen's components and the explainer only needs
  to hand focus over; threading refs through both trees for one focus call was heavier.
- **Clears it:** if the asking screen gains a focus API (refs from `useAskScreen`), call it
  instead.

## Listen and the switched-off call (decision 0035)

### Narration not yet heard from ElevenLabs

- **What:** `ElevenLabs.narration` follows the documented `/with-timestamps` shape; no request has
  reached ElevenLabs, so `eleven_v4` on that endpoint, the alignment spelling the text in every
  language, bracketed text read as text rather than as a v4 audio tag, and the real speaking rate
  behind the 1,000-characters-a-minute hold are unverified (decision 0035, Unverified).
- **Why left:** no provider call with a real key from the laptop; nothing is deployed by agents.
- **Clears it:** after the deploy, press Listen on one English and one Hindi Kutch Ajrakh answer;
  if `eleven_v4` is refused, set `NARRATION_MODEL` to `eleven_v4_turbo`; replace the fixture
  with the recorded answer.

### Two readers missing the same block both pay for it

- **What:** the narration cache is checked, then filled; two requests that miss the same block at
  the same moment both synthesise it and both are billed (the second write wins, both are valid).
- **Why left:** rare until many readers open the same new answer at once; a lock across processes
  needs a table or a lease.
- **Clears it:** an in-flight lease per cache id (a row with a short expiry, or an S3 conditional
  put with `If-None-Match`) so the second request waits for the first.

### Narration objects never age out

- **What:** `media/narration/<cacheId>/` objects stay forever; a block that changes (a claim
  retracted, a translation corrected) gets a new cache id and the old audio is orphaned.
- **Why left:** the bucket lifecycle is Terraform, which agents do not change; the cost is small.
- **Clears it:** a lifecycle rule expiring `media/narration/` objects not read for a year, or a
  sweep of cache ids no stored explainer or piece names.

### Listen has no fallback voice

- **What:** PLAN 10.6 reads aloud with the Gemini voice when ElevenLabs is down; Listen is hidden
  instead (`listen.languages` empty), because the Gemini voice gives no word timings.
- **Why left:** highlighting needs timings; a fallback without them is a second Listen.
- **Clears it:** a Gemini read-aloud that highlights by sentence only, if the owner wants Listen
  while ElevenLabs is down.

### The Listen route repeats the throttle shape

- **What:** `api/routes/listen.throttle` repeats the `Retry-After` arithmetic of the other route
  throttles (`terms`, `knowledge`, `voice`, `auth`, `password_change`).
- **Why left:** those routes belong to other lanes working in the tree at the same time.
- **Clears it:** one `core/rate_limit.refused(attempt, detail)` that raises the 429 with its
  `Retry-After`, used by every route.

## Sectioned composition (decision 0032)

### Sections share the depth's budget evenly

- **What:** `split_share` gives every section the same part of the depth's queries and documents
  (Basic: 2 queries over 3 or 4 sections), whether or not its stored claims already cover it; a
  section without a query share reaches live research only through the fresh retry, and only
  while the ledger has something left.
- **Why left:** which fields need live research is known only after each section's plan call.
- **Clears it:** plan every section first, then hand the budget to the sections with open facets.

### Two sections can read the same document

- **What:** each section runs its own planner and `DocumentReader`; the adapters cache searches
  for 600 s but not reads, so a paper found by two fields is fetched twice.
- **Why left:** a shared reader needs a per-answer cache passed through the planner.
- **Clears it:** one per-answer read cache (by evidence id) held by the answering service.

### A late failure drops the whole prose block

- **What:** a prose block is refused whole when one sentence has no stored citation after the
  write-back (for example a write-back skipped as invalid), although its other sentences passed;
  the model's one regenerate covers only what the composer's checks see.
- **Why left:** plan 2.1 drops a block with an uncited fact; such skips should be rare.
- **Clears it:** count refused blocks by reason in production; if they occur, regenerate the
  section once with the refused sentences named.

### Section titles and progress counts are generic

- **What:** a section's title is its field's label ("The chemistry"), not one written for the
  question; the `status` line's counts are the first section's to reach each step.
- **Why left:** `section_started` goes out before anything is composed and has no later title
  event; per-section progress is carried by `section_state`.
- **Clears it:** a title from the understanding call (validated like a heading), and a status
  line that sums the sections' counts.

### Schema counts are prompt lines

- **What:** with portable schemas, the whole-answer composer's six sections, the voice turn's one
  section of three sentences and the translation's length limit are no longer enforced by the
  schema; the section composer and the planner trim on our side, the voice turn and the coverage
  job's whole-answer composer do not.
- **Why left:** the voice call is switched off and the coverage job only writes claims.
- **Clears it:** trim in `parsed_answer` to its form's limits (sections, sentences, follow-ups).

### Stored plans and the explainer are not read back yet

- **What:** `Answer.plan` holds one plan per section and attempt and `Answer.mode` the first
  section's mode; the data migration wrapping older plans has no database test of an old row.
  The explainer is stored as the reader saw it (translated), not in English.
- **Why left:** nothing reads them yet besides Listen, which wants the shown language.
- **Clears it:** a DB test that seeds a pre-0014 plan and runs the upgrade, when a reader of
  `Answer.plan` is written.

## Stored knowledge pieces (decision 0033)

### Topic keys match only the same glossary terms

- **What:** a facet's topic is the glossary terms the question names (else the place or the
  craft), so "Why does alum fix alizarin?" and "How do alum and alizarin bond?" meet, but a
  rephrasing that names one more or one fewer term researches again; a question in an Indian
  script matches only the glossary's local names, so it falls back to the craft's topic.
- **Why left:** accuracy over speed; a model-chosen topic would be another model output to check,
  and rendering every question in English costs a TRANSLATE call before any reuse.
- **Clears it:** measure reuse in production; if near misses are common, add the planner's facet
  targets to the stored piece and accept a stored set whose terms are a subset of the question's
  when its vector is near the question's.

### Answers never grow the Process tab

- **What:** plan 2.2 wants process stages found by answers to land in the science tables, so the
  craft page's Process tab and later ladders use them. No answer writes `Process` or
  `ProcessStage` rows: stage concepts a `PROCESS` section cites stay concepts (their claims still
  appear in prose). Lane 0033 made the cited stages the process of a craft with none, numbered in
  the order the model wrote its sentences; decision 0038 removed that, since step numbers and
  order would have come from the model, not from a source.
- **Why left:** no source-stated order exists to build from: the write-back records claims on
  stage concepts, not which stage follows which.
- **Clears it:** a cited-order route: write `PRECEDES` edges between stage concepts only from
  claims that state the sequence, with their citations; create a live process only when those
  edges order every stage, taking ordinals from the edges; take stage names only from curated or
  seeded concepts, never from a planner's facet targets; or a professor places the stages from
  the review screen.

### A rebuild that composes nothing is tried every night

- **What:** a stale piece whose rebuild shows no block stays stale and unsuperseded, so the
  nightly job tries it again each night (within the budget, most-asked crafts first).
- **Why left:** a retracted claim usually leaves its topic answerable; a topic that cannot be is
  rare and bounded by the daily budget.
- **Clears it:** record each rebuild attempt on the piece and skip one tried in the last week.

### The rebuild may overshoot the day by one answer

- **What:** the rebuild checks the day's remaining budget before each group (at least
  `ENRICHMENT_QUESTION_RESERVE_USD`), and one Expert group can spend up to the Expert per-answer
  cap, above the reserve.
- **Why left:** the coverage job has the same shape; the cap bounds the overshoot.
- **Clears it:** hold each rebuild to the smaller of its depth's cap and what the day has left.
