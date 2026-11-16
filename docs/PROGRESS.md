# Progress

Where work stands and what comes next. Update it in the same change that finishes or starts a
piece of work. The plan is `docs/PLAN.md` (section 0 overrides the rest); the build order is its
section 17.

Last updated: 2026-11-16.

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
  `app/scripts/embed_craft_descriptors.py`, which no workflow runs yet (`docs/TECH_DEBT.md`).

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

## Next

1. Run one or two known-answer questions in `HYBRID` on the box once deployed (PLAN section 0),
   and clear the answer stream gaps in `docs/TECH_DEBT.md` (keep the write-back when the
   learner leaves, answer and trace rows, researcher chunk access).
2. **Day 3:** the craft page and the region panel; the `WEB_READ` reader for long documents.
3. Clear debt as files are touched (`docs/TECH_DEBT.md`), lowering the hygiene baseline.

## Waiting on the owner

- Free OpenAlex, Semantic Scholar and Springer Nature API keys (Settings, API keys); without
  them OpenAlex shares a small daily allowance per IP, Semantic Scholar's shared pool answers
  429 often, and Springer Nature stays off. An Elsevier institution token lets Elsevier return
  abstracts.

- The designer and documentation portals' next batched release: add
  `GET /api/cross-portal/peer/crafts` (`docs/contracts/portal-craft-feed.md`) and set
  `CROSS_PORTAL_CRAFT_FEED_ENABLED=true` on both, then run **Craft sync** once.

- Cloudflare Turnstile widget for `kalavigyan.vercel.app` (email sign-up is Google-only in
  production until then).
