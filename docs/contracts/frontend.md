# Frontend lane contract

The web client (`frontend/`, Next.js 16 App Router, React 19, Tailwind 4) is a port of the designer-portal (DR) shell. Wherever DR already has a route, the client calls it in DR's exact shape; the backend lane ports those routes unchanged. This file lists what the client assumes, and every route that is new for KalaVigyan.

## 1. Transport and session

- Every call goes to the same origin under `/api/*`. `frontend/proxy.ts` rewrites it to `API_ORIGIN` (falls back to `NEXT_PUBLIC_API_URL`) and adds the session token as `Authorization: Bearer` plus the shared proxy secret header `x-web-proxy-secret` (env `WEB_PROXY_SECRET`, same value on the API). This is DR's `lib/server/apiProxy.ts` unchanged.
- Sign-in, two-step verify, change-password and logout go through the Next route handlers in `frontend/app/api/{auth,session}/*`, which set and clear the `__Host-session` / `__Host-session-marker` cookies (DR shape). The API returns the token in the body of `POST /auth/login` and `POST /auth/two-factor/verify` exactly as DR does, and a fresh one in the `X-Session-Token` response header of `POST /auth/change-password`.
- Headers the client reads: `x-access-status` (`PENDING`, `REJECTED`, `SUSPENDED`, `NOT_RECORDED`) on a refused sign-in, `x-sign-in-hint`, `x-password-change-required: 1`, `x-two-factor-required`, `x-confirm-provider`.
- Env names (values never in the repo): `API_ORIGIN`, `NEXT_PUBLIC_API_URL`, `WEB_PROXY_SECRET`, `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, `NEXT_PUBLIC_APP_VERSION`, `NEXT_PUBLIC_BUILD_NUMBER`. See `frontend/.env.example`.

## 2. Roles

`UserRole` = `MASTER_ADMIN` (60), `PROFESSOR` (40), `RESEARCHER` (30), `STUDENT` (15), mirrored in `frontend/lib/permissions.ts` (`ROLE_RANK`). Route guards and the backend dependency each one mirrors:

| Path | Who | Backend dependency name |
|---|---|---|
| `/admin` | Master admin | `require_master_admin` |
| `/admin/keys`, `/admin/routing`, `/admin/usage` | Master admin | `require_master_admin` |
| `/admin/users` | Professor and above | `require_professor` |
| `/admin/access` | Professor and above | `require_access_roster_manager` |

A professor assigns only `RESEARCHER` and `STUDENT`; only the master admin changes roles of professors, suspends accounts and resets another account's two-step verification.

## 3. Routes ported from DR, called in DR's shape

`GET /me`, `GET|PUT /preferences/me`, `POST /auth/login` (`{email,password}` or `{googleIdToken, googleNonce}`), `POST /auth/logout`, `POST /auth/change-password`, `POST /auth/forgot-password`, `GET /auth/set-password`, `POST /auth/set-password/check`, `POST /auth/set-password`, `POST /auth/password-links`, `GET /auth/two-factor`, `POST /auth/two-factor/setup`, `POST /auth/two-factor/setup/cancel`, `POST /auth/two-factor/enable`, `POST /auth/two-factor/disable`, `POST /auth/two-factor/recovery-codes`, `POST /auth/two-factor/verify`, `GET /access/roster` (`page,pageSize,search,status` and the roster filter params), `GET /access/roster/pending-count`, `POST /access/roster`, `POST /access/roster/{id}/decision`, `PATCH /access/roster/{id}`, `DELETE /access/roster/{id}`, `GET /users` (`search,role,page,pageSize`), `PATCH /users/{id}` (`{role}`), `DELETE /users/{id}/two-factor`, `POST /users/{id}/sign-out-everywhere`, `GET /secrets`, `PUT /secrets/{key}`, `DELETE /secrets/{key}`, `POST /secrets/{key}/test`, `GET /crafts/catalogue` (ETag, `If-None-Match`, DR `CraftCatalogue` body).

Not called, by design: `GET /secrets/{key}/reveal` (PLAN §9, §15).

Changes to DR shapes the client assumes:

- `PUT /secrets/{key}` body is `{value, twoFactorCode}` and `DELETE /secrets/{key}` carries `{twoFactorCode}`: a six-digit TOTP step-up (PLAN §12, keys rotate with TOTP step-up). A wrong or missing code is a 401 with `x-two-factor-required: 1` and a sentence in `detail`; `apiFetch` keeps the session for that 401.
- `User` adds `affiliation`, `twoFactorRequired` (true for PROFESSOR and MASTER_ADMIN until two-step is on; the shell then shows only the setup card), `isActive`, `suspendedAt`.
- `POST /auth/login` with Google also takes `googleNonce`, the value from §4.1; the API verifies it once, with `aud`, `iss`, `exp` and `email_verified`.

## 4. New routes

### 4.1 Auth and sign-up

- `POST /auth/google/nonce` → `{nonce}`. Public. A fresh single-use nonce per attempt; the client passes it to `google.accounts.id.initialize({nonce})` and back with the ID token.
- `GET /auth/config` → `{signUpOpen, turnstileRequired, turnstileSiteKey|null, googleEnabled, googleClientId|null, mailAvailable}`. The sign-up page draws the email form only when `signUpOpen`, and the Turnstile widget when `turnstileRequired` and a site key is given; otherwise it offers Google only.
- `POST /auth/signup` body `{name, email, affiliation, requestedRole, profileUrl|null, ageAttested: true, privacyNoticeVersion|null, turnstileToken|null}` → `202 {status: "EMAIL_SENT", email}`, the same for every address. No password: the emailed link (`/set-password?token=`) confirms the address and sets it, and only then is the PENDING request recorded. `requestedRole` is one of `STUDENT`, `RESEARCHER`, `PROFESSOR`. Password sign-in into a never-confirmed account answers 401 with `x-sign-in-hint: EMAIL_UNVERIFIED`.
- `GET /privacy/notice` → `{version, title, body (Markdown), publishedAt|null}`. Public.

### 4.2 Manage users

- `POST /users/{id}/suspend` → `User` (with `suspendedAt` set; the account's sessions end).
- `POST /users/{id}/restore` → `User` (DR's name; master admin only).

### 4.3 AI routing (generalised DR transcription-provider order)

- `GET /settings/ai-routing` → `{tasks: TaskRoute[], providers: RouteProvider[]}` (DR's path; the backend task state carries more fields than listed here)
  - `TaskRoute = {task, label, publicText, routes: RouteRow[], effectiveChain: string[], normalisedNote|null}`
  - `RouteRow = {provider, model, enabled, keyState, testedAt|null, testError|null}`, order = ordinal
  - `RouteProvider = {id, name, keyName, keyState, publicTextOnly, models: [{id, label, tasks: string[]}]}`
  - `provider` ∈ `GEMINI`, `ANTHROPIC`, `OPENAI`, `DEEPSEEK`, `ELEVENLABS`; `keyState` ∈ `ABSENT`, `UNTESTED`, `PASSING`, `FAILING`
- `PUT /settings/ai-routing/{task}` body `{routes: [{provider, model, enabled}]}` → `TaskRoute`. The server may normalise (drop an unsupported model, a public-text-only provider on a private task) and say so in `normalisedNote`.
- `POST /settings/ai-routing/{task}/test` body `{provider, model}` → `TaskRoute` with that row's verdict (the backend tests the provider's key).

### 4.4 Usage

`GET /usage/report?from=ISO&to=ISO` → `{from, to, ceilingUsd, spentThisMonthUsd, spentUsd, calls, failures, byTask: [{task,label,calls,failures,inputTokens,outputTokens,costUsd}], byProvider: [{provider,name,model,calls,failures,costUsd,p95LatencyMs|null}], byDay: [{day,calls,costUsd}]}`. Money fields may be Decimal strings.

### 4.5 Asking

- `GET /answers/config` → `{modes: AnswerMode[], defaultMode, voice: {configured, languages}, languages: [{code,label}]}`. `AnswerMode` ∈ `VERIFIED`, `HYBRID`, `DEEP`; list only deployed modes. `voice.configured` decides whether the mic button and `VoicePanel` render at all.
- `POST /answers/stream` body `{question, mode, craftSlug|null, language|null, conversationId|null}` → `text/event-stream`. Each event is `event: <name>` + one JSON `data:` line, blank-line separated. Events, in any order after `match`:
  - `match`: `{status: "RESOLVED", craft: {slug,name,path}}` | `{status: "AMBIGUOUS", candidates: [{slug,name,path}] (≤5)}` | `{status: "NONE"}`. On AMBIGUOUS the server sends `done` next and nothing else; the client re-asks with `craftSlug`.
  - `source`: `SourceRef` = `{id, kind, title, authors[], year, doi, url, publisher, licence, attribution, reliability}`. Sent before the first citation that names it.
  - `section`: `{id, heading}`
  - `sentence`: `{sectionId, sentence: {id, text, level, translated?, citations: Citation[]}}`. A sentence with no citation is dropped by the client; the server never sends one.
  - `open_question`: `{sectionId, heading?, sentence}` (hypothesis-level sentences, shown collapsed)
  - `reaction`: `{id, label, equation (mhchem source, no `\ce{}` needed), balanced, level, conditions|null, citations}`
  - `follow_ups`: `{items: string[]}`
  - `done`: `{answerId|null}`; `error`: `{message}` (shown verbatim)
  - `Citation = {id, claimId, sourceId, quote|null (≤300 chars), locator|null, context|null (the surrounding passage the quote sits in), evidence: "QUOTED"|"INFERRED", level}`
  - `level` ∈ `VERIFIED`, `REVIEWED`, `PROVISIONAL`, `HYPOTHESIS`, `UNAVAILABLE` (uppercase enum values of `evidenceLevel`).
  - Outbound links are drawn only for `https:` URLs; a DOI without a URL becomes `https://doi.org/<doi>`.

### 4.6 Crafts and map

- `GET /crafts/{slug}/profile` → `CraftProfile`:
  - `craft: {id, slug, name, localName, giStatus, stateOfPractice[], stateOfOrigin[], description, categoryName, subCategoryName}`
  - `overview: Claim[]`, `stages: [{id, ordinal, name, stageType, durationText, claims: Claim[]}]`, `materials: [{id, name, description, claims: Claim[]}]`, `science: AnswerReaction[]`, `sources: SourceRef[]`
  - `locations: [{id, precision: STATE|DISTRICT|POINT, placeLabel, stateName, districtName, latitude|null, longitude|null, level}]` (state precision may carry the state seat's coordinates)
  - `Claim = {id, text, level, citations: Citation[]}`. An empty facet renders the "No source found" badge.
  - Unknown slug → 404; a MERGED slug may 308 to its target or answer with the target's profile.
- `GET /map/crafts` → `[{key, name, latitude, longitude, total, crafts: [{slug, name}]}]`, one point per place with the crafts practised there.

## 5. Voice (later lane)

`frontend/components/voice/VoicePanel.tsx` is the mount point, loaded with `next/dynamic` from `/ask` only when `voice.configured` is true. Props: `{open, onClose, craftSlug, mode, language, onTranscript?}`. The voice lane replaces its body and keeps the props.

## 6. Naming

`frontend/lib/naming.ts` is DR's helper with `PORTAL = "KalaVigyan"` (recovery codes download as `KalaVigyan_Account_<date>_Recovery-Codes.txt`). Golden rows belong in `shared/naming-golden.json` (shared lane).
