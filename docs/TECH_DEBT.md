# Technical debt register

What is knowingly below standard, why it was left, and what clears it. Add an entry in the same
change that takes the shortcut; delete it in the change that clears it.

Last reviewed: 2026-11-16.

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

- **What:** recorded in `tools/hygiene_baseline.json` on 2026-11-16: 14 files over 400 lines, 55
  functions over 40 lines, 9 functions with more than 5 positional parameters. The largest files:
  `backend/migrations/versions/0001_initial_schema.py` (2853), `etl/crafts/wikidata_link.py`
  (1121), `backend/app/api/routes/auth.py` (784), `backend/app/services/two_factor.py` (703),
  `etl/crafts/seed_claims.py` (642), `backend/app/providers/router.py` (566),
  `backend/app/models/knowledge.py` (553), `etl/crafts/aliases.py` (543),
  `backend/tests/db/test_db_flows.py` (524), `backend/app/services/knowledge_view.py` (502),
  `backend/app/services/managed_secrets.py` (496), `backend/app/services/ai_providers.py` (454),
  `backend/app/data/craft_master_loader.py` (433), `backend/app/api/routes/access.py` (414).
- **Why left:** most were ported from the designer portal with the same shapes so the portals
  stay mergeable; splitting them is a separate restructuring change.
- **Clears it:** split along responsibilities when a file is next changed; run
  `tools/hygiene_check.py --update-baseline` after each clean-up. The initial migration stays
  one file (migrations are not rewritten).

### Answer stream: gaps left on 2026-11-16 (decision 0012)

- **What:** (1) A client that disconnects cancels the answer, including a write-back in
  progress (its transaction rolls back), so research already paid for can be lost.
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
- **Clears it:** shield the keep step from cancellation (or hand it to a background task);
  write the answer rows and trace from the events already produced, with spend from the
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

### Portals do not serve the craft feed yet

- **What:** the craft sync (`app/scripts/sync_portal_crafts.py`, decision 0003) reads
  `GET /api/cross-portal/peer/crafts` from the designer and documentation portals, and neither
  serves it. Every run reports `not_found` for both portals and changes nothing: each deploy
  prints a warning after the seeds, and the daily **Craft sync** workflow fails. Only the 455
  master crafts are present until then.
- **Why left:** KalaVigyan may not edit the portal repositories; the route is specified in
  `docs/contracts/portal-craft-feed.md` for the portals' next batched release.
- **Clears it:** both portals ship the route with `CROSS_PORTAL_CRAFT_FEED_ENABLED=true` (GitHub
  secret and box `.env` on each), then run **Craft sync** once by hand and read its report.

### Craft descriptor embeddings are not filled

- **What:** semantic craft matching (decision 0004) needs `Craft.descriptorEmbedding`, and no
  workflow runs `app/scripts/embed_craft_descriptors.py`. Until it runs, the resolver uses
  exact, fuzzy, family and region signals only. It also fills only missing vectors, so a craft
  whose aliases change later (portal sync, enrichment) keeps its old vector.
- **Why left:** the script calls the paid embedding route and changing the deploy or a scheduled
  workflow is the infrastructure lane's change, batched with the next release.
- **Clears it:** run it after the seeds and the craft sync in Deploy backend and in the daily
  Craft sync, and store a hash of `descriptor_text` per craft so a changed descriptor is
  embedded again.

### Craft matching has no evaluation set

- **What:** PLAN 5.2's gate (300 match cases, top-1 at least 95%, in CI on seeded fixtures) does
  not exist. The resolver's weights, `FUZZY_MIN_SIMILARITY` 0.85, `SEMANTIC_MIN_SIMILARITY` 0.6
  and the hand list `GENERIC_TOKENS` were set from about 30 questions tried by hand against the
  master list (decision 0004). The model choice among the top 5 (PLAN 5.2 step 6,
  `MODEL_CHOICE`) is not built; a learner picks from the pills instead.
- **Why left:** the cases have to be written from real questions in several scripts; owner
  direction is 1-2 known-answer checks at a time, not a large suite on every change.
- **Clears it:** collect the cases as answers are corrected, run them in Backend checks, tune the
  constants against them, and add the model choice if top-1 stays below the gate.

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
  - Wikidata and Commons fetches render in English only; `fetch` takes no language, so a Hindi
    question cites English labels and descriptions.
  - Wikidata time values coarser than a year (decade, century) are left out of the item text,
    and the Commons `published` date is empty unless the original date is ISO.
  - PubChem hazards keep at most three reporting sources; the ECHA terms allow non-commercial
    reuse only, which suits the IIT research use but would need review for any commercial use.
  - Commons media use `SourceKind` `OTHER`: the enum has no image or media kind.
  - `WIKIPEDIA_LANGUAGES` is English and Indian languages only; a learner writing in another
    language gets `InvalidInput` from the Wikipedia adapter.
- **Why left:** no caller yet decides the language of a fetch or needs other wikis; a media
  source kind needs a migration of the `SourceKind` enum.
- **Clears it:** pass the answer language through to `fetch` (the answering service has it); add a `MEDIA` source kind with its migration when the media lane stores Commons files;
  widen the language list when the planner asks for it.

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
  vector. (5) Full-text ranking reads Latin-script words only; a question in an Indic script is
  ranked by the vector alone. (6) The HNSW indexes on `Claim.embedding` and `Chunk.embedding`
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
  failed, not every searcher asked. (5) A sentence in a language that writes numbers in its own
  digits fails the figure check unless its quote has the same digits; the prompt asks for 0-9.
- **Why left:** the reader and the answering service are separate lanes; chunk citations and
  claim sources need the stream and retrieval contracts to grow together.
- **Clears it:** the reader fills quotes for long documents; the answering service builds
  `compose_request` from the pack, joins each claim's sources and quotes from the database into
  its candidate, and records which searchers ran in the pack; add a chunk candidate kind with a
  source-only citation when the stream allows one; fold Indic digits in `figures_in`.

## Live research write-back (decision 0011)

### The quote overlap assumes one language (decision 0013)

- **What:** `UNRELATED_QUOTE` compares the sentence's content words with its quotes' words, so
  an answer written in another language than its sources would fail every sentence
  (`backend/app/research/quotes.py`, `quote_overlap`). The stop list and the four-letter stem
  are English.
- **Why left:** English is the only answer language (`ANSWER_LANGUAGES`).
- **Clears it:** before a second answer language is offered, compare against a translation of
  the quotes or skip the overlap for that language with a recorded decision.

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

