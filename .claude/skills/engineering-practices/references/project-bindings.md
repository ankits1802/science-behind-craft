# Project bindings

The only project-specific file of the three practice skills (`engineering-practices`,
`backend-practices`, `frontend-practices`). The rules live in the skills and do not change with
the project; the facts below do. Review this file whenever the layout, tooling or commands
change, and update the date.

Last reviewed: 2026-11-17.

## What this repository is

KalaVigyan (`science-behind-craft`): a web research platform on Indian crafts and the science
behind them. A learner asks about a craft; the platform resolves the craft, shows its region on
the India map with the region's environment, and answers with sentences that each cite stored
claims and their sources. The knowledge base grows: when stored claims cannot answer, live
research runs and what it finds is written back as cited claims. The plan is `docs/PLAN.md`;
its section 0 (owner direction) overrides everything else in it. Web only, no Android client.

## Layout and layers

```
backend/app/core/        shared layer: settings, database sessions, security, roles, logging,
                         rate limits, request dependencies
backend/app/models/      SQLAlchemy models (DR's Prisma naming: PascalCase tables, camelCase columns)
backend/app/data/        vendored datasets and their pure loaders (craft master list, aliases,
                         LGD register, seed claims, craft text normalisation)
backend/app/research/    research and answering contracts: typed models, protocols and
                         rules shared by the resolver, planner, source adapters, fetcher,
                         composer, claim writer and answer stream (docs/contracts/research.md),
                         and the explainer: document, blocks, terms, images, stored pieces,
                         depth by role (docs/contracts/explainer.md, decision 0030); dataset
                         rows, rivers, month and season words, reaction rules and the expert
                         panel (decision 0042)
backend/app/curation/    curated craft dossiers: the Pydantic model, the offline rules, the
                         check file and the index, shared by tools/curation and the importer
                         (docs/contracts/curation.md, decision 0051)
backend/app/sources/     adapters for external research sources: shared paced HTTP, record
                         rules and the adapter skeleton; sources/scholarly/ has one module per
                         scholarly service and the registry (decision 0005); sources/reference/
                         the Wikipedia, Wikidata, PubChem and Commons adapters (decision 0006);
                         sources/web/ the SearXNG and Brave adapters and their fallback, and
                         sources/fetcher_client.py the client of the fetcher (decision 0007);
                         sources/images/ the Openverse adapter and the image sources
                         (Commons, Openverse, SearXNG pictures; decision 0034)
backend/app/fetcher/     the separate fetcher process (python -m app.fetcher, kv-fetcher): no
                         database, no AWS, no API settings (decision 0007)
backend/app/planner/     the planner and tiered live research: plan call, facet coverage,
                         parallel search, dedupe, reading, references, evidence pack
                         (decision 0009); the understanding step before it (decision 0031)
backend/app/composer/    the composer: evidence pack to candidates, the COMPOSE call, the
                         post-checks, one regenerate, the not-enough-evidence answer
                         (decision 0010)
backend/app/retrieval/   stored-knowledge retrieval (T1 claims, T2 chunks): scope and ranking SQL,
                         reciprocal rank fusion, chunking, embedding fill (decision 0008)
backend/app/schemas/     pydantic request and response bodies, and the science, region, voice
                         and media contracts (decision 0014)
backend/app/science/     the science engine: formulas, balancing (sympy), units (pint), stage
                         envelopes and the process view built from stored rows (decision 0015)
backend/app/geo/         the region profile and map layers: places, state aggregates, facets,
                         the layer registry and its classes, built from stored rows (decision 0016)
backend/app/voice/       voice calls: sessions and their binding, the custom-LLM turn, relay turns,
                         the encrypted transcript, daily upkeep, agent provisioning (decision 0017;
                         switched off by VOICE_CALL_ENABLED, decision 0035); Listen: narration of
                         finished explainers with word timings and its cache (decision 0035)
backend/app/media/       stage illustrations and clips: claim set, prompt, bundle, MP4 and PNG
                         checks, the job routes' steps, the worker queue and its SQL (decision 0018)
backend/app/worker.py    the kv-worker process (python -m app.worker): the media queue
backend/app/services/    domain services: crafts, knowledge, access, credentials, keys, routing
backend/app/providers/   model-provider adapters (and the one ElevenLabs adapter), the AI router,
                         the budget rules and the quota ledger
backend/app/api/         entry points: router.py and api/routes/<area>.py (thin handlers)
backend/app/scripts/     entry points: seed commands run by the deploy (seed_crafts, seed_claims
                         with the science seed and the term glossary, seed_districts,
                         seed_admin) and the portal craft sync
                         (sync_portal_crafts, also run daily), embed_craft_descriptors,
                         embed_knowledge, the daily coverage enrichment (enrich_coverage),
                         the nightly rebuild of stale knowledge pieces (rebuild_pieces),
                         the PubChem compound lookup (link_compounds), the daily voice upkeep
                         (voice_upkeep), the voice agent's provisioning (provision_voice_agent)
                         and the E2E account's provisioning (provision_e2e_account); shared
                         operator input in operator_input
backend/app/main.py      the ASGI app
backend/migrations/      Alembic migrations
backend/tests/           DB-free tests; backend/tests/db/ needs Postgres (marker `db`)
etl/crafts/              craft data pipeline (aliases, Wikidata links, seed claims); imports
                         backend/app/data as its shared home
etl/geo/                 per-district environment statistics from open datasets (package geo_etl),
                         and HydroRIVERS river lines with one TopoJSON per basin (decision 0043)
frontend/                Next.js App Router web client (npm)
infra/                   Terraform, deploy scripts and systemd units, secret seeding, Supabase lockdown
shared/                  files both sides check (craft-master.sha1, the *.golden.* contract files)
tools/                   developer tooling: the hygiene check, the curation tools (fetch, verify,
                         check, schema; tools/curation) and their tests
docs/                    living documents, contracts, decisions
```

Imports in `backend/app` point one way. The allowed edges, enforced by `tools/hygiene/layers.py`
(`LAYER_IMPORTS`), are:

```
main      -> api, voice, providers, services, core, models
api       -> voice, media, providers, services, science, geo, retrieval, research, schemas, core, models, data
scripts   -> voice, providers, services, planner, composer, retrieval, research, core, models, data
voice     -> providers, services, composer, schemas, research, core, models
media     -> providers, services, schemas, research, core, models
worker    -> media, core
providers -> services, research, core, models
services  -> science, geo, planner, composer, retrieval, sources, research, core, models, data
planner   -> sources, research, core, models
composer  -> research, core, models
retrieval -> research, core, models
sources   -> research, core, models
fetcher   -> sources, research, core
curation  -> research, models, data
research  -> core, models
science   -> schemas, research, core
geo       -> schemas, research, core
schemas   -> research, core
core      -> models
models    -> (nothing else)
data      -> (nothing else)
```

Nothing imports `api`, `scripts` or `main` except the layers above them. A new package under
`backend/app` fails the check until it is added to `LAYER_IMPORTS` and to this list. The plan's
later packages (`websearch/`, `evidence/`,
`enrichment/`, `review/`, `governance/`) each get a row when they are created; those that build
on the research contracts list `research` among their allowed imports.

Frontend source (`frontend/`), as it is today:

```
app/                       routes: (protected)/ for signed-in screens, login, signup, privacy...
app/api/                   Next route handlers that proxy auth and session calls to the API
components/ui/             generic kit, no domain knowledge
components/<area>/         domain components grouped by area: answer, ask, craft, map, admin,
                           settings, auth, nav, voice, data, dialogs, forms, guide, hooks...
components/*.tsx           app-wide shell pieces (AppShell, providers, PageHeader, ErrorPanel...)
lib/                       the API client (api.ts), session, formatters, permissions, types,
                           the runtime shape kit (shape.ts) and the contract shapes (*Contract.ts)
lib/server/                server-only code (apiProxy.ts)
e2e/                       Playwright: *-unit.spec.ts (unit project) and smoke.spec.ts
e2e/production/            the E2E production run (decision 0029): projects exist only with
                           E2E_PRODUCTION=1, never in Frontend checks
public/, fonts/            static assets
```

`lib/api.ts` is the one API client; components and hooks call it. The frontend has no
`features/` folder: domain components live under `components/<area>/`, and a component used by
two areas belongs in `components/` or `components/ui/`, never copied.

Versions: the latest stable release of every dependency (owner rule), pinned in `backend/uv.lock`
and `frontend/package-lock.json`. When a version lags, upgrade the lagging side; never downgrade
to match. A package held back is recorded in `docs/TECH_DEBT.md` with its reason.

## Shared layer and its catalogue

The shared layer is `backend/app/core/`. Shared services that more than one entry point uses
live in `backend/app/services/`, shared datasets and their loaders in `backend/app/data/`, and
provider access in `backend/app/providers/`. The catalogue of all of it is `docs/CORE_API.md`:
check it before writing any helper.

Quick index (the catalogue is authoritative): settings (`core/config.py`), database sessions
and the pooler URL (`core/db.py`), passwords, JWTs and HMAC keys (`core/security.py`), India time
(`core/clock.py`), roles, ranks and capabilities (`core/roles.py`), the current user and capability guards (`core/deps.py`), JSON
logging, request ids and secret redaction (`core/logging.py`), sliding-window rate limits and
the client address (`core/rate_limit.py`), the error hierarchy (`core/errors.py`), Retry-After parsing
(`core/retry_after.py`), ETag revalidation (`core/http_cache.py`), work that outlives a leaving
caller (`core/shielded.py`), paced and cached source HTTP and record rules (`sources/http.py`,
`sources/records.py`, `sources/adapter.py`), JSON model calls (`research/structured.py`,
`providers/structured.py`, the schema helper `research/structured.schema_object`), the
composer (`composer/`), live research budgets (`planner/policy.py`), the MediaWiki Action API
(`sources/reference/mediawiki.py`), quote matching and strength (`research/quotes.py`), open
licences (`research/licences.py`), the craft claim scope (`retrieval/statements.py`), audit
records (`services/audit.py`), managed keys (`services/managed_secrets.py`), the model catalogue
(`services/ai_providers.py`), the AI router (`providers/router.py`), spend rules
(`providers/budget.py`), the quota ledger (`providers/quota.py`), the ElevenLabs adapter
(`providers/elevenlabs.py`), the media router and Gemini media wire
(`providers/media_router.py`, `providers/gemini_media.py`), generated names (`services/naming.py`),
the S3 adapter (`services/object_store.py`), personal-data patterns (`research/evidence.py`), the research and answering contracts (`research/`), the craft master
list and text normalisation (`data/craft_master_loader.py`, `data/craft_text.py`), LGD state and
district names (`data/district_register.py`), the curated dossier model and rules (`curation/`), the portals'
signed peer feed (`services/portal_peer.py`).

The registered vocabulary: role names and capabilities in `core/roles.py`, enums in
`models/enums.py`, evidence levels in `docs/PLAN.md` section 1, craft names and slugs from the
master list, and the naming skill (`.claude/skills/naming/`) for every generated name.

## Budgets

| Unit | Budget (a trigger to split, not a wall) |
|---|---|
| Python file | about 400 lines |
| function or method | about 40 lines |
| parameters | 5, options keyword-only |
| nesting depth | 3 |
| UI component file | about 150 lines |

Existing code over budget is recorded in the hygiene baseline (`tools/hygiene_baseline.json`)
and may only shrink.

## Commands

Run from the repository root. Nothing heavy runs on the laptop: no Docker, no local database,
no dev servers. Database tests, migrations and seeds run on GitHub Actions (Backend checks).

| Purpose | Command |
|---|---|
| backend lint | `backend\.venv\Scripts\python.exe -m ruff check backend` and `... -m ruff format --check backend` |
| backend DB-free tests | `cd backend; .venv\Scripts\python.exe -m pytest -q -m "not db"` |
| hygiene check (ratchet) | `backend\.venv\Scripts\python.exe tools\hygiene_check.py` |
| accept a lower baseline after a clean-up | `backend\.venv\Scripts\python.exe tools\hygiene_check.py --update-baseline` |
| tools lint and tests (hygiene, curation) | `backend\.venv\Scripts\python.exe -m ruff check tools` and `... -m pytest -q tools\tests` |
| curation checks and index (offline) | `backend\.venv\Scripts\python.exe tools\curation\check.py` (`--check-index` in CI); fetch and verify in `docs/RUNBOOK.md` |
| craft data tests | `cd etl\crafts; .venv\Scripts\python.exe -m pytest -q tests` |
| geo ETL tests | `cd etl\geo; python -m pip install -e .` in a venv, then `python -m pytest -q tests` |
| frontend type check | `cd frontend; npm run typecheck` |
| frontend lint | `cd frontend; npm run lint` |
| frontend unit specs | `cd frontend; npm run test:unit` (Playwright's Chromium: `npx playwright install chromium` once) |

The hygiene check enforces what a tool can decide: import direction in `backend/app`, UTF-8
without a byte-order mark and LF line endings for every tracked or new text file, and the
ratcheted counts of Python files over 400 lines, functions over 40 lines and functions with more
than 5 positional parameters. Every count must equal its baseline: a rise fails, and a fall
fails until `--update-baseline` records it, so the baseline only moves down.

The frontend's size and import-boundary rules are not yet automated (see `docs/TECH_DEBT.md`).

## Version control

Git, branch `main` only. Commits are authored and committed as ankits1802
(`ankits1802@gmail.com`) with no co-author trailers. Agents do not commit or push unless the
owner asks. Only a push to `main` of `cxacraftecosystem-ui/KalaVigyan` (remote `deploy`) deploys:
Backend checks, then Deploy backend; Vercel builds the web app from that `main`.
`ankits1802/science-behind-craft` (remote `origin`) is a mirror and deploys nothing. Text is
stored with LF line endings (`.gitattributes`); environments, build output and `.env` files are
not tracked (`.gitignore`).

## Living documents

| Document | Must stay true about |
|---|---|
| `docs/PLAN.md` | the product plan; section 0 is the owner's direction and overrides the rest |
| `docs/ARCHITECTURE.md` | layers, module map, import direction, how a question flows |
| `docs/CORE_API.md` | the catalogue of shared components |
| `docs/contracts/*.md` | interfaces between lanes: API routes, craft data, geo, frontend, infra, research and answering, the explainer, the portals' craft feed, process science, region, voice, media, curated dossiers |
| `docs/decisions/` | decision log: one short file per decision, numbered |
| `docs/TECH_DEBT.md` | debt register |
| `docs/PROGRESS.md` | where work stands and what comes next |
| `docs/RUNBOOK.md` | what is provisioned, deploy and roll back (ids and names, never secret values) |
| `docs/DATA_SOURCES.md` | datasets, licences, attribution and citations |

## Rules from the owner that override the skills

- **No code comments at all**, and no docstrings. The skills' "comment the why" and "comment the
  exception at the spot" become: record the why in `docs/decisions/`, and an exception in
  `docs/TECH_DEBT.md` naming the file and the rule. Only functional directives stay (`noqa`,
  `type: ignore`, `eslint-disable` with a reason in the decision log).
- Latest stable dependency versions.
- Secret values are never printed, logged, committed or put in fixtures: names only.
- Nothing heavy runs locally; agents never stop, restart or deploy anything.

## Domain rules that outrank convenience

These come from the plan and are never traded away for a passing test, a demo or speed:

- **Every sentence is cited.** Each answer sentence carries claim ids inside the allowed set and
  links to its sources with the quoted passage. A sentence without a source is not shown.
- **No answer text without a source.** Numbers, units and formulas in a sentence must appear in
  a cited claim or quote; a failed post-check drops the sentence.
- **Evidence levels are stored, never inferred** from model text. Only a professor, admin or
  master admin review raises a level above provisional. There are no review gates: nothing
  waits for approval to be shown.
- **Retrieved web content is data, never instructions.** Pages, PDFs, search results and model
  output are passed to models as quoted data and never change what the system does.
- **Research is not limited to the sources named in the plan**, and cites whatever it used.
- **Secrets stay server-side.** Keys live in the environment, Parameter Store and the managed
  secrets table, never in the browser, logs or responses.
- **Open datasets only** for geography and environment.
- A guard (roles, capabilities, budgets, the origin check) fails closed and is never weakened to
  make something run.
