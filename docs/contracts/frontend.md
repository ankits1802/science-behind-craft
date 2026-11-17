# Frontend lane contract

The web client (`frontend/`, Next.js 16 App Router, React 19, Tailwind 4) is a port of the designer-portal (DR) shell. Wherever DR already has a route, the client calls it in DR's exact shape; the backend lane ports those routes unchanged. This file lists what the client assumes, and every route that is new for KalaVigyan.

## 1. Transport and session

- Every call goes to the same origin under `/api/*`. `frontend/proxy.ts` rewrites it to `API_ORIGIN` (falls back to `NEXT_PUBLIC_API_URL`) and adds the session token as `Authorization: Bearer` plus the shared proxy secret header `x-web-proxy-secret` (env `WEB_PROXY_SECRET`, same value on the API). This is DR's `lib/server/apiProxy.ts` unchanged.
- Sign-in, two-step verify, change-password and logout go through the Next route handlers in `frontend/app/api/{auth,session}/*`, which set and clear the `__Host-session` / `__Host-session-marker` cookies (DR shape). The API returns the token in the body of `POST /auth/login` and `POST /auth/two-factor/verify` exactly as DR does, and a fresh one in the `X-Session-Token` response header of `POST /auth/change-password`.
- Headers the client reads: `x-access-status` (`PENDING`, `REJECTED`, `SUSPENDED`, `NOT_RECORDED`) on a refused sign-in, `x-sign-in-hint`, `x-password-change-required: 1`, `x-two-factor-required`, `x-confirm-provider`.
- Env names (values never in the repo): `API_ORIGIN`, `NEXT_PUBLIC_API_URL`, `WEB_PROXY_SECRET`, `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, `NEXT_PUBLIC_MICROSOFT_CLIENT_ID`, `NEXT_PUBLIC_MICROSOFT_TENANT`, `NEXT_PUBLIC_YAHOO_CLIENT_ID`, `NEXT_PUBLIC_APP_VERSION`, `NEXT_PUBLIC_BUILD_NUMBER`. See `frontend/.env.example`.

## 2. Roles

`UserRole` = `MASTER_ADMIN` (60), `ADMIN` (50, "Admin"), `PROFESSOR` (40), `RESEARCHER` (30), `STUDENT` (15), mirrored in `frontend/lib/permissions.ts` (`ROLE_RANK`, `ROLE_LABELS`) and checked against `shared/roles.json`. Route guards and the backend dependency each one mirrors:

| Path | Who | Backend dependency name |
|---|---|---|
| `/admin` | Admin and above | `require_admin` (the hub itself calls no route) |
| `/admin/keys`, `/admin/routing` | Master admin | `require_master_admin` |
| `/admin/usage` | Admin and above | `require_view_usage` |
| `/admin/users` | Professor and above | `require_professor` |
| `/admin/access` | Professor and above | `require_access_roster_manager` |

A professor assigns only `RESEARCHER` and `STUDENT`; an admin assigns up to `PROFESSOR`, changes roles, suspends and restores accounts and resets two-step verification for accounts ranked below Admin; only the master admin assigns `ADMIN` or acts on an admin. Each admin nav item is shown by its own route guard (`routeAllows`), and the hub lists the areas whose guard admits the viewer. The access roster shows only the actions the viewer may take on each entry (`accessEntryOffers`, by the entry's role). The admin view toggle stays with the master admin (`hasAdminView`).

## 3. Routes ported from DR, called in DR's shape

`GET /me`, `GET|PUT /preferences/me`, `POST /auth/login` (`{email,password}`, `{googleIdToken, googleNonce}` or the five `oidc*` fields of §4.1), `POST /auth/logout`, `POST /auth/change-password` (a first password with the proof fields of decision 0028), `POST /auth/first-password/nonce`, `POST /auth/forgot-password`, `GET /auth/set-password`, `POST /auth/set-password/check`, `POST /auth/set-password`, `POST /auth/password-links`, `GET /auth/two-factor`, `POST /auth/two-factor/setup`, `POST /auth/two-factor/setup/cancel`, `POST /auth/two-factor/enable`, `POST /auth/two-factor/disable`, `POST /auth/two-factor/recovery-codes`, `POST /auth/two-factor/verify`, `GET /access/roster` (`page,pageSize,search,status` and the roster filter params), `GET /access/roster/pending-count`, `POST /access/roster`, `POST /access/roster/{id}/decision`, `PATCH /access/roster/{id}`, `DELETE /access/roster/{id}`, `GET /users` (`search,role,page,pageSize`), `PATCH /users/{id}` (`{role}`), `DELETE /users/{id}/two-factor`, `POST /users/{id}/sign-out-everywhere`, `GET /secrets`, `PUT /secrets/{key}`, `DELETE /secrets/{key}`, `POST /secrets/{key}/test`, `GET /crafts/catalogue` (ETag, `If-None-Match`, DR `CraftCatalogue` body).

Not called, by design: `GET /secrets/{key}/reveal` (PLAN §9, §15).

Changes to DR shapes the client assumes:

- `PUT /secrets/{key}` body is `{value, twoFactorCode}` and `DELETE /secrets/{key}` carries `{twoFactorCode}`: a six-digit TOTP step-up (PLAN §12, keys rotate with TOTP step-up). A wrong or missing code is a 401 with `x-two-factor-required: 1` and a sentence in `detail`; `apiFetch` keeps the session for that 401.
- `User` adds `affiliation`, `twoFactorRequired` (true for PROFESSOR, ADMIN and MASTER_ADMIN until two-step is on; the shell then shows only the setup card), `isActive`, `suspendedAt`.
- `POST /auth/login` with Google also takes `googleNonce`, the value from §4.1; the API verifies it once, with `aud`, `iss`, `exp` and `email_verified`.

## 4. New routes

### 4.1 Auth and sign-up

- `POST /auth/google/nonce` → `{nonce}`. Public. A fresh single-use nonce per attempt; the client passes it to `google.accounts.id.initialize({nonce})` and back with the ID token.
- `POST /auth/oidc/nonce` body `{provider}` → `{nonce}`. Public. The login page asks for it when "Continue with Yahoo" (or Microsoft) is pressed, sends its SHA-256 digest (base64url) to the provider with a PKCE S256 challenge, keeps the raw value and the verifier in `sessionStorage` (`kalavigyan_oidc_pending`, 10 minutes), and posts `{oidcProvider, oidcCode, oidcCodeVerifier, oidcRedirectUri, oidcNonce}` to `/auth/login` when the provider returns. The provider returns to `/login/callback` (a route handler, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`), which forwards only `code`, `state` and `error` to `/login` in the fragment; the page strips the fragment before using it. The buttons are drawn from `NEXT_PUBLIC_YAHOO_CLIENT_ID` and `NEXT_PUBLIC_MICROSOFT_CLIENT_ID` (with `NEXT_PUBLIC_MICROSOFT_TENANT`); blank means no button (decision 0026).
- `GET /auth/config` → `{signUpOpen, turnstileRequired, turnstileSiteKey|null, googleEnabled, googleClientId|null, microsoftEnabled, microsoftClientId|null, yahooEnabled, yahooClientId|null, mailAvailable}`. The sign-up page draws the email form only when `signUpOpen`, and the Turnstile widget when `turnstileRequired` and a site key is given; otherwise it offers Google only.
- `POST /auth/signup` body `{name, email, affiliation, requestedRole, profileUrl|null, ageAttested: true, privacyNoticeVersion|null, turnstileToken|null}` → `202 {status: "EMAIL_SENT", email}`, the same for every address. No password: the emailed link (`/set-password?token=`) confirms the address and sets it, and only then is the PENDING request recorded. `requestedRole` is one of `STUDENT`, `RESEARCHER`, `PROFESSOR`. Password sign-in into a never-confirmed account answers 401 with `x-sign-in-hint: EMAIL_UNVERIFIED`.
- `GET /privacy/notice` → `{version, title, body (Markdown), publishedAt|null}`. Public.

### 4.2 Manage users

- `POST /users/{id}/suspend` → `User` (with `suspendedAt` set; the account's sessions end).
- `POST /users/{id}/restore` → `User` (DR's name; admin and above, for accounts ranked below them).

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

- `GET /answers/config` → `{depths: [{depth, label}], defaultDepth|null, voice: VoiceAvailability, languages: [{code, label, autonym, script, direction}], listen?: {languages: [code]}}` (`listen` absent or off the contract draws no Listen control, `lib/listen.listenLanguagesOf`) (`VoiceAvailability` is `docs/contracts/voice.md`; `languages` is checked by `lib/answerLanguages.answerLanguagesOf`, English always offered, an off-contract list falls back to English and is logged; `depths` and `defaultDepth` by `lib/askConfig.askDepthsOf`, which logs an off-contract list and draws no depth choice). `voice` feeds the craft page's dock only.
- The ask screen (decision 0036): the question box, dictation, and under it the craft (a searchable picker over `GET /crafts/catalogue` with Any craft, never required), the depth (the config's `depths`, starting at its `defaultDepth`, the role's) and the answer language. Dictation is the browser's Web Speech API (`SpeechRecognition`, else `webkitSpeechRecognition`) in the answer language's `<code>-IN` locale with live interim words (`lib/dictation.ts`, the one adapter); the mic is drawn only where the browser has the API and has not refused that language. No speech reaches the server: the question is sent as text.
- `POST /answers/stream` body `{question (2-1000), depth|null, craftSlug|null, anyCraft?, language|null, fresh?}` → `text/event-stream`. `fresh: true` is sent only by Research again, which the explainer draws once a done answer shows a block from earlier research (`lib/explainerView.showsEarlierResearch`); it asks the same question with the same choices and reuses no stored piece (decision 0033). `depth` is `BASIC`, `DETAILED` or `EXPERT` (the reader's choice, starting at the config's default), or null before the config is read (the server applies the role's default); the server runs it as its mode (`research/depth.DEPTH_POLICIES`). `anyCraft: true` is sent only when the reader chose Any craft over a detected craft, for that question. The client no longer sends `mode`. Each event is `event: <name>` + one JSON `data:` line, blank-line separated. The stream is the explainer stream of `docs/contracts/explainer.md`: `lib/explainerStream.streamExplainer` parses every frame with the contract's shapes (a frame off the contract is logged and dropped; the retired `match`, `section` and `sentence` are skipped), `lib/explainerState.reduceExplainer` keeps the answer's state and `components/answer/ExplainerView.tsx` draws it (decision 0037). Events:
  - `understood`: the `Understood` of `docs/contracts/explainer.md`, kept as `ExplainerState.understood` and drawn first as the understood line ("Answering for Kutch Ajrakh · Expert · in English"); each part the reader can change is a button that moves focus to its control under the question box. With no craft picked, the craft picker's Any craft row reads `<crafts> · detected`, an explicit Any craft row (`anyCraft`) is offered above the list, and the `candidates` are one-tap buttons that ask again with that `craftSlug` (`lib/askCraft.craftOffer`). Changing the craft, depth or language while the asked question is still in the box asks again (`reasksOnChange`).
  - `source`: `SourceRef` = `{id, kind, title, authors[], year, doi, url, publisher, licence, attribution, reliability}`. Sent before the first citation that names it.
  - `trail`: the research trail. While the answer streams it shows the counts per group and the five latest sources with their stage (Found, Read, Quoted); after `done` it is the counts and Replay the trail, which plays every entry in arrival order (at once under either reduced-motion switch). A key only moves forward; a reused piece reads "From earlier research · date".
  - `section_started`, `section_state`, `block`, `section_done`: sections are drawn in `order` with a section bar to jump between them; a working section shows its state (Researching, Writing, Checking) while the answer streams; blocks render as they arrive (`prose`, `process_ladder`, `images`, and once built the place kinds `region_story`, `map_layer`, `seasons` and `supply_map` of decision 0048, whose maps load on demand and read `GET /rivers/{mainRiv}` and `GET /map/layers[/{layer}]`, and the matter and expert kinds `reaction_player`, `material_card`, `molecule_3d` (3Dmol.js loaded on demand over `GET /molecules/{pubchemCid}/conformer`) and `expert_view` (a section's views as one panel with "Experts differ" cards) of decision 0049; a reused block carries "From earlier research · date"); an `EMPTY` section shows what was searched; a `READY` section with no block to draw is hidden. A translated sentence (and a translated section title) carries its English `original`; every sentence, title and paragraph sets `lang` and `dir` (`rtl` for Urdu), and a segmented control shows the English original (decision 0023). The request's `language` is the Ask picker's choice, or the language of the question's script when it is Auto, remembered as `answerLanguage` in `kalavigyan_preferences`.
  - Prose and ladder sentences carry citation chips (one numbering per answer, in the order of first citation walking the sections), a Verified or Reviewed badge where the level is one of those, and their term spans underlined at the first occurrence; a tap opens the term's summary (`GET /terms/{key}?language=` → `Term`; a 404 removes that term's underline for the answer). The ladder fills as the reader scrolls and is drawn filled under either reduced-motion switch.
  - `open_question`: `{sectionId, heading?, sentence}` (hypothesis-level sentences, shown collapsed)
  - `reaction`: `{id, label, equation (mhchem source, no `\ce{}` needed), balanced, level, conditions|null, citations}`
  - `follow_ups`: `{items: string[]}`
  - `done`: `{answerId|null}`; `error`: `{message}` (shown verbatim)
  - `status`: `{step, message}`, progress while the answer is worked out (`step` one of RESOLVING, PLANNING, SEARCHING_STORED, RESEARCHING, READING, COMPOSING, WRITING_BACK, TRANSLATING). The client shows `message` as the progress line (`AnswerProgress`, `role="status"`) and clears it on `done`, `error` or `not_enough_evidence`.
  - `not_enough_evidence`: `{message}`, nothing cited could be shown; `message` lists what was searched. The client's empty state (`NotEnoughEvidence`), not an error. Only `done` follows.
  - Depths: `/answers/config` lists the depths the asker may choose (every known role all three); a depth the role may not choose is a 403 with a sentence in `detail`.
  - Data states of the answer: loading (`asking`/`streaming` with the status line), empty (`empty`), error (`failed`, shown verbatim with Try again), success (`done`).
  - Listen: drawn after `done` only when `/answers/config` lists the answer's language in `listen.languages`; it reads `GET /answers/{answerId}/listen?language=` (the Listen section of `docs/contracts/explainer.md`), plays the tracks in order in a dock and highlights the sentence and word being read from the timings.
  - Heartbeat: an SSE comment `: keep-alive` after 60 s without an event; the parser already skips comments.
  - The backend side of this stream, with the models every event is validated against, is `docs/contracts/research.md` and `docs/contracts/explainer.md`; the client reduces `shared/explainer.stream.golden.sse` to `explainer.document.golden.json` (`e2e/explainer-view-unit.spec.ts`) and the answering flow's goldens (`e2e/answer-stream-golden-unit.spec.ts`).
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
- The craft page also reads `GET /crafts/{slug}/process` (Process tab) and `GET /crafts/{slug}/region` (Region tab), and `/map` reads `GET /map/layers` and `GET /map/layers/{layer}` (`?layer=` in the URL; `If-None-Match` through the browser cache), all as `docs/contracts/science.md` and `region.md` describe (decision 0019). The profile's `stages` and `science` are no longer drawn.

### 4.7 Media (decision 0021)

The Process tab reads `GET /media/options?craftSlug=` once per page and draws Image or Video on a stage only for the kinds listed for it with units left (`offeredKinds`, `lib/mediaContract.ts`); a failed or off-contract answer draws none. A press sends `POST /media/jobs` with a fresh `media:<uuid>` idempotency key, polls `GET /media/jobs/{id}` after each `pollAfterSeconds` with the ProgressBar, and draws the asset after the stage's evidence with its label, model, day and alt text, a Download that saves `fileName`, and for professors the sharing step the asset lists (`POST /media/assets/{id}/sharing`, not served yet). The store is `lib/craftMedia.ts`; routes, rules and the sharing shape are `docs/contracts/media.md`.

## 5. Voice (decision 0020)

`frontend/components/voice/VoicePanel.tsx` is the mount point: a non-modal dock, loaded with `next/dynamic` on `/crafts/[slug]` (Talk in the header, `components/craft/CraftVoice.tsx`), mounted only when voice is offered, which it never is while the call is switched off (`configured` false, decision 0035). The ask box's mic is dictation (decision 0036) and no longer opens the dock. Props: `{open, onClose, craftSlug, mode, question?, availability, host?, onTranscript?}`; the call's language is the Ask preference (`answerLanguage`, Auto following `question`'s script) resolved over `availability.languages` (decision 0025); `host` is what the page can show for the client tools: `{stages (id to name, the stages it drew), showOnMap, openStage}`. The call itself is `lib/voiceCall.ts` with its transports (`voiceRelay.ts`, `voiceAgent.ts`) and adapters (`voiceSession.ts` for the routes, `elevenLabsAgent.ts` for the SDK, `voiceDevice.ts` for the microphone and speech).

The voice routes, session shapes, client tools and the relay turn stream are `docs/contracts/voice.md`, typed and parsed by `frontend/lib/voiceContract.ts`. The craft page's process and region answers and the map layers are `docs/contracts/science.md` and `docs/contracts/region.md` (`lib/scienceContract.ts`, `lib/regionContract.ts`); generated media is `docs/contracts/media.md` (`lib/mediaContract.ts`); the explainer document, its blocks, terms and stream events are `docs/contracts/explainer.md` (`lib/explainerContract.ts` with `lib/explainerBlockBase.ts`, `explainerPlace.ts`, `explainerMatter.ts`, `explainerExperts.ts`, and `lib/explainerStream.ts`), whose shapes refuse a block kind that is not built yet; each built kind is drawn by its one renderer in `components/answer/blockRenderers.ts` (decision 0042). Each parses its response with `parseShape`, which refuses unknown fields and values.

## 6. Naming

`frontend/lib/naming.ts` is DR's helper with `PORTAL = "KalaVigyan"` (recovery codes download as `KalaVigyan_Account_<date>_Recovery-Codes.txt`). Golden rows belong in `shared/naming-golden.json` (shared lane).
