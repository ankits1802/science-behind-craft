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
| IAM | user `kalavigyan-media` (API's S3 key), role + instance profile `kalavigyan-box`, role `kalavigyan-deploy` (GitHub OIDC, `repo:ankits1802/science-behind-craft:ref:refs/heads/main` only) |
| Parameter Store | `/kalavigyan/env/*` (SecureString, one parameter per env key, the box's source of truth). `/kalavigyan/db-password` (Supabase DB password backup) |
| Database | Supabase project `science-behind-craft`, ref `inqbqiqspgvhfamupwuc`, org `pifvglrcqwrizapmooik`, ap-south-1, Postgres 17.11. Session pooler `aws-1-ap-south-1.pooler.supabase.com:5432`, user `postgres.inqbqiqspgvhfamupwuc` |
| Web | Vercel project `kalavigyan` (`prj_5hRNy7S9CS4fkhVVBRW5mbmAAUSd`), team `team_pcTf4Alb2DCIwq2IZcdu00dS`, root `frontend`, Node 26.x, no Git link, `https://kalavigyan.vercel.app` |
| Repository | `github.com/ankits1802/science-behind-craft` (private) |

### On the box

| Path / unit | Role |
|---|---|
| `/opt/kalavigyan/releases/<sha>` | One directory per release: `backend/` with its own `.venv`, `infra/deploy/`, `REVISION` |
| `/opt/kalavigyan/slot-8000`, `slot-8001`, `current` | Symlinks used by blue/green. nginx proxies to exactly one port. |
| `/opt/kalavigyan/.env`, `fetcher.env` | Rendered from Parameter Store by `kv-render-env` (0640 root:kalavigyan) |
| `kv-api@8000`, `kv-api@8001` | The two API colours (user `kalavigyan`, MemoryMax 3000M, Restart=always) |
| `kv-worker`, `kv-fetcher` | Started only once a release ships `app.worker` / `app.fetcher` |
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

Every secret is in three places: a GitHub Actions secret, `/kalavigyan/env/<NAME>` in Parameter Store, and `/opt/kalavigyan/.env` on the box.

- GitHub secrets: `DATABASE_URL`, `JWT_SECRET`, `SECRETS_ENCRYPTION_KEY`, `TWO_FACTOR_ENCRYPTION_KEY`, `ORIGIN_VERIFY_SECRET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `GOOGLE_CLIENT_ID`, `MASTER_ADMIN_EMAIL`, `MASTER_ADMIN_NAME`.
- GitHub variables: `AWS_REGION`, `AWS_DEPLOY_ROLE_ARN`, `EC2_INSTANCE_ID`, `MEDIA_BUCKET`, `API_BASE_URL`, `CLOUDFRONT_DISTRIBUTION_ID`, `WEB_ORIGIN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
- Parameter Store also holds non-secret config (`APP_ENV`, `BACKEND_CORS_ORIGINS`, `FORWARDED_CLIENT_HOPS`, `REDIS_URL`, `SEARXNG_URL`, …). See `infra/.env.example` for every name.
- Copied from the DR box without printing them: `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `GOOGLE_CLIENT_ID`, `MASTER_ADMIN_EMAIL`, `MASTER_ADMIN_NAME`.

**The owner still has to add these** (none of them were on the DR box):

| Name | Where |
|---|---|
| `VERCEL_TOKEN` | GitHub secret. Create it at vercel.com → Account → Tokens, scoped to the team. Deploy frontend fails until it exists. |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `BRAVE_API_KEY` | GitHub secrets. The next backend deploy copies them into Parameter Store and the box. |
| `MAIL_FROM_ADDRESS` | Parameter Store, once an SES identity is chosen for KalaVigyan mail |
| Google OAuth client | Add `https://kalavigyan.vercel.app` to the client's Authorized JavaScript origins |

To change a secret: `gh secret set NAME --repo ankits1802/science-behind-craft`, then run **Deploy backend**. The deploy copies changed GitHub secrets into Parameter Store and re-renders the box `.env`. For config that is not a GitHub secret:

```bash
aws ssm put-parameter --region ap-south-1 --name /kalavigyan/env/NAME --type SecureString --overwrite --cli-input-json file://value.json
sudo kv-render-env && sudo kv-blue-green restart     # on the box
```

`infra/scripts/seed_secrets.py` rebuilds the whole set. It keeps existing generated keys, takes the Terraform outputs, and writes Parameter Store, GitHub, Vercel and the box. Run it with a Python that has `boto3` and `cryptography`, passing `--terraform <path to terraform>`. `--copy-from-instance <id>` copies the provider keys from another box's `.env` over an RSA-encrypted SSM channel.

Never rotate `TWO_FACTOR_ENCRYPTION_KEY` or `SECRETS_ENCRYPTION_KEY` by overwriting them: stored data is encrypted with them.

## Deploy

Automatic: a push to `main` → `Checks` → **Deploy backend** → **Deploy frontend**. Both can also be run from the Actions tab (`workflow_dispatch`, optional `ref`).

Deploy backend (`.github/workflows/deploy-backend.yml`):

1. Assumes `kalavigyan-deploy` through GitHub OIDC (no static AWS keys in GitHub).
2. Copies changed secrets into `/kalavigyan/env`.
3. Uploads `git archive HEAD backend infra/deploy` to `s3://kalavigyan-media-626159998512/deploy/backend/<sha>/KalaVigyan_API_Release-Build_<sha12>.tar.gz`.
4. Runs `infra/deploy/release.sh <sha>` on the box over SSM `AWS-RunShellScript`, logging to `deploy/logs/<sha>/`. The script installs units, renders the env, builds the venv with uv, then `blue_green.sh release <sha>`:
   1. migrate (`alembic upgrade head`) while the old colour serves;
   2. start the other colour;
   3. wait for `/health`;
   4. switch nginx;
   5. stop the old colour;
   6. restart the worker and fetcher.

   It keeps the newest 5 releases.
5. Smoke-tests `https://d89rsltpszebp.cloudfront.net/health`.

Running the same sha again re-renders the env and restarts the live colour.

Deploy frontend (`.github/workflows/deploy-frontend.yml`): `vercel pull` → assert root `frontend` and `NEXT_PUBLIC_API_URL` → `vercel build --prod` → `vercel deploy --prebuilt --prod` → smoke `https://kalavigyan.vercel.app/`.

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
