# Backend contract (lane: backend foundation)

Every API route is under `/api`. Health routes are at the root. JSON bodies use camelCase, matching DR (designer-portal) shapes unless a row below says otherwise. Auth is a bearer JWT in `Authorization: Bearer <token>`; the token carries `sub` (user id), `tv` (token version), `email`, `role`. Any password, role, 2FA or suspension change bumps the version, so older tokens answer 401.

Errors are `{"detail": "<sentence>"}` (FastAPI); validation errors are FastAPI's 422 list. Unhandled errors are `{"detail": "...", "requestId": "..."}` with status 500. Every response carries `X-Request-ID`; send one (8-64 chars of `[A-Za-z0-9._-]`) to correlate.

## Headers the web client must read (all exposed by CORS)

| Header | When | Meaning |
|---|---|---|
| `X-Access-Status` | 403/503 from `/auth/login`, `/auth/two-factor/verify` | `PENDING`, `REJECTED`, `SUSPENDED`, `NOT_RECORDED` (queue full, 503). Same values as DR `lib/accessRoster.ts`. |
| `X-Two-Factor-Setup-Required: 1` | 403 from any route except the 2FA setup routes, `/auth/me`, `/me`, `/auth/change-password`, `/auth/logout` | PROFESSOR or MASTER_ADMIN without TOTP. Send the user to the 2FA setup screen. |
| `X-Password-Change-Required: 1` | 401 from any route except `/auth/me`, `/me`, `/auth/change-password`, `/auth/logout` | `mustChangePassword` is set. |
| `X-Two-Factor-Required: 1` | 401 from key or budget changes; 400 from change-password without a password | Ask for a TOTP code and resend. |
| `X-Session-Token` | 200 from `/auth/change-password`, `/auth/two-factor/enable`, `/auth/two-factor/disable` | Replace the stored token with this one. |
| `X-Sign-In-Hint: PASSWORD_NOT_SET` | 401 from password login | Account exists without a password. |
| `X-Sign-In-Hint: EMAIL_UNVERIFIED` | 401 from password login | The address was never confirmed (no emailed link opened, no Google sign-in, no admin-issued password, never signed in). |
| `Retry-After` | 429 | Seconds. |
| `ETag` | 200/304 from `/crafts/catalogue` | Send it back as `If-None-Match`; a match answers 304 with no body. |

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
| GET | `/auth/config` | | `{googleEnabled, googleClientId, turnstileRequired, turnstileSiteKey, mailAvailable, signUpOpen}`. Draw the Google button only when `googleEnabled`; draw the email sign-up form only when `signUpOpen` (mail configured, and in production a Turnstile secret and site key); render the Turnstile widget with `turnstileSiteKey` when `turnstileRequired`. |
| POST | `/auth/google/nonce` | | `{nonce, expiresAt, clientId}`. 404 when Google is off. Pass `nonce` to `google.accounts.id.initialize({nonce})`; the backend checks it once from the ID token's `nonce` claim. |
| POST | `/auth/login` | `{email, password}` or `{googleIdToken, googleNonce?}` | `{accessToken, tokenType:"bearer", user}` or `{two_factor_required:true, challenge_token}`. 401 bad credentials or `X-Sign-In-Hint`, 403 + `X-Access-Status`, 429 + `Retry-After`. An unknown Google address creates a PENDING roster request. Google sign-in into an account whose address was never verified first clears any password and 2FA on it (bumping `tokenVersion` and revoking outstanding links), then marks it verified and adopts the roster `admitRole`. |
| POST | `/auth/two-factor/verify` | `{challenge_token, code}` (6 digits or a recovery code) | Same as a successful login. 401 wrong or dead challenge, 429 locked. |
| POST | `/auth/signup` | `{email, name, affiliation?, requestedRole:"STUDENT"|"RESEARCHER"|"PROFESSOR", profileUrl?, note?, ageAttested:true, privacyNoticeVersion, turnstileToken?}` | 202 `{status:"EMAIL_SENT", email}`, identical whether or not the address already has an account (no enumeration). No password is taken. A new address gets an unverified `User` (default role, no password), a `ConsentRecord` and a PENDING `RoleRequest`; an INVITE link (`/set-password?token=`, 3 days) is mailed. Opening it sets the password and `emailVerifiedAt`, adopts the roster `admitRole` if the row is ACTIVE, and only then adds a PENDING roster row (subject to `ACCESS_PENDING_MAX`). An existing unverified address without a password gets a fresh link; any other existing address gets nothing. 503 when mail is not configured, or in production when Turnstile is not configured; 400 when the Turnstile check fails; 422 without `ageAttested`. |
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

## Me and preferences (`/api`)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/me` | | Same as `GET /auth/me`: user object with `accessStatus`. Allowed while a password change or 2FA setup is pending. |
| GET | `/preferences/me` | | `{theme:"system"|"light"|"dark", reducedMotion, largerText, highContrast, updatedAt}`. The row is created with defaults (`system`, all false) on first read. |
| PUT | `/preferences/me` | `{theme?, reducedMotion?, largerText?, highContrast?}` | Same shape as GET. Omitted or null fields keep their value; unknown fields and other theme values are 422. Blocked (401/403 + header) while a password change or 2FA setup is pending. |

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
| DELETE | `/secrets/{key}` | body `{twoFactorCode}` (the web proxy forwards bodies, not this header); header `X-Two-Factor-Code` also accepted | key row; 401 + `X-Two-Factor-Required` without a valid code |
| POST | `/secrets/{key}/test` | | key row with the fresh verdict |

## Craft catalogue (`/api/crafts`)

| Method | Path | Body / query | Response |
|---|---|---|---|
| GET | `/crafts/catalogue` | `includeInactive` (bool, PROFESSOR and above; 403 otherwise). Header `If-None-Match` | DR `CraftCatalogue`: `{version, categories:[{id, slug, name, sortOrder, subCategories:[{id, slug, name, sortOrder, craftCount}]}], crafts:[{id, slug, name, localName, categoryId, subCategoryId, sourceSerial, stateOfOrigin[], stateOfPractice[], giStatus: "GI"|"NON_GI"|null, isCatchAll, craftCode, aliases[]}]}`. With `includeInactive` each craft also has `status` (`ACTIVE`/`LEGACY`/`MERGED`), `mergedIntoId`, `referenceCount` (null for active crafts). |

- Any signed-in role may read it. Headers `ETag: "<version>"` and `Cache-Control: private, no-cache`; a matching `If-None-Match` (strong, weak `W/` or `*`, comma lists) answers 304 with the same headers and no body.
- Read from the database (`CraftCategory`, `CraftSubCategory`, `Craft`, `CraftSpelling`, active `CraftAlias`). Categories by `sortOrder, name`; crafts active first, then category order, sub-category order, `sourceSerial`, name, id. `craftCount` counts active crafts.
- `aliases` are normalised spellings: every `CraftSpelling` sharing the craft's `craftCode` plus every active `CraftAlias.aliasNorm`, minus the craft's own normalised name, sorted.
- `version` is a SHA-256 over the rows and their `updatedAt`, so any edit or alias change moves the ETag. The DB-free `craft_master_loader.build_catalogue()` gives the same shape (its `version` differs) for tests and offline fixtures.
- Seeding: run `uv run python -m app.scripts.seed_crafts` in `backend/` after `uv run alembic upgrade head`. It upserts `seed_plan()` from the vendored JSON in `backend/app/data/` (9 categories, 36 sub-categories, 455 crafts, 50 `CraftCode`, 174 `CraftSpelling`, 2170 `CraftAlias`) and prints the counts as JSON. Re-running is safe: rows match on slug, code, spelling and (`craftId`, `aliasNorm`), existing ids and statuses are kept, and nothing is deleted. CI runs it after the migrations in `backend-checks.yml`, and `tests/db/test_craft_seed.py` seeds twice on emptied craft tables and checks the counts and ids do not change. Deploy: `infra/deploy/blue_green.sh` (infra lane) should run `./.venv/bin/python -m app.scripts.seed_crafts` from `backend/` with the env loaded, right after its `alembic upgrade head` and before the new colour starts; a non-zero exit should stop the release like a failed migration.
- Seed knowledge: run `uv run python -m app.scripts.seed_claims` in `backend/` after `seed_crafts`. It loads `backend/app/data/seed_claims.json` (`craft_master_loader.SEED_CLAIMS_FILE`) into `Source` (122, `evidenceKind` from the row, seed id and `importRef` in `externalIds`), `Concept` (582, `originRef` = seed key, `craftId`/`subCategoryId` resolved by slug), `ConceptEdge` (767, `relation` plus the upstream `sourceRelation`; `claimId` points at the edge's first EDGE claim), `Process` ("Seed process", variant `seed_claims`, one per craft with stages) and `ProcessStage` (67 stages that carry an ordinal), `Claim` (1,914, row values as given: `status`, `evidenceLevel`, `levelReason`, `origin=IMPORT`, `createdByKind=SYSTEM`), `ClaimSource` (3,015 citations with `locator`, `quote` up to 300 chars, `quoteCheck`, `relation`) and one `ReviewEvent` per claim (`actorKind=SYSTEM`, `systemActor=import`, `toStatus`/`toLevel` from the claim, `note` = `seed import <seed id>`). Every id is `uuid5(ID_NAMESPACE, "seed-claims:<kind>:<seed id>")` and every insert is `ON CONFLICT DO NOTHING`, so a re-run adds nothing and never overwrites a later correction. It prints `{"total", "inserted", "unresolvedSlugs"}` as JSON and exits 2 when a craft or sub-category slug is missing (run `seed_crafts` first). `--dry-run` builds the plan from the file with no database and prints the totals. Seed claims arrive as `status=PROPOSED` (crafts lane contract); per §0 nothing is gated on status, so retrieval and answering must not filter claims to `APPROVED`, only drop `REJECTED` and `RETRACTED`. Edge `ordinal`, `conditions`, `determinism` and concept `localTerms`, `category`, `provenanceKind`, `compares` have no columns and are not stored. `tests/db/test_claim_seed.py` checks the plan without a database (run with `RUN_DB_TESTS=1 -m "not db"`, since the `tests/db` folder name is skipped by default) and, against Postgres, seeds crafts then claims twice on emptied tables. Deploy and CI should run it right after `seed_crafts`.

## Knowledge, privacy and map (`/api`)

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/privacy/notice` | public | `{version, title, body (Markdown, from app/data/privacy_notice.md), publishedAt}`. `version` is what signup sends as `privacyNoticeVersion`. |
| GET | `/crafts/{slug}/profile` | signed in | Frontend contract §4.6 `CraftProfile` (`craft` also carries `path`). A MERGED slug answers with its target's profile; unknown slug 404. `science` is `[]` until reactions are stored. Claims with status DRAFT, REJECTED or RETRACTED, non-OPEN sensitivity, or no visible citation are left out; PROPOSED seed claims show. |
| GET | `/map/crafts` | signed in | `[{key, name, latitude, longitude, total, crafts:[{slug, name, path}]}]`: one point per state of practice (a point on the state's surface, from `AdminState.geom`) plus one per district or point `CraftLocation`. |
| GET | `/answers/config` | signed in | `{modes, defaultMode:"HYBRID", voice:{configured:false, languages:[]}, languages:[{code:"en", label:"English"}]}`; `modes` are those the asker may use: `VERIFIED`, `HYBRID` for every role, `DEEP` for researchers and above. |
| POST | `/answers/stream` | signed in; `DEEP` needs `ASK_DEEP` (403), the others `ASK_STANDARD`; 30 per 10 min per user (429 + `Retry-After`) | `text/event-stream` per frontend contract §4.5 and `docs/contracts/research.md` (answer stream, the answering service): `status` steps while it works, `match`, then for `VERIFIED` the stored `VERIFIED`/`REVIEWED` claims, and for `HYBRID`/`DEEP` planner, live research, composer and write-back, then `source`, `section`, `sentence`, `open_question`, `follow_ups`, or `not_enough_evidence`; `error` on failure; `done {answerId}` last. A `: keep-alive` comment after 60 s of silence. Every frame is validated (`research/stream.event_frame`). |

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
| GET | `/settings/ai-routing` | | `{tasks: taskState[], providers: [{id, name, keyName, keyState:"ABSENT"|"UNTESTED"|"PASSING"|"FAILING", publicTextOnly, models:[{id, label, tasks[]}]}]}` |
| GET | `/settings/ai-routing/{task}` | | task state |
| PUT | `/settings/ai-routing/{task}` | `{routes:[{provider, model, enabled?, maxOutputTokens?, temperature?}]}` (1-8) | task state; routes whose key has not passed a test sink below passing ones (`normalised`, `normalisedNote`); 422 for an unsupported provider/model pair |
| POST | `/settings/ai-routing/{task}/test` | `{provider, model?}` | task state after testing that provider's key |
| GET | `/settings/ai-budget` | | `{monthlyCeilingUsd, mediaCapUsd, roleDailyUsd:{ROLE: number|null}, degradeAtFraction, signUpMode, domainAllowlist}` (MANAGE_CEILINGS) |
| PUT | `/settings/ai-budget` | any of the above + `twoFactorCode` | same shape; 422 if media cap exceeds the monthly ceiling |

Defaults (seeded in `AppSetting`): ceiling $800/month, media sub-cap $150/month, per-user daily caps STUDENT $0.50, RESEARCHER $3, PROFESSOR $5, MASTER_ADMIN none, degrade at 80%. Budget months and days run on Asia/Kolkata.

## Usage (`/api/usage`)

| Method | Path | Response |
|---|---|---|
| GET | `/usage/summary?month=YYYY-MM` (VIEW_USAGE) | `{month, monthlyCeilingUsd, mediaCapUsd, spentUsd, mediaSpentUsd, reservedUsd, fraction, degraded, calls, refusedCalls, failedCalls, byTask, byProvider, byModel, byRole: [{key, costUsd, calls, inputTokens, outputTokens, ok}], byDay:[{day, costUsd, calls}], topUsers:[{userId, name, email, role, costUsd, calls}]}` |
| GET | `/usage/report?from=ISO&to=ISO` (VIEW_USAGE) | `{from, to, ceilingUsd, spentThisMonthUsd, spentUsd, calls, failures, byTask:[{task, label, calls, failures, inputTokens, outputTokens, costUsd}], byProvider:[{provider, name, model, calls, failures, costUsd, p95LatencyMs|null}], byDay:[{day, calls, costUsd}]}`. `from` defaults to the start of the IST month, `to` to now; a date without a zone is read as IST; days are IST. Reserved (unsettled) events are left out. 422 when `to` is before `from`. |
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
- Data/ETL lane: owns the district and environmental tables and the source corpus. The craft seed (455 crafts, `CraftCode`, `CraftSpelling`, `CraftAlias`) belongs to this lane: `app/services/craft_seed.py` and `app/scripts/seed_crafts.py`, fed by the vendored JSON in `backend/app/data/`. The ETL lane reads crafts by slug or `craftCode` and must not insert or rename catalogue rows; changes to the catalogue go through the vendored JSON and the seeder.
- Infra lane: provides `DATABASE_URL` (Supabase session pooler, port 5432) and the names in `backend/.env.example` on the box. `blue_green.sh` runs `seed_crafts`, `seed_claims` and `seed_districts` after `alembic upgrade head` and stops the release if one fails, then `sync_portal_crafts` (a warning on failure); `backend-checks.yml` runs the same three before the DB tests. Client IP for rate limits: `x-viewer-address` when `x-web-proxy-secret` matches `WEB_PROXY_SECRET` (hmac compare), otherwise the `FORWARDED_CLIENT_HOPS` rule. Settings errors name fields only (`hide_input_in_errors`, `SettingsError`). The bucket and Brave key are read as `S3_BUCKET` and `BRAVE_SEARCH_API_KEY` (old `AWS_S3_BUCKET` and `BRAVE_API_KEY` still accepted). First master admin: `MASTER_ADMIN_EMAIL` signs in with Google, or the operator runs `python -m app.scripts.seed_admin` (password read from stdin) in `backend/`.
- `shared/roles.json`, when added, holds `{"ranks": {"MASTER_ADMIN": 60, "PROFESSOR": 40, "RESEARCHER": 30, "STUDENT": 15}}`; a backend test checks it matches.
