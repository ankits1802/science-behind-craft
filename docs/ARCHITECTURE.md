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
| `shared/` | Files checked by more than one side (`craft-master.sha1`) |
| `tools/` | Developer tooling: `hygiene_check.py` and the `hygiene` package with its tests |
| `docs/` | Plan, architecture, catalogue, contracts, decisions, debt, progress, runbook, data sources |
| `.claude/skills/` | Practice skills (engineering, backend, frontend), naming, frontend design system |

## Backend layers

```
entry points   main.py   api/ (router.py, routes/<area>.py)   scripts/ (seeds, sync, coverage job)
                 |
adapters       providers/   model adapters, AI router, spend rules
                 |
domain         services/    crafts, knowledge view, access roster, credentials, keys, routing,
                            live-research write-back and the coverage job (decision 0011)
               schemas/     request and response bodies
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
shared         core/        settings, db, security, roles, deps, logging, rate limits
                 |
foundation     models/      ORM tables          data/   vendored datasets and pure loaders
```

The allowed import edges are the table `LAYER_IMPORTS` in `tools/hygiene/layers.py`, listed in
the project bindings (`.claude/skills/engineering-practices/references/project-bindings.md`).
The hygiene check fails on any other edge, including late imports inside functions, and on any
package under `backend/app` that has no row yet. Two placements are deliberate and recorded:
`core/deps.py` imports `models.User` because the current-user dependency returns the ORM row,
and `providers/` imports `services/` for the model catalogue, app settings and managed keys
(decision 0001).

## API surface

All routes are under `/api` except `/health` and `/health/ready`. Route groups (`api/routes/`):
`auth`, `two_factor`, `me`, `access`, `users`, `crafts`, `knowledge`, `secrets`, `settings`,
`usage`. Shapes, headers and error forms are in `docs/contracts/backend.md`; the web client's
side is `docs/contracts/frontend.md`.

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
   `store_live_research`, decision 0011), and each sentence is sent with the citations of the
   stored claims it rests on, including the ones just written. `status` events mark each step.
5. Nothing cited: `not_enough_evidence` says what was searched; any failure is one `error`;
   `done` always ends the stream.

## Data

Tables follow DR's Prisma naming (quoted PascalCase tables, camelCase columns) so the portals
stay mergeable; the full list is `backend/app/models/` and `backend/migrations/versions/`.
Craft data is vendored from the designer portal (`docs/contracts/crafts.md`); district and
environment data come from open datasets (`docs/contracts/geo.md`, `docs/DATA_SOURCES.md`).
Seeds (`app/scripts/seed_crafts`, `seed_claims`, `seed_districts`) run on every deploy and are
idempotent. After them, `app/scripts/sync_portal_crafts` adds every craft the two portals hold
beyond the master list, with their aliases, spellings and merge redirects, through the signed
peer route of `docs/contracts/portal-craft-feed.md`; it also runs daily (decision 0003).

## Frontend

Next.js App Router. Signed-in screens are under `app/(protected)/` (ask, crafts, map, settings,
admin); `app/api/` holds route handlers that proxy auth and session calls; `lib/api.ts` is the
one API client and `lib/server/apiProxy.ts` the server-side proxy. Generic components are in
`components/ui/`, domain components in `components/<area>/`. Design rules are the
`field-repo-frontend`, `motion` and `gsap` skills; practice rules are `frontend-practices`.

## Checks

| Workflow | Runs |
|---|---|
| Backend checks | ruff, DB-free pytest, hygiene tool tests, hygiene check, offline migration render; then migrations, seeds and DB tests against PostGIS with pgvector |
| Frontend checks | typecheck, lint, unit specs, smoke specs |
| Craft data | master-list sha1, lint and tests of `etl/crafts`; weekly regeneration |
| Geo ETL | `etl/geo` tests and the district statistics build |
| Deploy backend | after Backend checks succeed on a push to `main` of `cxacraftecosystem-ui/KalaVigyan` |
