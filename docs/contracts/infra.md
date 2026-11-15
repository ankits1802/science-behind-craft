# Contract: provisioning and deploy lane

What the box and the deploy workflows assume from the backend, frontend and CI lanes. If one of these is wrong, change it here and in `infra/` together.

## CI

- A workflow named exactly `Checks` (`.github/workflows/checks.yml`) runs on `push` to `main`. `Deploy backend` starts from its `workflow_run` and only when it concluded `success`.
- `Deploy frontend` starts from `Deploy backend` succeeding, so the web app never ships ahead of the API.

## Backend

| Assumption | Detail |
|---|---|
| Packaging | `backend/pyproject.toml` with uv. Commit `backend/uv.lock`; without it the box resolves dependencies itself and the deploy warns. Installed with `uv sync --no-dev --no-editable --frozen` on CPython 3.14.10 (standalone build at `/opt/cpython/3.14.10+20261110`). |
| ASGI app | `app.main:app`, started from `backend/` as `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000|8001 --workers ${API_WORKERS} --no-proxy-headers`. `API_WORKERS` defaults to 1. |
| Liveness | `GET /health` answers 200 without touching the database. The blue/green switch, nginx check, watchdog and CloudFront smoke test all call it. |
| Migrations | `backend/alembic.ini` present → `python -m alembic upgrade head` runs from `backend/` with the env loaded, before the new colour starts. No `alembic.ini` → no migrations. |
| Worker | `app.worker` (`app/worker.py` or `app/worker/__main__.py`). systemd starts `kv-worker` only if one exists. Stopped during migrations, restarted after the switch. |
| Fetcher | `app.fetcher` (`app/fetcher.py` or `app/fetcher/__main__.py`), listening on `FETCHER_HOST:FETCHER_PORT` (127.0.0.1:8090). It gets only `/opt/kalavigyan/fetcher.env`: keys starting with `FETCHER_` plus `APP_ENV` and `LOG_LEVEL`. It has no AWS keys or database URL. systemd blocks link-local (instance metadata) and private ranges. It does **not** block loopback, so the fetcher must refuse loopback targets itself. Memory cap 768 MB, 64 tasks. |
| Env file | `/opt/kalavigyan/.env`, rendered from SSM `/kalavigyan/env/*` as `NAME='value'` lines. It is symlinked as `backend/.env` in every release, so pydantic-settings and Alembic find it. Values never contain `'` or line breaks. |
| Database | `DATABASE_URL` is `postgresql://postgres.<ref>:<pw>@aws-1-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require` (Supabase **session** pooler). SQLAlchemy code converts the scheme to `postgresql+psycopg` itself. `DATABASE_USE_TRANSACTION_POOLER=false`, `DATABASE_CONNECTION_LIMIT=5` per colour. Extensions vector, postgis, pg_trgm, unaccent and citext are in schema `extensions`. Every new `public` table gets RLS from an event trigger. The app connects as `postgres`, which bypasses RLS. anon and authenticated have no grants. |
| Media | `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` belong to IAM user `kalavigyan-media`. It may Put/Get/Delete/AbortMultipart on `media/*` and Put/Get on `exports/*`, and ListBucket only within those two prefixes. Keys follow the naming skill: `media/<userId>/<uuid32hex>/<FileName>`. `exports/` expires after 7 days. The bucket is private: presigned GET/PUT only, SSE-S3 (`AES256`). |
| Client address | Chain is browser → CloudFront → nginx → uvicorn, so with `FORWARDED_CLIENT_HOPS=2` the client is the 2nd `X-Forwarded-For` entry from the right. `X-Forwarded-Proto` is `https` for viewer traffic. |
| Streaming | nginx has `proxy_buffering off`. CloudFront's origin read timeout is 120 s between bytes, so SSE answers send a heartbeat at least every 60 s. |
| CORS | `BACKEND_CORS_ORIGINS=https://kalavigyan.vercel.app` (comma-separated list). The bucket's CORS also allows `http://localhost:3000` and `http://127.0.0.1:3000` for local dev. |
| Search | SearXNG at `SEARXNG_URL` (`http://127.0.0.1:8888`) with JSON enabled: `/search?q=…&format=json`. |
| Redis | `REDIS_URL` (`redis://127.0.0.1:6379/0`), loopback only, 256 MB LRU. Treat it as a cache. The job queue stays in Postgres (PLAN §3). |
| Request body | nginx accepts up to 200 MB. Large media goes to S3 directly. |

## Frontend

- Vercel project `kalavigyan` (team `cxacraftecosystem-8028s-projects`), Root Directory `frontend`, Node 26.x, no Git link. Production URL `https://kalavigyan.vercel.app`.
- `NEXT_PUBLIC_API_URL=https://d89rsltpszebp.cloudfront.net` (origin only, no trailing slash, no path). The frontend adds whatever prefix the backend mounts its routes under. Also set: `NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_GOOGLE_CLIENT_ID`. All are stored as Encrypted (not Sensitive), so `vercel pull` in CI can read them.
- The app must build with `vercel build --prod` from the repository root.
