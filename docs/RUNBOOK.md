# KalaVigyan runbook

This page lists what is provisioned, how to deploy, and how to roll back. It holds ids and names only. Secret values live in GitHub Actions secrets and SSM Parameter Store, and nowhere else.

## What exists

| Thing | Id / name |
|---|---|
| AWS account / region | `626159998512` / `ap-south-1` |
| API box | EC2 `i-0a58a2feb528241aa` (`kalavigyan-api`, t3.large, Ubuntu 26.04, 40 GB gp3 encrypted, IMDSv2 only, no key pair) |
| Elastic IP | `13.206.8.117` (`ec2-13-206-8-117.ap-south-1.compute.amazonaws.com`). Port 80 answers CloudFront only. Nothing listens publicly on 22 or 443. |
| Security group | `sg-07ac2689e2bf12426` (`kalavigyan-api`): inbound 80 from prefix list `com.amazonaws.global.cloudfront.origin-facing` only |
| HTTPS API | `https://d89rsltpszebp.cloudfront.net`, CloudFront `E3J72POLWOPQ8T`, origin `kalavigyan-ec2-origin`, http-only to the origin, header `X-Origin-Verify`, CachingDisabled + AllViewerExceptHostHeader, PriceClass_200 |
| Media bucket | `kalavigyan-media-626159998512`: private, public access blocked, versioned, SSE-S3, TLS-only policy, CORS for `https://kalavigyan.vercel.app` + localhost:3000 |
| Terraform state | `s3://kalavigyan-tfstate-626159998512/kalavigyan/infra.tfstate` (versioned, private, S3 lockfile). DR's and FR's state are not touched. |
| IAM | user `kalavigyan-media` (API's S3 key), role + instance profile `kalavigyan-box`, role `kalavigyan-deploy` (GitHub OIDC, `repo:cxacraftecosystem-ui/KalaVigyan:ref:refs/heads/main` only) |
| Parameter Store | `/kalavigyan/env/*` (SecureString, one parameter per env key, the box's source of truth). `/kalavigyan/db-password` (Supabase DB password backup) |
| Database | Supabase project `science-behind-craft`, ref `inqbqiqspgvhfamupwuc`, org `pifvglrcqwrizapmooik`, ap-south-1, Postgres 17.11. Session pooler `aws-1-ap-south-1.pooler.supabase.com:5432`, user `postgres.inqbqiqspgvhfamupwuc` |
| Web | Vercel project `kalavigyan` (`prj_5hRNy7S9CS4fkhVVBRW5mbmAAUSd`), team `team_pcTf4Alb2DCIwq2IZcdu00dS`, root `frontend`, Node 26.x, no Git link, `https://kalavigyan.vercel.app` |
| Repository | `github.com/cxacraftecosystem-ui/KalaVigyan` (deploys); mirror `github.com/ankits1802/science-behind-craft` (public, no deploys) |

### On the box

| Path / unit | Role |
|---|---|
| `/opt/kalavigyan/releases/<sha>` | One directory per release: `backend/` with its own `.venv`, `infra/deploy/`, `REVISION` |
| `/opt/kalavigyan/slot-8000`, `slot-8001`, `current` | Symlinks used by blue/green. nginx proxies to exactly one port. |
| `/opt/kalavigyan/.env`, `fetcher.env` | Rendered from Parameter Store by `kv-render-env` (0640 root:kalavigyan) |
| `kv-api@8000`, `kv-api@8001` | The two API colours (user `kalavigyan`, MemoryMax 3000M, Restart=always) |
| `kv-worker`, `kv-fetcher` | Started only once a release ships `app.worker` / `app.fetcher`. `app/worker.py` (the media queue, decision 0018) ships with the media backend; `journalctl -u kv-worker` shows its jobs. |
| `api-watchdog.timer` | Restarts a running colour after 2 failed `/health` checks a minute apart (`journalctl -t api-watchdog`) |
| nginx site `kalavigyan` | `:80`. The snippet `kalavigyan-origin-verify.conf` returns 403 without CloudFront's header; loopback is exempt. |
| `redis-server` | `127.0.0.1:6379`, 256 MB LRU |
| Docker `searxng` | `127.0.0.1:8888`, image `searxng/searxng:2026.11.15-2d500cb6b`, settings `/etc/searxng/settings.yml` |
| `/opt/cpython/3.14.10+20261110` | Standalone CPython (python-build-standalone 20261110, sha256-checked). uv 0.13.8 in `/usr/local/bin` |
| `/usr/local/sbin/kv-blue-green`, `kv-render-env` | Installed from `infra/deploy/` on every release |
| certbot | Installed, unused: TLS ends at CloudFront. It is there for a custom domain later. |

## Shell on the box

```bash
aws ssm start-session --target i-0a58a2feb528241aa --region ap-south-1
sudo kv-blue-green status
```

## Secrets

Every secret is in three places: a GitHub Actions secret, `/kalavigyan/env/<NAME>` in Parameter Store, and `/opt/kalavigyan/.env` on the box. The one exception is the E2E account (`E2E_EMAIL`, `E2E_PASSWORD`): only the E2E production workflow reads it, so it is a GitHub secret alone (E2E production run, below).

- GitHub secrets: `DATABASE_URL`, `JWT_SECRET`, `SECRETS_ENCRYPTION_KEY`, `TWO_FACTOR_ENCRYPTION_KEY`, `ORIGIN_VERIFY_SECRET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `GOOGLE_CLIENT_ID`, `MASTER_ADMIN_EMAIL`, `MASTER_ADMIN_NAME`.
- GitHub variables: `AWS_REGION`, `AWS_DEPLOY_ROLE_ARN`, `AWS_RIVER_LOAD_ROLE_ARN` (decision 0050), `EC2_INSTANCE_ID`, `MEDIA_BUCKET`, `API_BASE_URL`, `CLOUDFRONT_DISTRIBUTION_ID`, `WEB_ORIGIN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
- Parameter Store also holds non-secret config (`APP_ENV`, `BACKEND_CORS_ORIGINS`, `FORWARDED_CLIENT_HOPS`, `REDIS_URL`, `SEARXNG_URL`, …). See `infra/.env.example` for every name.
- Copied from the DR box without printing them: `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `GOOGLE_CLIENT_ID`, `MASTER_ADMIN_EMAIL`, `MASTER_ADMIN_NAME`.
- `CROSS_PORTAL_TOKEN`: copied without printing from the shared SSM SecureString `/iit/shared/cross-portal-token` (the designer and documentation portals' value) into `/kalavigyan/env/CROSS_PORTAL_TOKEN` and the GitHub secret on 2026-11-16. `DESIGNER_PORTAL_API_URL` and `FIELD_REPOSITORY_API_URL` are in Parameter Store. The box `.env` gets all three at the next deploy's render.

**The owner still has to add these** (none of them were on the DR box):

| Name | Where |
|---|---|
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `BRAVE_SEARCH_API_KEY` | GitHub secrets. The next backend deploy copies them into Parameter Store and the box. |
| `TURNSTILE_SECRET_KEY`, `TURNSTILE_SITE_KEY` | Create a Cloudflare Turnstile widget for `kalavigyan.vercel.app`. The secret is a GitHub secret and the site key a GitHub variable; each deploy copies both into Parameter Store. Until both exist, production email sign-up is closed and the page offers Google only. |
| `WEB_PROXY_SECRET` | Re-run `seed_secrets.py` once: it generates the value and writes Parameter Store, the GitHub secret and the Vercel env (Sensitive). It also deletes the retired names `AWS_S3_BUCKET`, `BRAVE_API_KEY`, `NEXT_PUBLIC_APP_URL`, `DATABASE_USE_TRANSACTION_POOLER`, `TWO_FACTOR_KEY_REQUIRED` and `MEDIA_PRESIGNED_READS` from Parameter Store. |
| `VOICE_LLM_BEARER`, `VOICE_SESSION_HMAC_KEY`, `TRANSCRIPT_ENCRYPTION_KEY` | Re-run `seed_secrets.py` once: it generates all three like the other generated keys and writes Parameter Store and the GitHub secrets; Deploy backend keeps them in sync. Voice stays hidden until `TRANSCRIPT_ENCRYPTION_KEY` and `ELEVENLABS_API_KEY` exist. |
| `MEDIA_BUNDLE_HMAC_KEY` | Re-run `seed_secrets.py` once: it generates it like the voice keys and writes Parameter Store and the GitHub secret; Deploy backend keeps it in sync. Media stays hidden and `kv-worker` waits until it exists. |
| `ELEVENLABS_AGENT_ID` | Only for the `AGENT` transport: after the voice agent is provisioned (Voice, below), store the printed agent id as a GitHub secret and deploy. |
| `CORE_API_KEY` | Rotate it with CORE: a settings error on the laptop printed the start of the old value. The backend now hides input values in settings errors. |
| `MAIL_FROM_ADDRESS` | Parameter Store, once an SES identity is chosen for KalaVigyan mail |
| Google OAuth client | Add `https://kalavigyan.vercel.app` to the client's Authorized JavaScript origins |
| `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `NEXT_PUBLIC_YAHOO_CLIENT_ID` | Register the Yahoo app and set the three names as in Yahoo sign-in, below. Until then there is no "Continue with Yahoo" button. |

To change a secret: `gh secret set NAME --repo cxacraftecosystem-ui/KalaVigyan`, then run **Deploy backend**. The deploy copies changed GitHub secrets into Parameter Store and re-renders the box `.env`. For config that is not a GitHub secret:

```bash
aws ssm put-parameter --region ap-south-1 --name /kalavigyan/env/NAME --type SecureString --overwrite --cli-input-json file://value.json
sudo kv-render-env && sudo kv-blue-green restart     # on the box
```

`infra/scripts/seed_secrets.py` rebuilds the whole set. It keeps existing generated keys, takes the Terraform outputs, and writes Parameter Store, GitHub, Vercel and the box. Run it with a Python that has `boto3` and `cryptography`, passing `--terraform <path to terraform>`. `--copy-from-instance <id>` copies the provider keys from another box's `.env` over an RSA-encrypted SSM channel.

Never rotate `TWO_FACTOR_ENCRYPTION_KEY`, `SECRETS_ENCRYPTION_KEY` or `TRANSCRIPT_ENCRYPTION_KEY` by overwriting them: stored data is encrypted with them.

## Yahoo sign-in

Decision 0026. The backend redeems Yahoo's code with the client secret, so the secret never reaches a browser.

1. Register the app at `https://developer.yahoo.com/apps/create/`, signed in with the project's Yahoo account:
   - Application Name `KalaVigyan`, Homepage URL `https://kalavigyan.vercel.app`.
   - Redirect URI(s): exactly `https://kalavigyan.vercel.app/login/callback`. The backend accepts only `PUBLIC_WEB_URL` + `/login/callback`, so the two must match; a new web domain needs both changed.
   - OAuth Client Type: Confidential Client.
   - API Permissions: OpenID Connect Permissions, with Email and Profile ticked. Without Email the ID token carries no verified address and every sign-in is refused.
   - Create the app and keep the page open: it shows the Client ID (Consumer Key) and Client Secret (Consumer Secret).
2. Backend first: `gh secret set YAHOO_CLIENT_ID --repo cxacraftecosystem-ui/KalaVigyan` and `gh secret set YAHOO_CLIENT_SECRET --repo cxacraftecosystem-ui/KalaVigyan` (paste each value at the prompt, never on the command line), then run **Deploy backend**. It copies both into Parameter Store and the box `.env`. `GET https://kalavigyan.vercel.app/api/auth/config` then answers `yahooEnabled: true`.
3. Then the web: add `NEXT_PUBLIC_YAHOO_CLIENT_ID` (the same Client ID, Encrypted, Production and Preview) to the Vercel project, or re-run `seed_secrets.py`, which sets it from Parameter Store once both Yahoo values are there. Redeploy the web app: the value is read at build time. The login page now shows "Continue with Yahoo".
4. Check: sign in with a Yahoo address that is on the access roster. An address not on the roster becomes a PENDING request, exactly as with Google.

Rotating the secret: create a new secret on the Yahoo app page, `gh secret set YAHOO_CLIENT_SECRET`, deploy. A wrong or retired secret turns every Yahoo sign-in into "Yahoo sign-in didn't work" and the API log shows `oidc: the provider refused the redemption` with `invalid_client`. To switch Yahoo off, delete `NEXT_PUBLIC_YAHOO_CLIENT_ID` in Vercel and redeploy the web, then remove the two backend values from GitHub and `/kalavigyan/env/` and deploy.

Microsoft sign-in is built the same way and stays off: leave `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_TENANT` and `NEXT_PUBLIC_MICROSOFT_CLIENT_ID` unset.

## Voice

Decision 0017; contract `docs/contracts/voice.md`.

- The live call is off (decision 0035): `VOICE_CALL_ENABLED` defaults to false, so every
  `/api/voice` route answers 404 and no voice button is drawn. Turning it on means adding
  `VOICE_CALL_ENABLED=true` to the environment **Deploy backend** writes to the box `.env` (a
  workflow change and a deploy); the call then starts from the craft page's Talk button only (the
  mic on `/ask` is dictation, decision 0036).
- Listen (decision 0035) needs only `ELEVENLABS_API_KEY` (Settings, API keys) and `S3_BUCKET`. Its
  audio lives under `media/narration/<cacheId>/` in the media bucket (part MP3s, then
  `narration.json`); deleting a folder only makes the next listener synthesise it again. The
  voice is `AppSetting` `voice.voice_id`; changing it starts a new cache.
- Film scores (decision 0058) use the same key through the media router: Settings, AI routing
  shows Film music (`music_v2_5`) and Film sound effects (`eleven_text_to_sound_v3`), seeded by
  migration `0022_elevenlabs_media`. The restricted key needs the Music and Sound Effects
  permissions; the ElevenLabs image and video choices (`gemini-3.1-flash-image`,
  `veo-3.1-fast-generate-001`, not in any chain until an admin adds them) need the Image and Video
  permission and a Pro plan. Spend counts against the media sub-cap. Clips live under
  `media/score/<cacheId>/` (MP3 and `clip.json`) and each score's manifest under
  `media/score/<answerId>/<language>/score.json`; deleting either only makes the next ask make it
  again. A finished ElevenLabs image or video is fetched only from `storage.googleapis.com`
  (decision 0061); if a generation fails with "generation link answer is off its documented shape",
  ElevenLabs has moved its downloads: add the new host to
  `providers/elevenlabs_download.DOWNLOAD_HOSTS` after checking the reference.

- Transport: `AppSetting` `voice.transport` is `RELAY` until the ElevenLabs spike passes. To switch,
  on the box: `INSERT INTO "AppSetting" (key, value) VALUES ('voice.transport', '"AGENT"') ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;`
  (the same for `voice.max_live_sessions`, default 5, and `voice.voice_id`).
- Agent: `cd /opt/kalavigyan/current/backend && sudo -u kalavigyan bash -c 'set -a; . /opt/kalavigyan/.env; set +a; .venv/bin/python -m app.scripts.provision_voice_agent --dry-run'`
  prints the body; without `--dry-run` it creates or updates the workspace secret
  `KALAVIGYAN_VOICE_LLM_BEARER`, the client tools `show_on_map`, `open_stage`, `show_sources`,
  `offer_image` and the agent `KalaVigyan voice`, and prints the agent id (not a secret). Needs
  `PUBLIC_API_URL`, `VOICE_LLM_BEARER` and `ELEVENLABS_API_KEY`.
- Rotating `VOICE_LLM_BEARER` (quarterly): `gh secret set VOICE_LLM_BEARER`, deploy, then run the
  provisioning script again so the workspace secret matches; calls in progress end with a 401.
- Upkeep: `app.scripts.voice_upkeep` runs first in the daily **Coverage enrichment** box job; its JSON
  line reports closed, purged, reconciled and refunded seconds.

## Deploy

Automatic: a push to `main` that touches `backend/**`, `shared/**`, `infra/deploy/**`, `backend-checks.yml` or `deploy-backend.yml` → **Backend checks** → **Deploy backend**. Vercel builds the web app from `main` on its own.

Deploy backend (`.github/workflows/deploy-backend.yml`):

1. Assumes `kalavigyan-deploy` through GitHub OIDC (no static AWS keys in GitHub).
2. Copies changed secrets into `/kalavigyan/env`.
3. Uploads `git archive HEAD backend infra/deploy` to `s3://kalavigyan-media-626159998512/deploy/backend/<sha>/KalaVigyan_API_Release-Build_<sha12>.tar.gz`.
4. Runs `infra/deploy/release.sh <sha>` on the box over SSM `AWS-RunShellScript`, logging to `deploy/logs/<sha>/`. The script installs units, renders the env, builds the venv with uv, then `blue_green.sh release <sha>`:
   1. migrate (`alembic upgrade head`), seed (`seed_crafts`, `seed_claims`, `seed_districts`) and import the curated dossiers (`import_curation`, decision 0053; a refused dossier exits 2 and stops the release like a failed seed) while the old colour serves, then sync crafts from both portals (`sync_portal_crafts`; a failure is a warning, the release goes on) and fill missing craft descriptor vectors (`embed_craft_descriptors`; a failure is a warning too);
   2. start the other colour;
   3. wait for `/health`;
   4. switch nginx;
   5. stop the old colour;
   6. restart the worker and fetcher.

   It keeps the newest 5 releases.
5. Smoke-tests `https://d89rsltpszebp.cloudfront.net/health`.

Craft sync (`.github/workflows/craft-sync.yml`): daily at 21:37 UTC and on dispatch, runs `app.scripts.sync_portal_crafts` in `/opt/kalavigyan/current/backend` on the box over SSM, logging to `deploy/logs/craft-sync/<run id>/`. It prints one JSON report and fails when a portal did not answer (`docs/contracts/portal-craft-feed.md`).

Alert digest (`.github/workflows/alert-digest.yml`): Mondays at 03:30 UTC (09:00 India time) and on dispatch, runs `app.scripts.send_alert_digest` on the box over SSM, logging to `deploy/logs/alert-digest/<run id>/`. It prints `{enabled, weekOf, readers, sent, failed, ok}`; while `ALERT_DIGEST_ENABLED` is unset or false it sends nothing and succeeds. To switch it on, after an SES sender identity is verified for `MAIL_FROM_ADDRESS` (region `MAIL_SES_REGION`) and the account is out of the SES sandbox: put `ALERT_DIGEST_ENABLED=true` at `/kalavigyan/env/ALERT_DIGEST_ENABLED` as above and re-render the box `.env` (`sudo kv-render-env`). Enabled without `MAIL_FROM_ADDRESS` it fails without sending. Readers opt in under Settings (decision 0063).

Coverage enrichment (`.github/workflows/coverage-enrichment.yml`): daily at 22:17 UTC and on dispatch, runs `app.scripts.voice_upkeep`, `app.scripts.embed_craft_descriptors` (missing craft name-and-alias vectors for the resolver, decision 0016), `app.scripts.embed_knowledge` (fills every missing claim, chunk and knowledge-piece vector, so the backlog is never embedded inside a learner's request, decision 0013), `app.scripts.link_compounds` (links every unlinked compound with a formula to its PubChem record and prints `{linked, notFound, failed, ok}`, decision 0045) and last `app.scripts.recheck_saved` (re-checks every saved explainer for new cited claims in its fields, writes "This answer got better" notes, no model call, prints `{checked, notified, ok}`, decision 0063) in `/opt/kalavigyan/current/backend` on the box over SSM, logging to `deploy/logs/coverage-enrichment/<run id>/`; the step fails when any of them fails. Since commit fdf478c it no longer researches crafts or rebuilds pieces (`app.scripts.rebuild_pieces` and `app.scripts.enrich_coverage` are not run; the dataset is curated by Claude Code, `docs/plans/dataset-curation.md`).

Running the same sha again re-renders the env and restarts the live colour.

Frontend: Vercel's Git integration builds `main` (`frontend/vercel.json`); there is no Actions deploy.

## Geo ETL

**Geo ETL** (`.github/workflows/geo-etl.yml`, dispatch only) first lints and tests `etl/geo`, then extracts the district statistics on a matrix and, for `riverlines`, the river lines and one TopoJSON per basin in a single job. With `load` it upserts the district tables, and uploads the topologies under `media/rivers/<edition>/<mainRiv>/<sha256>/` (content-addressed, decision 0050) then replaces `RiverBasin` and `RiverReach` in one transaction. The load jobs read `DATABASE_URL`; the river load assumes `kalavigyan-river-load` through GitHub OIDC (the variable `AWS_RIVER_LOAD_ROLE_ARN`; the role may only put and read objects under `media/rivers/` and list that prefix) and reads `AWS_REGION` and `MEDIA_BUCKET`. It holds no long-lived AWS key. Contracts: `docs/contracts/geo.md`; datasets and licences: `docs/DATA_SOURCES.md`.

Before the first river load, once: the owner applies `infra/terraform` (it adds the role `kalavigyan-river-load`, its policy and the output `river_load_role_arn`) and sets the repository variable, by re-running `infra/scripts/seed_secrets.py` or directly:

```bash
gh variable set AWS_RIVER_LOAD_ROLE_ARN --repo cxacraftecosystem-ui/KalaVigyan --body "$(terraform -chdir=infra/terraform output -raw river_load_role_arn)"
```

The `load-rivers` job stops with a named error when the variable is unset.

After the backend deploy that carries migration `0016_river_reaches` (decision 0043), dispatch these one at a time (the `geo-etl` concurrency group keeps one pending run):

1. River lines and basin topologies: datasets `riverlines`, load on (states and shards do not apply).
   ```bash
   gh workflow run geo-etl.yml --repo cxacraftecosystem-ui/KalaVigyan -f datasets=riverlines -f load=true
   ```
   The `rivers` job's summary gives the reaches, basins and the largest file; `load-rivers` prints the topologies uploaded and the rows written. Check: `GET /api/rivers/<mainRiv>` for a basin of `RiverBasin` answers 200 with an `ETag`. Re-running is safe: a file already stored under its digest is not uploaded again, and a changed file goes to a new key beside the old one.
2. Rainfall and temperature, 1981 to last year, with their trends (decision 0065): after the backend deploy that carries migration `0021_climate_trend_stats` (the load writes the stats `TREND_PER_DECADE` and `TREND_P_VALUE`, which the database refuses before it). Datasets `chirps,ghcncams`, states `all`, shards `24`, load on, prune on.
   ```bash
   gh workflow run geo-etl.yml --repo cxacraftecosystem-ui/KalaVigyan -f datasets=chirps,ghcncams -f states=all -f shards=24 -f load=true -f prune=true
   ```
   `chirps` runs on 24 shards (45 annual and 540 monthly files a shard, about four times the old ten-year run, so each shard stays well inside the 350-minute limit) and writes the CHIRPS dataset row over `1981-<last year>`: the yearly series, the annual and twelve monthly normals and the trend of every district with all years. `ghcncams` is one job whatever the shards: it downloads the GHCN CAMS file (about 190 MB) once and writes each district's yearly mean temperature, normal and trend over the same years. `prune` deletes each loaded district's older rows of the two datasets, so the ten-year normals of the last CHIRPS load (`2016-2025`) do not linger beside the new ones. Then the seasons blocks credit the rainfall as a monthly normal over `1981-<last year>`, and the climate builder finds trends once `climate_risk` is built. Checks, read-only on the box: `select count(distinct v."districtLgd") from "DistrictEnvValue" v join "EnvDataset" d on d.id = v."datasetId" where d.code = 'CHIRPS_3_0' and v.variable = 'monthly_precipitation' and v."depthOrPeriod" like d.period || '-%'` should be 752, and `select d.code, count(distinct v."districtLgd") from "DistrictEnvValue" v join "EnvDataset" d on d.id = v."datasetId" where d.code in ('CHIRPS_3_0', 'GHCN_CAMS_T2M') and v.stat = 'TREND_PER_DECADE' and v."depthOrPeriod" = d.period group by d.code` should give 752 for CHIRPS and, for GHCN CAMS, 752 less the districts the run summary lists under `districtsWithoutCells` (a district with no 0.5 degree land cell, such as an island). Then replace the placeholder Kachchh trend in `shared/explainer.phase-d.golden.json` with the loaded row (`docs/TECH_DEBT.md`, decision 0062).

## How to curate a craft

The plan is `docs/plans/dataset-curation.md`; the dossier format and every rule are in
`docs/contracts/curation.md` (decision 0051). Run from the repository root on the laptop with the
backend environment (`backend\.venv\Scripts\python.exe` on Windows; `backend/.venv/bin/python`
elsewhere). No model or keyed API is called; `fetch.py` and `verify.py` make plain HTTP requests.

1. Read each source as the verifier will, and copy quotes only from these numbered lines:
   ```bash
   backend/.venv/Scripts/python.exe tools/curation/fetch.py "https://<the source page or PDF>" --out <scratch file>
   ```
   When it prints `read: ARCHIVE ...`, the live page refused and the text came from the Wayback
   Machine: put the printed `archivedUrl` on the source.
2. Write `backend/app/data/curation/<CraftSlug>.json` (`<CraftSlug>` as on the master list, for
   example `Kutch-Ajrakh`), recording every query in `searched`.
3. Verify every quote against a fresh fetch; this writes `<CraftSlug>.check.json` beside it and
   prints one line per source that could not be read and per quote not found:
   ```bash
   backend/.venv/Scripts/python.exe tools/curation/verify.py backend/app/data/curation/<CraftSlug>.json
   ```
   Drop each failing quote, each claim left without one, and each unreadable source with its
   claims, then verify again.
4. Run the offline checks; this prints one line per problem and regenerates
   `backend/app/data/curation/index.json`:
   ```bash
   backend/.venv/Scripts/python.exe tools/curation/check.py backend/app/data/curation/<CraftSlug>.json
   ```
   Fix and repeat steps 3 and 4 until both print nothing. An edit to a source or a quote needs
   step 3 again; prose and structure edits need only step 4.
5. Before a wave is committed, check every dossier and keep the index it writes; CI runs the same
   checks with `--check-index`, which writes nothing and fails on a stale index:
   ```bash
   backend/.venv/Scripts/python.exe tools/curation/check.py
   ```

## Import the curated dossiers again

The deploy imports every checked dossier after the seeds (above). To re-run it on the box by hand
(it is idempotent: a second run reports an empty `changed` for every dossier and withdraws no
more edge sentences):

```bash
cd /opt/kalavigyan/current/backend && sudo -u kalavigyan bash -c 'set -a; . /opt/kalavigyan/.env; set +a; .venv/bin/python -m app.scripts.import_curation'
```

It prints one JSON report: `withdrawnEdgeSentences`, `imported`, `refused`, and per dossier its
`status`, `changed` row counts, `problems` and `droppedSentences` (overview sentences the prose
validator refused). Exit 2 means a dossier was refused; its `problems` are the checker's lines.
To see a dossier's craft page without a database, from `backend/` on the laptop:

```bash
.venv/Scripts/python.exe -m app.scripts.import_curation --preview Kutch-Ajrakh --out ../shared/craft.page.golden.json
```

That command also regenerates the craft page fixture after a change to the Kutch Ajrakh dossier
or the page; `tests/contracts/test_craft_page_contract.py` fails until it is rerun.

## Roll back

Backend, on the box. This is instant: the previous release is still in the other slot.

```bash
sudo kv-blue-green status
sudo kv-blue-green rollback            # back to whatever the idle slot holds
sudo kv-blue-green rollback <sha>      # or any kept release: ls -t /opt/kalavigyan/releases
```

A rollback does not reverse migrations. If a migration has to be undone, run `alembic downgrade` from the release that added it before rolling back.

Frontend: `vercel rollback --scope cxacraftecosystem-8028s-projects` (or Instant Rollback in the dashboard). A rollback stops automatic domain assignment until the next `vercel promote` or `--prod` deploy.

## Checks

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://d89rsltpszebp.cloudfront.net/health   # 200 once a backend is deployed (502 = nginx up, no API yet)
curl -m 8 http://13.206.8.117/health                                                     # must time out: the origin is CloudFront-only
aws cloudfront get-distribution --id E3J72POLWOPQ8T --query "Distribution.DistributionConfig.Origins.Items[0].CustomHeaders.Items[].HeaderName"
aws ssm get-parameters-by-path --region ap-south-1 --path /kalavigyan/env --query "Parameters[].Name"
```

As provisioned on 2026-11-16, each layer was checked:

- CloudFront → nginx answered 502 from nginx (the origin header was accepted and no API exists yet).
- The Elastic IP gave no answer.
- SearXNG JSON returned results, and Redis answered PONG.
- The box reached Postgres 17.11 through the session pooler, with the five extensions and the RLS event trigger present.

## E2E production run

Decision 0029. **E2E production** (`.github/workflows/e2e-production.yml`, dispatch only, deploy repository only) drives `https://kalavigyan.vercel.app` with Playwright at 1440x900, 834x1194 and 390x844. It signs in through the login form, visits landing, login, Ask, Crafts, Kutch Ajrakh (Overview, Process, Region, Shared science), the map with a layer chosen, Settings and the 404 page, and fails on console errors, failed requests, sideways scroll, overflowing text, error alerts, gap copy or a menu that does not match the role. With `questions=true` it also asks the four known-answer questions, up to 10 minutes each: at Detailed depth the mordant in English and Hindi (alum) and the water of Kachchh for Kutch Ajrakh, which passes only on a `region_story` with a traced river and every step cited; at Expert depth how indigo turns blue on Kutch Ajrakh cloth (decision 0061), which passes when every generated explainer the stream sends is drawn in a `sandbox="allow-scripts"` frame whose document opens with the sandbox policy, draws something, offers no peer connection, and attempts no network request (each one is aborted and recorded) and no load its policy refuses; when the builder chose no concept the report notes it and does not fail. Until the river lines are loaded, dispatch without `rivers_loaded` and a missing story is written to the report's notes, not failed; from the first run after the Geo ETL `riverlines` load add `-f rivers_loaded=true` (decision 0050). After the questions it opens the English answer's stored explainer (`/ask?explainer=<id>`) and downloads, through its Export menu, the report PDF and the APA, BibTeX, RIS and CSL-JSON citations: each must open (a PDF with pages, a parseable CSL-JSON list) and carry every source the answer streamed (its DOI or URL link in the PDF, APA and BibTeX, its title in RIS and CSL-JSON). An account that may build lesson packs also builds one from that explainer and checks its PPTX and PDF the same way; the Researcher account only notes that step in the report (decision 0070; `docs/PROGRESS.md`, Waiting on the owner).

The account is `e2e-researcher@kalavigyan.example`: Researcher (Deep allowed, no two-step), active on the roster, email verified, voice consent unset.

1. Provision it on the box, once a backend deploy has shipped `app.scripts.provision_e2e_account`. It prompts for the password (12 to 200 characters) and never prints it. Running it again resets the password, role, roster row and two-step, and ends the account's sessions.
   ```bash
   aws ssm start-session --target i-0a58a2feb528241aa --region ap-south-1
   cd /opt/kalavigyan/current/backend && sudo -u kalavigyan bash -c 'set -a; . /opt/kalavigyan/.env; set +a; .venv/bin/python -m app.scripts.provision_e2e_account'
   ```
2. Store the address and the same password as GitHub secrets, pasting each value at the prompt:
   ```bash
   gh secret set E2E_EMAIL --repo cxacraftecosystem-ui/KalaVigyan
   gh secret set E2E_PASSWORD --repo cxacraftecosystem-ui/KalaVigyan
   ```
3. Dispatch it (Actions, **E2E production**, Run workflow, or):
   ```bash
   gh workflow run e2e-production.yml --repo cxacraftecosystem-ui/KalaVigyan
   gh workflow run e2e-production.yml --repo cxacraftecosystem-ui/KalaVigyan -f questions=true
   gh workflow run e2e-production.yml --repo cxacraftecosystem-ui/KalaVigyan -f questions=true -f rivers_loaded=true
   ```

The run summary has a table per screen and width, and one per question. Two artifacts carry the run id: `e2e-production-screenshots-<run id>` and `e2e-production-report-<run id>` (`KalaVigyan_Eval-Run_<date>_<time>_<Width>-Screens_Report.json`, `..._Known-Answers_Report.json` with each answer's sentences, citations, sources and timing, and `..._Summary_Report.md`). Each question is one Detailed answer (`HYBRID` research) under the Researcher daily cap.

## Terraform

`infra/terraform`, Terraform ≥ 1.17.2, aws provider ~> 6.73, random ~> 3.9. The lock file is committed for linux/windows/darwin.

```bash
cd infra/terraform
terraform init
terraform plan      # must read "No changes" before any edit
```

- The instance and the bucket have `prevent_destroy`.
- `ami` and `user_data` are ignored after creation, so an edit to `user_data.sh` only affects a rebuilt box.
- State holds the media user's secret and the origin header value. It lives only in the state bucket.

Rebuilding the box:

1. Taint or replace `aws_instance.api` after lifting `prevent_destroy`.
2. Apply. The Elastic IP and CloudFront origin follow.
3. Run `seed_secrets.py --skip-github --skip-vercel` to render the env.
4. Run Deploy backend.

## Supabase lockdown

`infra/supabase/lockdown.sql` was applied through the Management API (`/v1/projects/inqbqiqspgvhfamupwuc/database/query`):

- the extensions in schema `extensions`;
- all privileges in `public` revoked from `anon` and `authenticated`, including default privileges;
- RLS on every public table;
- event trigger `enable_rls_on_new_tables`.

The Data API therefore exposes nothing. Re-run the file after anything recreates the schema.
