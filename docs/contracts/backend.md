# Backend contract (lane: backend foundation)

Every API route is under `/api`. Health routes are at the root. JSON bodies use camelCase, matching DR (designer-portal) shapes unless a row below says otherwise. Auth is a bearer JWT in `Authorization: Bearer <token>`; the token carries `sub` (user id), `tv` (token version), `email`, `role`. Any password, role, 2FA or suspension change bumps the version, so older tokens answer 401.

Errors are `{"detail": "<sentence>"}` (FastAPI); validation errors are FastAPI's 422 list. Unhandled errors are `{"detail": "...", "requestId": "..."}` with status 500. Every response carries `X-Request-ID`; send one (8-64 chars of `[A-Za-z0-9._-]`) to correlate.

## Headers the web client must read (all exposed by CORS)

| Header | When | Meaning |
|---|---|---|
| `X-Access-Status` | 403/503 from `/auth/login`, `/auth/two-factor/verify` | `PENDING`, `REJECTED`, `SUSPENDED`, `NOT_RECORDED` (queue full, 503). Same values as DR `lib/accessRoster.ts`. |
| `X-Two-Factor-Setup-Required: 1` | 403 from any route except the 2FA setup routes, `/auth/me`, `/auth/change-password`, `/auth/logout` | PROFESSOR or MASTER_ADMIN without TOTP. Send the user to the 2FA setup screen. |
| `X-Password-Change-Required: 1` | 401 from any route except `/auth/me`, `/auth/change-password`, `/auth/logout` | `mustChangePassword` is set. |
| `X-Two-Factor-Required: 1` | 401 from key or budget changes; 400 from change-password without a password | Ask for a TOTP code and resend. |
| `X-Session-Token` | 200 from `/auth/change-password`, `/auth/two-factor/enable`, `/auth/two-factor/disable` | Replace the stored token with this one. |
| `X-Sign-In-Hint: PASSWORD_NOT_SET` | 401 from password login | Account exists without a password. |
| `Retry-After` | 429 | Seconds. |

## User object (`serialize_user`)

```
{ id, email, name, avatarUrl, role, roleLabel, authProvider, affiliation, mustChangePassword,
  twoFactorEnabled, twoFactorRequired, twoFactorSetupRequired, hasPassword, capabilities: string[],
  accessStatus?, emailVerifiedAt, firstLoginAt, lastLoginAt, passwordSetAt, ageAttestedAt, createdAt, updatedAt }
```
Roles: `MASTER_ADMIN` (60), `PROFESSOR` (40), `RESEARCHER` (30), `STUDENT` (15). `capabilities` is the list from `app/core/roles.py` (`Capability`): ASK_STANDARD, ASK_DEEP, VOICE, GENERATE_IMAGE, GENERATE_VIDEO, SAVE_EXPORT, READ_RESEARCHER_QUOTES, PROPOSE_KNOWLEDGE, RUN_ENRICHMENT, ACCEPT_ALIASES, MARK_CLAIM_LEVEL, RETRACT_CLAIM, SHARE_MEDIA, HANDLE_OBJECTIONS, MANAGE_ACCESS, LIST_USERS, INVITE_PROFESSORS, CHANGE_ROLES, DISABLE_USERS, MANAGE_KEYS, MANAGE_ROUTING, MANAGE_QUOTAS, MANAGE_CEILINGS, MANAGE_DATASETS, VIEW_USAGE, VIEW_EVALUATION, VIEW_AUDIT_LOG. Gate nav items on capabilities, not on role names. No review gates exist (PLAN §0).

## Health

| Method | Path | Response |
|---|---|---|
| GET | `/health` | `{status:"ok", release, version}` |
| GET | `/health/ready` | `{status:"ready"|"unavailable", database: bool, latencyMs}`; 503 when the database does not answer in 3 s |

## Auth (`/api/auth`)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/auth/config` | | `{googleEnabled, googleClientId, turnstileRequired, mailAvailable}`. Draw the Google button only when `googleEnabled`. |
| POST | `/auth/google/nonce` | | `{nonce, expiresAt, clientId}`. 404 when Google is off. Pass `nonce` to `google.accounts.id.initialize({nonce})`; the backend checks it once from the ID token's `nonce` claim. |
| POST | `/auth/login` | `{email, password}` or `{googleIdToken}` | `{accessToken, tokenType:"bearer", user}` or `{two_factor_required:true, challenge_token}`. 401 bad credentials, 403 + `X-Access-Status`, 429 + `Retry-After`. An unknown Google address creates a PENDING roster request. |
| POST | `/auth/two-factor/verify` | `{challenge_token, code}` (6 digits or a recovery code) | Same as a successful login. 401 wrong or dead challenge, 429 locked. |
| POST | `/auth/signup` | `{email, name, password (>=10), affiliation?, ageAttested:true, privacyNoticeVersion, turnstileToken?}` | 202 `{accessStatus:"PENDING"|"ACTIVE", email}`. The account exists but cannot sign in until an admin approves the roster row. 409 if the address has an account. |
| POST | `/auth/logout` | | `{ok:true}` (stateless; drop the token) |
| GET | `/auth/me` | | user object with `accessStatus` |
| POST | `/auth/consent` | `{kind:"PRIVACY_NOTICE"|"VOICE_NOTICE", noticeVersion}` | `{kind, noticeVersion, acceptedAt}` |
| POST | `/auth/google/link-nonce` | | `{nonce, expiresAt, clientId}` for linking from a signed-in session |
| POST | `/auth/google/link` | `{googleIdToken, password? , twoFactorCode?}` | user object. Needs a fresh password or TOTP; the Google email must match. |
| POST | `/auth/forgot-password` | `{email}` | `{message}` always the same; 429 after 5/hour per IP. Link goes to `${PUBLIC_WEB_URL}/set-password?token=...`, valid 30 min. |
| GET | `/auth/set-password?token=` | | `{valid, reason, purpose}`; reasons `MISSING`, `MALFORMED`, `EXPIRED`, `REVOKED`, `SPENT`, `UNKNOWN_ACCOUNT`; purpose `INVITE`/`RESET` |
| POST | `/auth/set-password/check` | `{token}` | same as above (token out of the URL) |
| POST | `/auth/set-password` | `{token, password (>=10)}` | `{ok:true}`; ends every session |
| POST | `/auth/change-password` | `{currentPassword, newPassword, twoFactorCode?}` | `{ok:true}` + `X-Session-Token` |
| POST | `/auth/password-links` | `{userId, delivery:"COPY_LINK"|"EMAIL"}` | 201 `{id, link|null, expiresAt, purpose, deliveredBy}`; MANAGE_ACCESS and a lower-ranked target |
| POST | `/auth/password-links/{id}/revoke` | | `{ok:true}` |

### Two-step (`/api/auth/two-factor`), DR shapes

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/auth/two-factor` | | `{enabled, pending, required, recovery_codes_remaining, enabled_at}` |
| POST | `/auth/two-factor/setup` | | `{secret, otpauth_uri, qr_svg}` (409 if on) |
| POST | `/auth/two-factor/setup/cancel` | | 204 |
| POST | `/auth/two-factor/enable` | `{code}` | `{recovery_codes: string[10], accessToken}` + `X-Session-Token` (the old token stops working) |
| POST | `/auth/two-factor/disable` | `{code}` | `{ok:true, accessToken}`; 409 for PROFESSOR and MASTER_ADMIN (mandatory) |
| POST | `/auth/two-factor/recovery-codes` | `{code}` (TOTP only) | `{recovery_codes}` |

## Access roster (`/api/access`), DR `/access/roster` semantics

Capability MANAGE_ACCESS (PROFESSOR, MASTER_ADMIN). A professor admits RESEARCHER and STUDENT only; the master admin admits any role. Statuses `ACTIVE`, `PENDING`, `REJECTED`, `SUSPENDED`.

Roster row: `{id, email, fullName, affiliation, status, admitRole, joinedAt, requestedAt, attemptCount, lastAttemptAt, decidedAt, decidedById, decidedByName, firstSeenAt, notes, createdAt, updatedAt, addedById, addedByName}`.

| Method | Path | Body / query | Response |
|---|---|---|---|
| GET | `/access/roster/pending-count` | | `{pending, capacity, capReached}` |
| GET | `/access/roster` | `page, pageSize (<=200), search, status (repeatable or comma list), roles (role names or "default"), dateField (added, requested, decided, joined, firstSeen), dateFrom, dateTo, sort (added, email, name, standing, joined, requested, decided, firstSeen, attempts), dir` | `{items, total, page, pageSize, pages, roleMatchTruncated:false, assignableRoles}` |
| POST | `/access/roster` | `{email, fullName?, role?, notes?, affiliation?, password?, mustChangePassword?}` | 201 row + `{accountPromotionHeld, accountCreated}`; 409 if listed |
| POST | `/access/roster/{id}/decision` | `{decision:"APPROVE"|"REJECT", role?, notes?}` | row + `{accountPromotionHeld}`. Approve also sets the role on an existing account (token version bumped). Reject ends sessions. |
| PATCH | `/access/roster/{id}` | `{fullName?, role?, notes?, affiliation?}` | row + `{accountPromotionHeld}` |
| DELETE | `/access/roster/{id}` | | row with `status:"SUSPENDED"`; ends sessions |

## Manage users (`/api/users`)

List and view: LIST_USERS (PROFESSOR+). Role changes, suspend, restore, 2FA reset, delete: master admin only.

| Method | Path | Body / query | Response |
|---|---|---|---|
| GET | `/users` | `search, role, access (ACTIVE, PENDING, REJECTED, SUSPENDED, NOT_LISTED), sort (created, name, email, role, lastLogin), dir, page, pageSize (<=100)` | `{items: user[], total, page, pageSize, pages}`; each item has `accessStatus` |
| GET | `/users/{id}` | | user |
| PATCH | `/users/{id}` | `{name?, role?, affiliation?, mustChangePassword?}` | user |
| POST | `/users/{id}/suspend` | `{reason?}` (optional body) | user with `accessStatus:"SUSPENDED"`; sessions end |
| POST | `/users/{id}/restore` | | user with `accessStatus:"ACTIVE"` |
| POST | `/users/{id}/sign-out-everywhere` | | user |
| DELETE | `/users/{id}/two-factor` | | user (2FA off, sessions end; the user must set it up again at next sign-in if their role requires it) |
| DELETE | `/users/{id}` | | 204 (soft delete, `deletedAt`) |

## API keys (`/api/secrets`), MANAGE_KEYS (master admin)

There is no reveal route. Changes need a TOTP step-up.

Key row: `{key, label, description, group, formatOnly, configured, source:"database"|"environment"|"unset", overrideUnreadable, hint (last 4), lastStatus:"UNKNOWN"|"OK"|"FAILED", lastCheckedAt, lastError, updatedBy, updatedAt}`.

Keys: GEMINI_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY, ELEVENLABS_API_KEY, BRAVE_SEARCH_API_KEY, EXA_API_KEY, TAVILY_API_KEY, OPENALEX_API_KEY, SEMANTIC_SCHOLAR_API_KEY, CORE_API_KEY, SPRINGER_NATURE_API_KEY, ELSEVIER_API_KEY, ELSEVIER_INSTTOKEN, WILEY_TDM_TOKEN, DATA_GOV_IN_API_KEY, GOOGLE_CLIENT_ID.

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/secrets` | | key row[] |
| PUT | `/secrets/{key}` | `{value, twoFactorCode}` | key row; 401 + `X-Two-Factor-Required` without a valid code; 404 unknown key |
| DELETE | `/secrets/{key}` | header `X-Two-Factor-Code` | key row |
| POST | `/secrets/{key}/test` | | key row with the fresh verdict |

## Settings hub (`/api/settings`)

`/settings/ai-routing` generalises DR `/settings/transcription-providers` to one ordered list per task (stored in `RoutePolicy`).

Routable tasks: PLAN, WEB_READ, COMPOSE, VOICE_TURN, EXTRACT, EMBED, EVAL_JUDGE, IMAGE, VIDEO. WEB_READ and EXTRACT are public-text tasks; DeepSeek (PUBLIC_TEXT_ONLY) is offered and accepted only there.

Task state:
```
{ task, label, publicText, normalised, normalisedNote,
  routes: [{ordinal, provider, providerLabel, model, modelLabel, enabled, maxOutputTokens, temperature, supported,
            dataClass, keyName, keyLabel, configured, keyState:"ABSENT"|"UNTESTED"|"PASSING"|"FAILING",
            rankable, frozenReason, testedAt, testError}],
  effectiveChain: ["PROVIDER:model"], verifiedChain: ["PROVIDER:model"],
  availableModels: [{provider, model, label, priceVerified}] }
```

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/settings/ai-catalogue` | | `{providers:[{provider, label, managedKey, consoleUrl, pricingUrl, dataClass, defaultModel, models:[{id, label, note, pricePerMTok:[in,out]|null, pricePerUnit, unit, priceVerified, tasks}]}], tasks}` |
| GET | `/settings/ai-routing` | | `{tasks: taskState[]}` |
| GET | `/settings/ai-routing/{task}` | | task state |
| PUT | `/settings/ai-routing/{task}` | `{routes:[{provider, model, enabled?, maxOutputTokens?, temperature?}]}` (1-8) | task state; routes whose key has not passed a test sink below passing ones (`normalised`, `normalisedNote`); 422 for an unsupported provider/model pair |
| POST | `/settings/ai-routing/{task}/test` | `{provider}` | task state after testing that provider's key |
| GET | `/settings/ai-budget` | | `{monthlyCeilingUsd, mediaCapUsd, roleDailyUsd:{ROLE: number|null}, degradeAtFraction, signUpMode, domainAllowlist}` (MANAGE_CEILINGS) |
| PUT | `/settings/ai-budget` | any of the above + `twoFactorCode` | same shape; 422 if media cap exceeds the monthly ceiling |

Defaults (seeded in `AppSetting`): ceiling $800/month, media sub-cap $150/month, per-user daily caps STUDENT $0.50, RESEARCHER $3, PROFESSOR $5, MASTER_ADMIN none, degrade at 80%. Budget months and days run on Asia/Kolkata.

## Usage (`/api/usage`)

| Method | Path | Response |
|---|---|---|
| GET | `/usage/summary?month=YYYY-MM` (VIEW_USAGE) | `{month, monthlyCeilingUsd, mediaCapUsd, spentUsd, mediaSpentUsd, reservedUsd, fraction, degraded, calls, refusedCalls, failedCalls, byTask, byProvider, byModel, byRole: [{key, costUsd, calls, inputTokens, outputTokens, ok}], byDay:[{day, costUsd, calls}], topUsers:[{userId, name, email, role, costUsd, calls}]}` |
| GET | `/usage/me` | `{todayUsd, dailyCapUsd, allowances:{VOICE_SECONDS, IMAGE, VIDEO}, platformDegraded}` |

## AI router (for the answering, voice, media and enrichment lanes)

`app.providers.router.run(task, *, system, user, json_schema=None, max_tokens=None, temperature=None, texts=None, principal=Principal(user_id, role), request_budget_usd=None) -> RouterResult(text, embeddings, provider, model, cost_usd, degraded, attempts, usage_event_id, ...)`.

- Walks `RoutePolicy` in ordinal order; skips routes the catalogue does not support for the task and PUBLIC_TEXT_ONLY providers on private tasks.
- `rate_limit`/`unavailable` with Retry-After <= 2 s retries the same route once, otherwise moves on; `auth` marks the key FAILED and moves on; `refusal`/`bad_request` raise `RouterError(kind)` at once.
- Before each call it reserves the estimate as a `UsageEvent` (`RESERVED`) under a Postgres advisory lock, refusing with `RouterError(kind="ceiling", reason="MONTHLY_CEILING"|"MEDIA_CAP"|"ROLE_DAILY_CAP"|"REQUEST_BUDGET")` and a `REFUSED_CEILING` row. After the call it settles the row to `OK` with the real cost, or `ERROR`/`REFUSED_PROVIDER`. No DB session is held across a provider call.
- `degraded=True` once the month passes 80% of the ceiling; COMPOSE, EXTRACT, VOICE_TURN, PLAN and WEB_READ then try the cheapest route first. The caller drops Deep to Hybrid.
- EMBED returns 1536-dimension vectors (`texts=[...]`).
- IMAGE and VIDEO are not called through `run`; the media lane calls `router.reserve(...)` and `router.settle(...)` around its own job so the media sub-cap applies.
- Unverified prices (gpt-6.1-terra, gemini-4-argon, DeepSeek models, Omni video) are budgeted at $5/$30 per MTok, $0.134/image, $0.15/s until the owner sets `AI_MODEL_PRICES` (`{"model-id": {"in": x, "out": y}}` or `{"unit": z}`) in `AppSetting`.

## Data model

Migration `backend/migrations/versions/0001_initial_schema.py` creates every PLAN §4 table with quoted PascalCase names and camelCase columns, extensions `vector`, `postgis`, `pg_trgm`, `unaccent`, `citext`, RLS on every table with `anon`/`authenticated` revoked when those roles exist, append-only triggers on `AuditLog` and `ReviewEvent`, and seeds for `Provider`, `RoutePolicy` (PLAN §9 defaults), `AppSetting` and `QuotaPolicy`. Added beyond §4: `AuthNonce`, `SecretTestResult`, `SavedItem`, `Compound`, `Material`, `StageMaterial`, `AnswerSentence`, `AnswerCitation` (per-sentence citations with quote, locator, URL), `Job` (queue), `User.tokenVersion`, `User.emailVerifiedAt`. `ClaimOrigin` and `SourceOrigin` gain `LIVE_RESEARCH` so live research can write back cited claims (§0). Claims default to `status=APPROVED` because nothing waits for review; `evidenceLevel` is the label.

DR columns not carried: Aadhaar columns on `User`, `Craft.workshopId` (no Workshop table here). IDs are uuid (`gen_random_uuid()`), not DR's cuid.

## Assumptions about other lanes

- Frontend: the DR screens it ports call these paths with the `/api` prefix. DR's `/secrets/{key}/reveal` and `/settings/transcription-providers` do not exist here; use `/settings/ai-routing` instead. Secrets changes must collect a TOTP code. Suspension of an account is `/users/{id}/suspend`, not a roster DELETE (both work).
- Data/ETL lane: owns the craft seed (455 crafts, `CraftCode`, `CraftSpelling`, `CraftAlias`) and district tables; this lane only creates the tables. The vendored JSON in `backend/app/data/` is left untouched.
- Infra lane: provides `DATABASE_URL` (Supabase session pooler, port 5432) and the names in `backend/.env.example` on the box. First master admin: `MASTER_ADMIN_EMAIL` signs in with Google, or the operator runs `python -m app.scripts.seed_admin` (password read from stdin) in `backend/`.
- `shared/roles.json`, when added, holds `{"ranks": {"MASTER_ADMIN": 60, "PROFESSOR": 40, "RESEARCHER": 30, "STUDENT": 15}}`; a backend test checks it matches.
