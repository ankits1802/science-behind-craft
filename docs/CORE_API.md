# Shared code catalogue

Every shared backend component, with what it guarantees. Check here before writing a helper; if
what you need is close to something listed, extend it. A component enters this list when a
second real caller exists, and leaves it in the same change that deletes it.

Paths are under `backend/app/`. Last reviewed: 2026-11-17.

## core/config.py: settings

| Name | Guarantee |
|---|---|
| `Settings`, `get_settings() -> Settings` | The one loader of environment settings (pydantic-settings, `backend/.env`), cached. Invalid values raise `SettingsError` at start-up, never later. |
| `is_local_db_host(host) -> bool` | True for loopback and local container host names. |
| `with_explicit_sslmode(url, require) -> str` | Returns the URL with exactly one `sslmode`, replacing any ssl query keys. |

## core/db.py: database sessions

| Name | Guarantee |
|---|---|
| `build_runtime_database_url(base_url) -> RuntimeDatabase` | Converts a Postgres URL to `postgresql+psycopg`, drops Prisma-only parameters, and records the connect arguments and whether it is the Supabase transaction pooler (`TRANSACTION_POOLER_PORT`) or the session pooler (`SESSION_POOLER_PORT`). |
| `get_engine()`, `sessionmaker()` | One async engine and session factory per process. |
| `get_session()` | FastAPI dependency yielding one `AsyncSession` per request. |
| `session_scope()` | Async context manager: commits on success, rolls back on any error. |
| `ping()`, `dispose_engine()` | Readiness probe (raises when the database does not answer) and shutdown. |

## core/security.py: passwords and tokens

| Name | Guarantee |
|---|---|
| `hash_password(password) -> str` | bcrypt `2b` at `BCRYPT_ROUNDS`; raises `ValueError` for a password it cannot check (a NUL character, or longer than `MAX_CHECKED_PASSWORD_BYTES`). |
| `verify_password(password, hash) -> bool` | False for a missing hash; constant-time compare. |
| `verify_password_or_decoy(password, hash) -> bool` | Same, but spends bcrypt time against a decoy when there is no hash, so a missing account is not visible by timing. |
| `create_access_token(subject, *, token_version, extra_claims=None, expires_minutes=None) -> str` | Signed JWT carrying `TOKEN_VERSION_CLAIM` (`tv`). |
| `decode_access_token(token) -> dict` | Verifies signature and expiry with the allowed algorithms; raises on any failure. |
| `jwt_signing_weakness(secret)`, `verify_jwt_configuration()` | Refuse placeholder or short signing keys (`MIN_JWT_SIGNING_KEY_LENGTH`) at start-up. |
| `secret_key(name, value, *, min_chars=SECRET_KEY_MIN_CHARS) -> bytes`, `secret_key_or_none(...)` | The one rule for an HMAC key read from the environment: surrounding whitespace dropped, at least 32 characters, else `NotConfigured` naming the key. The `_or_none` form answers `None` for an unset key and logs an error (name only) for one set but too short. Used by the media bundle and the voice binding (decision 0022). |

## core/clock.py: India time

| Name | Guarantee |
|---|---|
| `INDIA_TZ`, `INDIA_TZ_NAME` | `Asia/Kolkata`, the zone of every quota day, budget month, file name date and media label date (`providers/budget`, `services/naming`, `media/views`, the usage routes). |

## core/roles.py: roles and capabilities

| Name | Guarantee |
|---|---|
| `MASTER_ADMIN`, `ADMIN`, `PROFESSOR`, `RESEARCHER`, `STUDENT`, `ROLE_RANK`, `ROLE_LABELS`, `ROLES_BY_RANK` | The role vocabulary and ranks (60, 50, 40, 30, 15); `shared/roles.json` holds the same ranks and labels for the web client. |
| `Capability`, `CAPABILITY_MIN_ROLE` | Every capability and the lowest role that holds it. |
| `can(user_or_role, capability) -> bool` | Unknown roles hold nothing. |
| `capabilities_of`, `role_value`, `role_rank`, `has_rank`, `is_known_role`, `is_master_admin` | Read a role from a user object or a role string. |
| `assignable_roles(actor)`, `may_assign(actor, role)`, `may_manage_target(actor, target)` | The master admin assigns and manages every role; an actor with MANAGE_ACCESS only roles ranked below its own (an admin up to Professor); anyone else none. |
| `requires_two_factor(user_or_role)`, `TWO_FACTOR_REQUIRED_ROLES` | Professor, admin and master admin must have TOTP. |
| `daily_allowance(user_or_role, resource)`, `DAILY_ALLOWANCES` | Per-role daily limits; `None` means unlimited. |

## core/deps.py: request dependencies

| Name | Guarantee |
|---|---|
| `get_current_user` | The signed-in, active user whose token version matches; refuses with 401 or 403 and the contract headers when a password change or 2FA setup is pending. |
| `get_current_user_any_step` | Same, but allows the pending-step routes. |
| `require(capability)` | Dependency factory that refuses with 403 and a capability-specific sentence (`refusal_for`). |
| `require_master_admin` | Master admin only. |
| `refuse_unless_assignable(actor, role)` | 422 for an unknown role, 403 naming the roles the actor may give (`may_assign`). Used by the Manage users and access roster routes that set a role. |
| `refuse_unless_manageable(actor, target)`, `MANAGE_TARGET_REFUSAL` | 403 unless `may_manage_target`; each Manage users route calls it before changing another account. |
| `user_from_token(session, token)`, `token_matches_user(claims, user)` | Resolve and check a bearer token outside a route. |
| `password_change_pending`, `two_factor_setup_pending`, `refuse_pending_steps` | The pending-step rules used by both dependencies. |
| `is_configured_master_admin`, `is_break_glass_master` | The account named by `MASTER_ADMIN_EMAIL`. |

## core/logging.py: logs and request ids

| Name | Guarantee |
|---|---|
| `configure_logging(level)`, `JsonFormatter` | One JSON line per record, with request id and user id when known. |
| `redact_secrets(value) -> str` | Masks bearer tokens, Anthropic, OpenAI and Google API-key shapes, and `api_key`, `apiKey`, `insttoken` and `access_token` query values in a string before it is logged. |
| `RequestContextMiddleware`, `REQUEST_ID_HEADER` | Accepts a well-formed inbound `X-Request-ID` or makes one, and returns it on every response. |
| `current_request_id()`, `new_request_id()`, `set_log_user(user_id)` | Read and set the per-request log context. |
| `request_id_scope(request_id)` | Context manager that tags everything inside it (logs, `UsageEvent.requestId`, `AuditLog`) with a well-formed request id outside an HTTP request, and restores the previous one. |

## core/rate_limit.py: rate limits and the client address

| Name | Guarantee |
|---|---|
| `SlidingWindow` | Thread-safe sliding-window counter with a bounded key set; `attempt` returns `(allowed, retry_after_seconds)`. |
| `client_ip(connection) -> str` | The viewer address: the Vercel proxy's `x-viewer-address` when `x-web-proxy-secret` matches (constant-time); otherwise, only for a loopback peer (nginx), the `FORWARDED_CLIENT_HOPS`-th `X-Forwarded-For` entry from the right; otherwise the peer address. |
| `ip_hash(address) -> str` | HMAC-SHA256 of the address keyed by the JWT secret, 32 hex characters, for storage in place of the address. |
| `sign_in_attempt_by_ip`, `sign_in_attempt_by_account`, `forgot_password_attempt`, `code_attempt`, `ask_attempt`, `voice_session_attempt`, `voice_turn_attempt`, `voice_speech_attempt` and their `refund_*` | The named limits used by auth, two-step, asking, starting a voice call (10 in 10 minutes), relay turns (40) and reply replays (60). |
| `reset_all()` | Clears every window (tests only). |

## core/errors.py: the error hierarchy

| Name | Guarantee |
|---|---|
| `AppError` | Base of every application error; catch by the categories below. |
| `InvalidInput` | The caller sent something a contract refuses (also a `ValueError`). |
| `Refused(reason, message)` | A guard said no; `reason` is a stable code (never empty). |
| `NotConfigured(name, message)` | A key, setting or route is missing. |
| `ExternalFailure(message, *, kind, retryable, status, retry_after, service)` | Another service failed; `kind` must be in `FAILURE_KINDS`; `tries_next` is true for `NEXT_ROUTE_KINDS`. `ProviderError` is a subclass. |
| `FAILURE_KINDS`, `NEXT_ROUTE_KINDS`, `STOP_KINDS` | The failure vocabulary shared by the AI router and every source adapter. |
| `failure_kind(status)`, `RETRYABLE_KINDS` | The one HTTP status to failure kind mapping and the kinds marked retryable; used by `sources/http`, the MediaWiki helper and the fetcher. |

## core/retry_after.py: wait hints

| Name | Guarantee |
|---|---|
| `parse_headers(headers, now=None) -> float \| None` | Seconds to wait from `retry-after-ms` or `Retry-After` (seconds or an HTTP date); never negative; `None` when absent or unreadable. |
| `parse_retry_info(body)`, `retry_after_of(exc)` | The same hint from a Google `RetryInfo` body or an SDK exception's response. Used by the model providers and `sources/http`. |

## core/http_cache.py: revalidated answers

| Name | Guarantee |
|---|---|
| `revalidated(request, response, version) -> Response \| None` | Sets `ETag: "<version>"` and `Cache-Control: private, no-cache` on the response, or returns the 304 to send when `If-None-Match` matches. Used by the craft catalogue and the map layer. |
| `quoted_etag(version)`, `etag_matches(if_none_match, etag)`, `PRIVATE_NO_CACHE` | The quoted tag; a match ignores `W/` and accepts `*` and lists. |

## core/shielded.py: work that outlives its caller

| Name | Guarantee |
|---|---|
| `ShieldedWork()`, `.run(work, *, name) -> T`, `.drain(timeout=DRAIN_SECONDS) -> int` | One per process (`app.state.shielded_work`). `run` awaits the work through `asyncio.shield`: a cancelled caller leaves it running, held until it ends, a later failure logged with its name; `drain` waits at shutdown and returns how many were still running. Used by the answer write-back (decision 0016). |

## research/: research and answering contracts

Shapes and rules are in `docs/contracts/research.md` (decision 0002).

| Name | Guarantee |
|---|---|
| `research/base`: `ContractModel`, `HttpsUrl`, `PartialDate` | Frozen, extra-forbidding models with camelCase JSON; https-only URLs; partial ISO dates. |
| `research/vocabulary`: literal types, `LEVEL_ORDER`, `LABEL_LEVELS`, `weakest_level(levels)` | Vocabulary built from `models/enums.py`; the one rule for combining evidence levels. |
| `research/quotes`: `normalise_quote_text`, `quote_key`, `quote_occurs`, `trivial_quote`, `quote_overlap`, `content_stems`, `figures_in`, `formulas_in`, `numbers_in`, `fold_digits`, `unsupported_figures`, `QUOTE_MIN_CHARS`, `QUOTE_OVERLAP_MIN` | The verbatim-quote check on whole words and numbers, the minimum quote length, the sentence-to-quote overlap and the "every figure is cited" check (decision 0013); figures read native digits (every Unicode decimal digit and the Arabic separators) as ASCII (decision 0023). |
| `research/translation`: `TranslationRequest`, `TranslationItem`, `Translator`, `translation_problems`, `protected_tokens`, `written_in`, `TRANSLATION_ATTEMPTS`, the unit lists | The translation contract and its post-check: same numbers after folding native digits, same formulas, mhchem and units after NFKC, prose in the target script (decision 0023). |
| `research/licences.open_licence(licence)` | Whether a licence string is an allow-listed open licence (CC0, CC BY, CC BY-SA, PDDL, public domain) by name or canonical URL; everything else is closed (decision 0013). |
| `research/crafts.craft_block(craft)` | The craft name and slug as one untrusted block for model prompts. |
| `research/elements`: `ELEMENTS`, `ELEMENT_SYMBOLS` | The periodic table's symbols, the one list used by the PubChem formula test and the science engine's formula parser. |
| `research/vocabulary`: `ANSWER_LANGUAGE_SPECS`, `ANSWER_LANGUAGES`, `AnswerLanguage`, `CANONICAL_LANGUAGE`, `RIGHT_TO_LEFT_SCRIPTS`, `text_direction`, `language_option` | The one list of answer languages (label, autonym, script; one line each) offered by `/answers/config` and accepted by the ask route, plan requests and preferences; `language_option` is the `{code, label, autonym, script, direction}` both the answer and the voice languages are sent as; English is the language answers are composed and checked in (decision 0023). |
| `research/crafts`: `CraftRef`, `CraftQuery`, `CraftResolution`, `CraftResolver`, `clear_winner` | Craft resolution types and the accept rule (0.85, margin 0.15). |
| `research/evidence`: `EvidenceItem`, `Quote`, `SearchQuery`, `SourceDocument`, `SourceAdapter`, `canonical_url`, `personal_data_in`, `without_personal_data`, `DOI_PATTERN` | One adapter interface for every external source; quotes are backed by the document text. `PERSONAL_DATA` (email written or spoken, phone and Aadhaar-like numbers) is the one home of the personal-data patterns: `personal_data_in` names them, `without_personal_data` replaces them with `[email]` or `[number]`. |
| `research/evidence`: `OpenAccessLocation`, `OpenAccessLocator`, `OPEN_ACCESS_STATUSES` | Whether a DOI has a legal open copy and where (https only); `CLOSED` carries no URL. |
| `research/fetcher`: `FetchRequest`, `FetchedPage`, `Fetcher`, `FetchRefused`, the caps | The sandboxed fetch interface and its refusal codes. |
| `research/fetcher`: `FETCHER_PATH`, `FETCHER_HEALTH_PATH`, `FETCHER_REFUSED_STATUS`, `FETCHER_FAILURE_STATUS`, `FetchRefusalBody`, `FetchFailureBody` | The fetcher service's wire, shared by the server and `FetcherClient` (decision 0007). |
| `research/untrusted`: `clean_untrusted_text`, `untrusted_block`, `UNTRUSTED_TAG` | Invisible and control characters out of retrieved text (ZWJ and ZWNJ kept); the one wrapper for retrieved text in a prompt, which the text cannot close. |
| `research/evidence`: `EVIDENCE_ID_MAX_CHARS` | The 500-character limit on evidence and composer ids. |
| `research/planning`: `RetrievalPlan`, `PlanRequest`, `Planner`, `MODE_POLICIES` | Plans that cannot exceed their mode's tiers, queries or fetches. |
| `research/planning`: `FacetCoverage`, `FACET_COVERED_MIN_CLAIMS`, `COVERING_LEVELS` | The one rule for when stored claims cover a facet (2 matching claims at a level the mode shows outside open questions). |
| `research/structured`: `StructuredModel`, `StructuredReply`, `reply_object`, `MODEL_SERVICE`, `schema_object` | One JSON-object model call and the reader of its reply (a code fence accepted; anything but an object is `ExternalFailure`); `schema_object(**properties)` is the one strict JSON-schema object (every property required, no others). |
| `research/evidence_pack`: `EvidencePack`, `PackedEvidence`, `ResearchFailure`, `RESEARCH_STAGES` | What live research hands on: plan, stored hits, coverage, ranked deduplicated evidence, documents read and every failure, checked against each other. |
| `research/composition`: `ComposeRequest`, `ComposedAnswer`, `Composer`, `sentence_violations`, `sentence_level`, `ResearchSummary`, `not_enough_evidence_message` | Composer input and output, the per-sentence post-checks (cited, quoted, every figure in a verified quote), and the one message that lists what was searched when nothing survives. |
| `research/write_back`: `ClaimWriteBack`, `ClaimWriter`, `claim_dedupe_key` | What live research stores, its level labels and dedupe key. |
| `research/embedding`: `TextEmbedder`, `checked_vectors`, `EMBEDDING_SERVICE` | The one embedding protocol (texts in, vectors out) and the check that every text got a vector of 1536 dimensions. |
| `research/retrieval`: `KnowledgeQuery`, `KnowledgeHits`, `ClaimHit`, `ChunkHit`, `KnowledgeRetriever`, `MODE_CLAIM_LEVELS`, `MODE_CLAIM_STATUSES`, `HIDDEN_CLAIM_STATUSES`, `VISIBLE_SENSITIVITY`, `RESTRICTED_SENSITIVITY` | Stored-knowledge search types and the one definition of which claims, levels and sensitivities each mode may show. |
| `research/stream`: event models, `STREAM_EVENTS`, `parse_event`, `event_frame`, `sse_frame`, `match_event`, `HEARTBEAT_SECONDS`, `HEARTBEAT_FRAME` | The answer stream contract; `event_frame` refuses a payload that breaks it. |
| `research/stream.event_stream(produce, *, heartbeat_seconds)`, `Emit`, `ResearchProgress`, `StatusStep` | Runs a producer as a task, validates and queues each event, sends the heartbeat on every silent interval, cancels the producer when the response closes. |

## sources/: adapters for external research sources

Decisions 0005, 0006 and 0007; the adapters themselves are listed in `docs/contracts/research.md`.

| Name | Guarantee |
|---|---|
| `sources/http`: `SourceHttp`, `RatePolicy`, `ResponseCache`, `SourceResponse`, `source_client(contact_email)` | One paced, cached GET per service: at least `min_interval` between calls, Retry-After of up to `max_retry_wait` waited out once, longer ones and later calls fail as `rate_limit` until they pass, no Retry-After pauses `DEFAULT_BLOCK_SECONDS`; any non-2xx, transport failure or body over `SOURCE_MAX_BYTES` is an `ExternalFailure` naming the service only. Secret parameters and headers are sent but never cached or put in messages. Redirects are not followed. |
| `sources/records`: `classify(work_kind)`, `WORK_KINDS`, `doi_of`, `doi_url`, `partial_date_of`, `published_since`, `markup_text`, `clean_text`, `title_of`, `https_or_none`, `query_terms`, `UnusableRecord`, `AUTHORS_MAX` | Pure rules for turning a service record into contract fields: source type and trust by work kind, DOI spellings, partial dates from strings, years and date parts, HTML and JATS to text (hidden, script and style content dropped). |
| `sources/adapter`: `HttpSourceAdapter`, `build_document`, `checked_k`, `native_id`, `utc_now` | The `SourceAdapter` skeleton: checks `k` and ids, normalises records (logging and leaving out unusable ones), applies `freshnessDays`, caps document text at `FETCH_TEXT_MAX_CHARS` with its SHA-256 (`truncated` also kept when the caller passes it). |
| `sources/fetcher_client`: `FetcherClient(base_url, client)`, `FETCHER_SERVICE` | The `Fetcher` over HTTP at `FETCHER_URL`: refusals and failures come back as `FetchRefused` and `ExternalFailure`; an answer off the contract is a failure. |
| `sources/web/page`: `WebPageAdapter`, `page_item(adapter, url, page)`, `WEB_TRUST` | The skeleton of a web search adapter: https hits with the URL as id, and `fetch` through the fetcher into a `FULL_TEXT` document. |
| `sources/web/registry`: `web_search(config, client, fetcher)`, `WebSearchConfig`; `sources/web/fallback`: `WebSearch` | SearXNG first, Brave when it gives fewer than 3 hits or fails and a key is set (decision 0007). `WebSearchConfig` never prints the key. |
| `sources/scholarly/registry`: `scholarly_sources(keys, client)`, `ScholarlyKeys`, `ScholarlySources`, `SCHOLARLY_KEY_NAMES` | Builds every scholarly adapter and the Unpaywall locator with their own pacing; leaves out CORE (reported) and the dormant publishers (silent) without keys. `ScholarlyKeys` never prints a key. |
| `sources/reference/mediawiki`: `action_api(http, endpoint, params)`, `pages_in_order`, `page_revision`, `rights_text`, `primary_language`, `with_language`, `language_and_native`, `WIKIMEDIA_RATE` | The MediaWiki Action API for every Wikimedia adapter: JSON format 2 with plaintext errors, API errors inside a 200 raised as `ExternalFailure` with a kind, search pages in rank order, the latest revision id and date, the wiki's licence text, and a language tag reduced to its checked primary subtag (decision 0006); Wikidata and Commons ids carry a non-English language (`hi:Q42`) so `fetch` renders in it (decision 0023). |
| `sources/reference/pubchem`: `PubChemAdapter.compounds(text, k)`, `PubChemCompound` | Typed compound records (CID, title, Hill formula, weight, IUPAC name, InChIKey, SMILES) for a name or formula, through the adapter's own paced HTTP (decision 0015). |
| `sources/reference/registry`: `reference_sources(client)` | Builds the Wikipedia, Wikidata (with its SPARQL pacing), PubChem and Wikimedia Commons adapters, each with its own pacing and cache. |
| `services/scholarly_keys.scholarly_keys(session)` | Reads `SCHOLARLY_KEY_NAMES` from the managed secrets and `RESEARCH_CONTACT_EMAIL` from settings. |
| `services/web_sources.web_search_config(session)` | The web search settings: `SEARXNG_URL` and the managed `BRAVE_SEARCH_API_KEY`. |
| `services/live_sources.live_sources(session, client)`, `DOI_SOURCE` | Every live source for the planner: scholarly, reference and web adapters, one `FetcherClient` (`FETCHER_URL`), the Unpaywall locator and Crossref for cited DOIs. Hold it for the process. |

## schemas/common.py: request and page shapes

| Name | Guarantee |
|---|---|
| `APIModel` | Base for request bodies: unknown fields refused, strings stripped, camelCase or field names accepted. |
| `normalize_pagination(page, page_size)`, `page_payload(items, total, page, page_size)`, `MAX_PAGE_SIZE` | One page shape (`items`, `total`, `page`, `pageSize`, `pages`) with size capped at 200. |

## schemas/: science, region, voice and media contracts (decision 0014)

Shapes and rules are in `docs/contracts/science.md`, `region.md`, `voice.md` and `media.md`;
the client side is `frontend/lib/{scienceContract,regionContract,voiceContract,mediaContract}.ts`
over the runtime shape kit `frontend/lib/shape.ts` and `answerShapes.ts`. The client's voice
rules (offer, tool re-checks, the transcript ledger) are `frontend/lib/voiceRules.ts`, and its one
call controller is `frontend/lib/voiceCall.ts` (decision 0020). The client's media rules
(`checkedMediaJob`, `checkedMediaOptions`, `offeredKinds`) are in `frontend/lib/mediaContract.ts`
and its job store is `frontend/lib/craftMedia.ts` (decision 0021).

| Name | Guarantee |
|---|---|
| `schemas/science`: `CraftProcess` and its parts, `process_claims` | Every material, condition and reaction cites; levels are the weakest input; sources in first-citation order. |
| `schemas/science`: `mhchem_equation`, `reaction_level`, `envelope_status`, `sources_differ`, `cited_source_ids(cited)` (anything with `citations`: claims or answer sentences, the `Cited` protocol), `CONDITION_UNITS`, `SOURCES_DIFFER_*`, `UNBALANCED_*` | The PLAN 7 rules: the equation string built from species, the unbalanced cap at hypothesis, envelope status, the 15 % / 25 °C "sources differ" test, one unit per quantity. |
| `schemas/region`: `CraftRegion`, `MapLayerList`, `MapLayer`, `place_key`, `basis_source_ids`, `split_depth_or_period`, `DATASET_FACETS`, `STATE_AGGREGATIONS`, `BOUNDARY_CAPTION` | Places, values, facets, place sources and layers; which stats aggregate to a state and how; the dataset-to-facet table; the PLAN 8 caption. |
| `schemas/voice`: `VoiceAvailability`, `VoiceSessionRequest`, `VoiceSessionStarted`, `VoiceSessionEnded`, `VoiceTranscript`, `ClientToolCall`, `relay_frame`, `parse_relay_event`, `speech_path` | Session answers by transport, client tools, the relay turn stream (refuses a frame off the contract), spoken replies of at most 60 words that say each cited sentence. |
| `schemas/voice_llm`: `LlmChatRequest`, `LlmChunk`, `LlmError`, `llm_frame`, `llm_error_frame`, `DONE_FRAME`, `VOICE_LLM_PATH`, `CONVERSATION_HEADER` | The OpenAI-compatible custom-LLM wire: inbound fields beyond the contract ignored, outbound chunks strict. |
| `schemas/media`: `MediaJobRequest`, `MediaJobView`, `MediaOptions`, `style_hint_problem`, `MEDIA_PROMPT_BANS`, `MEDIA_FILE_NAME_PATTERN`, `MEDIA_S3_KEY_PATTERN`, the queue and quota constants | Requests carry a stage, never claim ids; status decides asset, failure, refund and polling; the PLAN 11 bans and the PLAN 14.3 names. |

## science/: the science engine (decision 0015)

Pure: no database and no network. Rules and shapes are `docs/contracts/science.md`.

| Name | Guarantee |
|---|---|
| `science/formula`: `parse_formula(text) -> Formula`, `hill_formula(formula)`, `ELECTRON`, `HYDRATE_SEPARATORS` | Element counts and charge of a formula with brackets, hydrate dots and mhchem charges (`Al^3+`, `e^-`); anything else is `InvalidInput` naming the formula. |
| `science/balance`: `balance(species) -> Balance`, `ProposedSpecies`, `composition_matrix`, `CHECKER_VERSION`, `BALANCE_OUTCOMES` | Smallest positive integer coefficients from the sympy integer null space, only when it has exactly one dimension; otherwise `NO_SOLUTION`, `NOT_UNIQUE` or `NOT_POSITIVE` and no coefficients. |
| `science/reactions`: `check_reaction(species) -> CheckedReaction`, `SpeciesProposal` | The only writer of coefficients: takes species without them, returns balance, checker version, the proposed and balanced mhchem equations; species-only (a species without a formula) is unbalanced with no equation. |
| `science/units`: `normalised_bounds(quantity, Bounds, unit) -> Bounds`, `NORMALISED_DIGITS` | Stated bounds to `CONDITION_UNITS` with pint (pH only as `pH`), rounded to 6 decimals; wrong dimensions, unknown units, missing or reversed bounds are `InvalidInput`. |
| `science/envelopes`: `envelope_for`, `envelope_check -> EnvelopeCheck`, `STAGE_ENVELOPES`, `PHYSICAL_CONSTANTS` | PLAN 7's stage envelopes and the cited constants each one rests on (claim keys in `app/data/science_seed.json`). |
| `science/records`: `ProcessRecords` and its records; `science/process_view`: `craft_process(records) -> CraftProcess`, `ordered_claims`, `condition_id` | Stored rows to the contract answer: visible claims only, linked citations only for readings and reactions, the contract's levels, envelopes and "Sources differ", sources in first-citation order; a balanced row without coefficients or a cited source not loaded fails loudly. |

## geo/: the region profile and map layers (decision 0016)

Pure: no database and no network. Rules and shapes are `docs/contracts/region.md`.

| Name | Guarantee |
|---|---|
| `geo/records`: `RegionRecords`, `LocationRecord`, `ValueRecord`, `SeriesTotals`, `Coverage`, `DatasetRecord`, `LayerSpec`, `LayerListing`, `LayerValues`, `GEOLOGY_*`, `LITHOLOGY_TWIN_PREFIX` | The stored rows the services hand over, and how a geology share becomes a value. |
| `geo/places`: `region_places(locations, practice) -> tuple[PlaceRecord, ...]`, `practice_states(names, known)`, `MASTER_LIST_LEVEL`, `NATIONWIDE` | Cited district and state places, one per district or state, the stronger basis first; uncited locations left out and logged. |
| `geo/aggregation`: `state_aggregate(totals, coverage) -> StateAggregate`, `absent_means_zero`, `ABSENT_MEANS_ZERO`, `AGGREGATED_STATS` | Area-weighted means, sums, minima, maxima of a state's districts; sparse series count absent districts as zero; a stat without a state aggregate is `InvalidInput`. |
| `geo/region_view`: `craft_region(records) -> CraftRegion`, `region_facets`, `value_order`; `geo/datasets`: `region_dataset`, `value_grid` | Places, facets in contract order, values in one order, every grid stated (the dataset's native grid when a row has none), cited datasets only, every place's source once; a row without a unit or dataset, or a place source not loaded, fails loudly. |
| `geo/layers`: `MAP_LAYERS`, `LAYERS_BY_ID`, `map_layer_list(listing)`, `map_layer(values)`, `quantile_classes(values)`, `layer_version(parts)`, `layer_unit`, `stored_depth_or_period` | The layer registry; type 7 quantile classes at 3 significant figures; the version is the SHA-256 of the rest of the body. |

## retrieval/: stored-knowledge retrieval (decision 0008)

| Name | Guarantee |
|---|---|
| `retrieval/hybrid`: `StoredKnowledgeSearch(session, *, embed)`, `SessionScopedSearch(sessions, *, embed)`, `craft_scope(session, slug)` | The `KnowledgeRetriever` over Postgres: craft-scoped claims (T1) and chunks (T2), full text and exact pgvector rankings fused by RRF; `SessionScopedSearch` opens one session per search so none is held across model calls. |
| `retrieval/fusion`: `reciprocal_rank_fusion(rankings, *, k=RRF_K)`, `FusedItem`, `RRF_K` | Pure RRF (k 60) with deterministic ties; refuses a ranking that repeats an item. |
| `retrieval/statements`: `CraftScope`, `claim_conditions`, `chunk_conditions`, `*_lexical_ranking`, `*_vector_ranking`, `RANKING_DEPTH` | The SQL of the scope and both rankings, built without a database. |
| `retrieval/text`: `or_tsquery`, `query_text`, `document_text` | The OR text query and the embedding prompts for questions and stored text. |
| `retrieval/chunking`: `chunk_text`, `TextChunk`, `CHUNK_MAX_CHARS` | Pure paragraph-aware chunking with quote-sized overlap and paragraph locators. |
| `retrieval/indexing`: `replace_source_chunks`, `embed_pending`, `embed_written`, `EmbeddedCounts` | Store a source's chunks (vectors kept when unchanged) and fill missing vectors, all of them or only the given claims and sources' chunks, never for restricted or hidden rows. |

## planner/: planning and tiered live research (decision 0009)

| Name | Guarantee |
|---|---|
| `planner/orchestrator`: `ResearchPlanner(*, model, retriever, sources)`, `PlannedQuestion` | The `Planner`, and `research(request) -> EvidencePack`: one plan call, stored coverage per facet, live search of the open facets, dedupe, reading and (deep) open-access copies and cited DOIs. |
| `planner/reading`: `LiveSources`, `DocumentReader`, `reading_order` | The live sources by role; reads the best item per facet first, replaces failed reads within a cap, opens open-access copies through the fetcher. |
| `planner/live_search`: `run_searches`, `merged_evidence`, `evidence_rank`, `SearchHit` | Every query on every source of its tier in parallel within time and result budgets; merge by source key and id; one ranking (trust, agreement, rank, id). |
| `planner/drafting`: `draft_plan`, `plan_schema`, `parsed_draft`, `PlanDraft` | The `PLAN` model call with its strict schema; the question only as untrusted data; one retry, then `ExternalFailure`. |
| `planner/plans`: `retrieval_plan`, `planned_queries`, `native_queries`, `search_query`, `search_question`, `effective_mode`, `open_facets` | Pure: coverage and draft into a `RetrievalPlan`; query egress rules (craft anchor, native craft name for native queries, personal data, withheld terms, dedupe, limit); the English text stored claims are searched with. |
| `planner/coverage`: `facet_coverage`, `covering_claims`, `stored_knowledge` | Stored searches for coverage and for the pack. |
| `planner/references`: `dois_in`, `cited_dois`, `follow_references` | DOIs cited in read text, followed through the DOI source. |
| `planner/failures`: `FailureLog` | Records `ExternalFailure`, `Refused` and timeouts of one live call as `ResearchFailure` and lets everything else raise. |
| `planner/policy`: `LIVE_BUDGETS`, `TierBudget`, `NATIVE_QUERY_SEARCHERS`, `native_query_limit`, the concurrency, timeout and reserve constants | Every live research budget, defined once; native-language queries only where the language has a Wikipedia, only on Wikipedia and Wikidata. |

## composer/: answer composition (decision 0010)

| Name | Guarantee |
|---|---|
| `composer/composer`: `ModelComposer(*, model)`, `assembled_answer` | The `Composer`: one `COMPOSE` call, one retry for an unusable reply or one regenerate of failing sentences, checked sentences only, hypotheses as open questions, else the not-enough-evidence answer. |
| `composer/candidates`: `compose_request(pack, question)`, `research_summary`, `claim_candidate`, `stored_claim_candidate(claim_id, text, level)`, `document_candidate`, `WHOLE_TEXT_MAX_CHARS` | Pack to candidates: stored claims, read documents whole when short or by their verified quotes; what was searched. |
| `composer/prompt`: `COMPOSE_SYSTEM_PROMPT`, `REGENERATE_SYSTEM_PROMPT`, `SOURCE_RULES`, `compose_schema(*, max_sections, max_sentences, max_follow_ups)`, `regenerate_schema`, `compose_message`, `regenerate_message` | Rules in the system prompt; question, passages and failed sentences only inside `untrusted_block`. The voice turn narrows the same schema (decision 0017). |
| `composer/drafts`: `parsed_answer`, `parsed_replacements`, `checked_sentence`, `free_text_problem` | Reply to checked draft sentences; cited ids come from the quotes; headings and follow-ups free of links, markup, personal data (headings also of figures). |
| `composer/translation`: `ModelTranslator(*, model)`, `checked_translation`, `translate_schema`, `translate_message`, `parsed_translations`, `TRANSLATE_SYSTEM_PROMPT` | The `Translator`: one `TRANSLATE` call for every item, failing items asked again once with their problems, items failing twice left out (decision 0023). |

## voice/: the voice pipeline (decision 0017)

Shapes and rules are `docs/contracts/voice.md`. Only `api`, `scripts` and `main` import `voice`.

| Name | Guarantee |
|---|---|
| `voice/records`: `SessionRecord`, `VoiceStore`, `TurnSave`, `AnswerRecord`; `voice/store.SqlVoiceStore(sessions)` | One voice session row as a value (hard end, nonce expiry, liveness) and every database step behind one protocol; the SQL store opens a short session per step and writes a turn's transcript, answer and seconds in one transaction under a row lock. |
| `voice/binding`: `binding_nonce`, `session_nonce`, `nonce_hash`, `session_is_bound`, `bearer_matches`, `hmac_key` (through `core/security.secret_key`) | The contract's HMAC nonce, recomputed from the row and compared in constant time; the agent bearer check. |
| `voice/sessions`: `start_session`, `end_session`, `owned_session`, `may_use_voice`, `VoiceRefused` | The start checks in contract order with stable refusal reasons; ending is idempotent. |
| `voice/languages`: `VOICE_LANGUAGES`, `heard_and_spoken`, `voice_language_options` | The voice languages: answer languages both ElevenLabs models support, in answer order, and their options for `/answers/config` (decision 0025). |
| `voice/turns`: `spoken_turn(TurnAsk, TurnTools) -> SpokenTurn`, `TurnAsk.begun`; `voice/pack`: `VoicePack`, `VoicePackStore`, `ranked_claims`; `voice/compose.voice_composed` | One turn from the claim pack: ranked by the English rendering of the question, stored claims for `VERIFIED`, one checked `VOICE_TURN` compose for `HYBRID`, translated into the session language within the call's hard end, spoken within 60 words in that language with labels and client tools. |
| `voice/spoken`: `spoken_reply`, `spoken_label`, `word_count`; `voice/phrases`: `phrase` and the phrase tables (`FILLERS`, `NO_EVIDENCE_REPLIES`, `NO_CRAFT_REPLIES`, `UNSAID_REPLIES`, `END_CALL_REPLIES`, `SOURCE_WORDS`) | The spoken text and every fixed phrase, for every voice language. |
| `voice/llm.reply_stream`, `voice/agent_turn`: `authorised_session`, `agent_reply`; `voice/relay`: `relay_turn_events`, `turn_speech`, `RelayAudio.checked` | The custom-LLM frames (filler, text, `end_call`, error) and the relay turn stream, with their seconds: a relay turn is claimed (a minute held, one of 40 turns) before speech to text and keeps at least its floor; a reply is synthesised again only during the call or its 2-minute grace, billed under its own key. |
| `voice/audio`: `upload_floor_seconds(content, content_type)`, `wav_seconds(content)` | A relay upload's least billable seconds: a PCM WAV's own length, or compressed bytes over 5 000 a second; past a minute is `Refused("too_long")`, an unreadable WAV `InvalidInput`. |
| `voice/seconds`: ledger keys (`agent_hold_key`, `relay_audio_key`, `relay_refund_key`, `relay_speech_key`, `relay_replay_key`, `refund_key`, `settle_key`), `capped_seconds`, `ledger_entry`, `START_WINDOW_SECONDS`, `AGENT_OCCUPANCY_SECONDS` | Every `VOICE_SECONDS` key in one place; an agent call holds its user's slot for at most the start window plus the longest session. |
| `voice/privacy`: `heard_text`, `TranscriptCipher`; `voice/transcript`: `StoredTranscript`, `turn_merge`, `transcript_view` | Scrubbed heard text; the sealed, versioned transcript and the contract view. |
| `voice/upkeep.run_upkeep`, `voice/upkeep.settle_own_calls(user_id, store, elevenlabs)`, `voice/agent`: `agent_body`, `provision_agent` | Daily close, purge and reconcile, settling agent calls both ways (refund or `voice-settle` charge); the same reconcile for one user's ended calls at their next start; the agent's configuration and idempotent provisioning. |
| `api/multipart_form`: `limited_body(request, limit)`, `form_file(content_type, body, field)` | A request body capped while it streams; exactly one form field, byte for byte. |

## media/: stage illustrations and clips (decision 0018)

Shapes and rules are `docs/contracts/media.md`. Only `api` and the worker (`app/worker.py`) import `media`.

| Name | Guarantee |
|---|---|
| `media/claim_set`: `claim_set(claims, *, acls)`, `enough_claims`, `acls_for(user)`; `schemas/media.names_a_group(text)`, `NAMED_GROUP_WORDS` (singular or plural) | The contract's server-derived claim set: status, sensitivity, restricted sources, levels with readable or passing citations, group words out, strongest first, own before material, at most 8. |
| `media/prompt`: `build_prompt(kind, stage_name, claims, *, style_hint, model) -> MediaPrompt`, `prompt_hash`, `alt_text`, `names_a_place`, `media_ask`, `billed_units`, `REQUESTED_OUTPUT` | Template `media-prompt/v1` with every ban, the hash of the documented material, alt text of whole claims within 1,000 characters, the provider request per kind. |
| `media/bundle`: `sealed_bundle(key, job, *, role, now)`, `opened_bundle(key, bundle, job, *, now) -> role`, `bundle_key(value)` (through `core/security.secret_key`) | The HMAC bundle; a missing, forged, changed or expired one is `Refused` with a stable reason. |
| `media/mp4`: `video_facts(data)`, `without_audio(data)`; `media/output.checked_output(kind, result)`, `png_size` | Size and duration from the video track; audio tracks removed with chunk offsets moved; PNG and MP4 checks before storage. |
| `media/jobs`: `media_options`, `submit_job`, `visible_job`, `MediaDeps`, `MediaRefused`, `idempotency_hash`; `media/views.job_view` | The three routes' steps in contract order, against `MediaStore` and `MediaBudget`; the contract view with a fresh presigned URL. |
| `media/runner`: `run_job(deps, job_id)`, `abandon_job`; `media/queue.MediaQueue`; `media/wiring.media_queue(settings, *, worker_id)` | One attempt (bundle, hold release, generate under the timeout, check, name, upload, store; retry or final with a refund) and the worker loop with per-queue concurrency, stale hand-back and a drain on stop. |
| `media/store.SqlMediaStore`, `media/queue_store.SqlQueueStore`, `media/rows` | The SQL behind `MediaStore` and `QueueStore`: stage facts with the craft's place, the claim facts in three queries, creation under a per-user lock, claims under a per-queue lock with `SKIP LOCKED`, settlements of `MediaJob` and `Job` together. |

## Shared services

| Name | Guarantee |
|---|---|
| `services/audit.record(session, *, action, actor=None, target_type=None, target_id=None, detail=None, ip_hash=None)` | Adds an `AuditLog` row in the caller's transaction, with the request id, and logs the action without its detail. |
| `services/app_settings`: `load_all`, `get_value`, `set_value`, `public_view` | Admin-set settings stored in `AppSetting` (ceilings, prices, sign-up mode, domain allow-list, `voice.transport`, `voice.max_live_sessions`, `voice.voice_id`), with the key names as constants. |
| `services/managed_secrets`: `get_secret`, `peek_secret`, `env_value`, `set_secret`, `delete_secret`, `test_secret`, `list_managed_secrets`, `describe_secret`, `hint`, `fingerprint`, `encrypt`, `decrypt` | Provider keys stored encrypted (Fernet) with the environment as fallback; responses carry a hint and fingerprint, never the value. |
| `services/ai_providers`: `AiProvider`, `AiTask`, `AiModel`, `ProviderSpec`, `spec_for`, `models_for`, `model_for`, `supports`, `allows_data`, `default_model_for`, `looks_like_key`, `catalogue` | The model catalogue, same shapes as the designer portal's: which provider serves which task with which model and price. |
| `services/users.serialize_user(user, *, access_status=None)` | The one user object of `docs/contracts/backend.md`. |
| `services/access_roster`, `services/credential_links` | The access roster and emailed password links, shared by the auth, access and users routes. |
| `services/two_factor` | TOTP, recovery codes, encrypted secrets and attempt budgets, shared by auth, two-step, secrets and users routes. |
| `services/password_accounts`: `upsert_password_account(session, *, email, name, role, password, now) -> PasswordAccount`, `account_by_email`, `operator_password_refusal`, `MIN_OPERATOR_PASSWORD_LENGTH` | An operator-set password account: found by address in any case or created, role and password set, password change off, undeleted, `tokenVersion` bumped on update, and an ACTIVE roster row with that role; passwords 12 to 200 characters. Used by `seed_admin` and `provision_e2e_account`. |
| `services/e2e_account`: `provision_e2e_account(session, password, *, email=E2E_ACCOUNT_EMAIL, now=None)`, `E2E_ACCOUNT_EMAIL`, `E2E_ACCOUNT_ROLE` | The E2E production run's account (decision 0029): a RESEARCHER with a verified email, two-step off and a named roster row; writes no consent. |
| `services/auth_nonces`: `issue_nonce(session, *, purpose, user_id=None, ip_hash=None)`, `consume_nonce(session, raw, *, purpose, user_id=None) -> bool`, `nonce_hash`, `NONCE_MINUTES` | Server sign-in nonces: random, stored only as a SHA-256 hash with a purpose (`AuthNoncePurpose`), 10 minutes, spent at most once. Used by Google sign-in and linking, by Microsoft and Yahoo sign-in (decision 0026) and by the first-password confirmation (`FIRST_PASSWORD`, bound to the account, decision 0028). |
| `services/signed_tokens`: `split_token(token) -> SignedToken`, `check_signature(token, jwks_uri)`, `forget_cached_keys`, `TokenRefused(reason)` | A JWS checked against a provider's published keys: RS256 or ES256 only (refused before any key is read), key matched by `kid`, `use` and `alg`, keys cached an hour and refetched for an unknown key at most once a minute. |
| `services/oidc_sign_in`: `provider(name) -> Provider \| None`, `client_id_if_enabled`, `prove(name, *, code, code_verifier, redirect_uri, raw_nonce) -> ProvedIdentity`, `prove_once(session, grant: CodeGrant, *, purpose, user_id=None) -> ProvedIdentity`, `verify_id_token`, `verified_email`, `nonce_digest`, `acceptable_redirect_uri`, `callback_uri`, `SignInRefused`, `EmailNotVerified` | Microsoft and Yahoo sign-in (decision 0026): a provider exists only with its client ID and secret; the code is redeemed here with the secret and the PKCE verifier; the ID token's issuer, audience, lifetime (a minute of leeway) and nonce digest are checked; the address counts only when the provider verified it. `prove_once` refuses an unconfigured provider or a redirect URI other than the web callback, then spends the nonce of `purpose` (and `user_id`) before redeeming, so a replay costs no provider call; sign-in and the first-password proof both use it. Refusals carry a reason tag and log no credential. |
| `services/provider_proof`: `require_fresh_proof(session, account, proof: ProviderProof, *, now=None) -> str`, `ProviderProof(google_id_token=None, grant=None)`, `ProofRefused(provider, reason)`, `account_provider(account)`, `client_id_for(provider)`, `issued_recently(issued_at, now)`, `NONCE_PURPOSE`, `PROOF_MAX_AGE_SECONDS`, `PROOF_LEEWAY_SECONDS` | The fresh provider proof a first password needs (decision 0028): from the account's own provider (`GOOGLE`, `MICROSOFT` or `YAHOO`), verified as at sign-in, its `FIRST_PASSWORD` nonce bound to the account and spent once, issued within 300 seconds (60 seconds of leeway ahead), for the account's own address. Returns the provider; every refusal is a `ProofRefused` with a reason tag. |
| `services/craft_seed`: `seed_crafts`, `ids_by_slug(session, model)`, `BATCH` | The master-list seed; `ids_by_slug` maps slug to id for any slugged craft table (used by the claim seed and the portal sync). |
| `services/portal_peer`: `PortalPeer`, `peer_for(settings, portal)`, `peer_signature` | The one adapter for the portals' signed peer routes: bearer and nonce out, signature checked in; failures are `ExternalFailure`, `Refused("unsigned_answer")` or `NotConfigured` (`docs/contracts/portal-craft-feed.md`). |
| `services/portal_craft_feed`: `PortalCraftFeed`, `parse_feed`, `PORTALS` | The portal craft feed, validated on load (references resolve, one version). |
| `services/portal_craft_sync`: `run_sync`, `fetch_feeds`, `sync_feeds`, `load_known`, `apply_plan` | Fetch both feeds, plan with `portal_craft_reconcile.plan_sync` (pure), write in one transaction; a failed portal is reported, never silently skipped. |
| `services/craft_index`: `CraftRecord`, `AliasRecord`, `SpellingRecord`, `CraftIndex`, `build_index`, `keys_of`, `EXACT_SCORES`, `GENERIC_TOKENS` | Pure: every matchable name of every active craft keyed by its Latin core key, merged crafts pointing at their target, places per craft (decision 0004). |
| `services/craft_matching`: `lexical_match`, `resolution_from`, `slug_resolution`, `SemanticHit`, the weights | Pure: exact, fuzzy, family, semantic and region signals ranked into a contract `CraftResolution` (`docs/contracts/research.md`). |
| `services/craft_resolver`: `DatabaseCraftResolver`, `CraftIndexStore`, `load_index`, `descriptor_text`, `fill_descriptor_embeddings` | The `CraftResolver` over the database: cached index, pgvector neighbours; fills `Craft.descriptorEmbedding`. |
| `services/live_sources`: `live_sources(session, client)`, `live_source_client()`, `LiveSourcesStore` | Every live searcher, the fetcher client, the Unpaywall locator and the DOI source; the one HTTP client for them, carrying the research contact address. `LiveSourcesStore` holds them for the API process (rebuilt every 600 s on one client, closed at shutdown). |
| `services/write_back_plan.write_back_plan(pack, answer, *, found_by, answer_id) -> WriteBackPlan`, `composed_sentences(answer)` | Pure: composed sentences citing read documents become contract write-backs, labelled and deduped; the rest are skipped with a reason (decision 0011). `composed_sentences` is the one sentence order (sections, then open questions) and `sentence_keys` follows it. |
| `services/live_source_store`: `keep_document`, `source_for`, `chunk_for_quote`, `live_source_id`, `chunk_acl` | Find or create the `Source` of an evidence item (derived id, DOI, URL) and chunk a read document's text, never replacing curated or richer text. |
| `services/claim_writer`: `SqlClaimWriter`, `write_back_claim_id`, `citation_id` | The `ClaimWriter`: derived ids so writes never duplicate, concept and stage linking, per-citation provenance, `HYPOTHESIS` raised to `PROVISIONAL` by a passing quote. |
| `services/research_write_back.store_live_research(session, pack, answer, *, embed, found_by, answer_id=None) -> StoredResearch`, `sentence_claim_ids(answer, stored)` | Documents, claims, commit, embeddings: the one write-back step for the answering service and the coverage job; `sentence_claim_ids` maps each sentence to its stored claims and the claim written for it. |
| `services/knowledge_view.claims_by_id(session, ids)`, `claims_for(session, craft, *, mode, question=None)`, `craft_scope_of(craft)` | Visible claims with their visible citations and sources, by id or by a craft and mode through `retrieval/statements.claim_conditions`, ranked by any word of the question. |
| `services/answering`: `answer_question`, `AnswerAsk`, `AnswerPipeline`, `AnswerStore`, `KeptAnswer`, `status_message`; `services/answer_events`: `CitedClaims`, `cited_claims`, `stored_answer_events`, `composed_answer_events`; `services/answer_store`: `SqlAnswerStore`, `build_answer_pipeline`, `build_answer_translation` | The answer stream end to end (decision 0012): resolve, stored or researched answer, write-back (on `ShieldedWork`, so it finishes when the learner leaves), cited events, status steps, one error and `done`. |
| `services/answer_translation`: `AnswerTranslation`, `TranslationCache`, `Segment`, `translate_segments`, `translated_stored_events`, `translated_composed_events`, `translated_sentences`, `english_question`, `needs_english_rendering`; `services/translation_cache`: `SqlTranslationCache`, `source_sha256` | Verified English answers in the asker's language (decision 0023): claim sentences served from `ClaimTranslation` while the claim text is unchanged, the rest in one checked TRANSLATE call, citations copied, failures left in English; `translated_sentences` is the voice turn's entry point. |
| `services/coverage_selection`: `least_covered_crafts`, `open_questions`, `STANDARD_QUESTIONS`; `services/coverage_enrichment.run_coverage_enrichment` | The daily coverage job within `ENRICHMENT_DAILY_BUDGET_USD`, one `EnrichmentJob` per craft. |
| `services/region_records`: `region_records(session, craft) -> RegionRecords`, `dataset_records(session, codes)`, `region_values()` | A craft's cited locations (a point placed by the polygon that covers it), its states of practice, its districts' values (geology shares in, GLiM twins out), its states' per-series totals over district areas and the `SourceRef` of each place's source, in a fixed number of queries. |
| `services/map_layer_store`: `listed_layers(session) -> LayerListing`, `layer_values(session, spec) -> LayerValues \| None` | The registry layers that have stored values, with their one unit; one layer's district values, or `None` when it has none or the boundary row is missing. |
| `services/craft_process.process_records(session, craft) -> ProcessRecords` | A craft's processes, stages, materials, compounds, reactions, citations, conditions and readings, with their visible claims (`claims_by_id`) and sources, in a fixed number of queries. |
| `services/science_seed`: `seed_science(session)`, `science_seed_plan(science, claims)`, `constants_data`, `load_science_seed`, `SCIENCE_SEED_FILE` | The science seed: constants through `claim_seed.seed_claims`, then compounds, materials, stage materials, reactions (balanced by `check_reaction`), reaction citations, conditions and readings upserted by derived id; the pure plan refuses unknown stages, materials without a kind, missing citations and readings their claim does not state. |
| `services/compound_lookup`: `find_compound(finder, *, name, formula)`, `link_compounds(session, finder, *, now) -> LinkReport`, `pubchem_finder(client)` | A compound's PubChem record by name then Hill formula, accepted only with the same element counts; fills CID, properties and a `COMPOUND_RECORD` source; failures are reported per compound. |
| `services/naming`: `generated_media_file_name(MediaName)`, `file_name(*, entity, what, ext, moment, place, craft, subject, sequence)`, `media_key(owner_id, leaf, *, token=None)`, `content_disposition(leaf, *, inline)`, `field`, `place_field`, `PlaceParts`, `PORTAL` | The one name helper (PLAN 14.3, the naming skill): `KalaVigyan_<Entity>_<IST date (core/clock.INDIA_TZ)>_<HHMM>_<Place>_<Craft>_<Subject>_<What>_<Sequence>.<ext>`, ASCII Title-Case fields through `data/craft_text.to_latin`, a media Subject cut to 40 characters, the 150-character fit (Subject, Craft, Place), `media/<owner>/<uuid32hex>/<leaf>` keys, `filename` plus `filename*=UTF-8''` dispositions; golden rows in `shared/naming-golden.json` (decision 0018). |
| `services/object_store`: `object_store(settings, *, client=None) -> ObjectStore`, `ObjectStore.put(key, body, *, content_type)`, `.presigned_get(key, *, disposition, seconds, now) -> PresignedGet` | The one S3 adapter: SSE-S3 uploads off the event loop, presigned GETs on the bucket's regional virtual-hosted host only, failures as `ExternalFailure` with the shared kinds (decision 0018). |

## Providers (the AI adapter layer)

| Name | Guarantee |
|---|---|
| `providers/router.run(task, *, system, user, json_schema, max_tokens, temperature, texts, principal, request_budget_usd, session_factory) -> RouterResult` | The one way to call a model: reads the task's route order, reserves budget before the call, falls through on retryable failures, settles the actual cost in `UsageEvent`. Raises `RouterError` when no route can serve. |
| `providers/budget`: `evaluate`, `token_cost`, `unit_cost`, `token_price`, `unit_price`, `estimate_tokens`, `month_start`, `day_start`, `budget_today` | Pure spend rules: monthly ceiling, media cap, per-role daily cap, per-request budget, on India days and months (`core/clock.INDIA_TZ`). |
| `providers/base`: `Adapter`, `ChatRequest`, `ChatResult`, `ProviderError` | The adapter interface every provider implements; failures are `ProviderError` (an `ExternalFailure`) with a kind. |
| `providers/registry.build_adapter(*, preset, kind, api_key, api_key_name, ...)` | Builds an adapter from a preset (`providers/presets.PRESETS`); refuses a key name that does not belong to the preset. |
| `providers/usage` | Read token usage from each SDK's responses (Retry-After hints: `core/retry_after`). |
| `providers/structured.router_structured_model(task, principal=None) -> StructuredModel` | A JSON-schema model call through `router.run`, returning the text and the router's degraded flag. |
| `providers/router.tagged_spend(session, *, request_id_prefix, since) -> Decimal` | Spend since a time of the `UsageEvent` rows whose request id starts with the prefix (reservations counted while fresh, as the ceiling does). |
| `providers/embedding.router_embedder(principal=None) -> TextEmbedder` | The one embedding adapter: embeds through `router.run(EMBED)` and checks the vector count and size (`EMBEDDING_DIMENSIONS`). |
| `providers/elevenlabs`: `ElevenLabs(*, api_key, client)`, `speech_seconds(bytes)`, `ConversationToken`, `ConversationRecord`, `HeardSpeech`, `STT_MODEL`, `TTS_MODEL`, `STT_LANGUAGE_CODES`, `TTS_LANGUAGES` | The one ElevenLabs adapter (decision 0017): conversation token, conversation details and deletion, speech to text in the session's Scribe code (seconds to the last word), text to speech with its language code (mp3 at 128 kbit/s); a language its tables lack is refused before any request; agents, client tools and workspace secrets for provisioning. Failures are `ExternalFailure` with the shared kinds and never carry the key; an answer off the documented shape fails loudly. |
| `providers/quota`: `used_today(session, *, user_id, resource, now)`, `remaining_today(user, resource, used)`, `record_units(session, LedgerEntry) -> bool`, `seconds_until_next_day(now)`, `next_day_start(now)` | The `QuotaLedger`: units a user used on the budget time zone's day, what the role's daily allowance leaves (`None` unlimited), one row per idempotency key (a repeat inserts nothing). Resource-neutral: voice seconds and media units. |
| `providers/media_router`: `MediaRouter(*, session_factory, adapter_factory=None, sleep, poll_seconds)` with `.generate(MediaAsk) -> MediaCall`, `.hold(ask)`, `.release(event_id)`, `.available(ask)`, `.first_model(task)`; `media_cost(choice, result, *, units, overrides)` | The router walk for `IMAGE` and `VIDEO`: `RoutePolicy` order, one `router.reserve` per call (media sub-cap and ceiling refuse there), next-route kinds fall through, refusal and bad request stop, video polled and deleted, cost settled from billed tokens (unit price without usage) with a `media price drift` warning past 20 % (decision 0018). |
| `providers/gemini_media.GeminiMediaWire(*, api_key, client)`, `interaction_body`, `interaction_poll`; `providers/base`: `MediaRequest`, `MediaResult`, `MediaPoll`, `Adapter.generate_image`, `.start_video`, `.poll_video`, `.forget_media` | The Interactions API for media (`POST /v1beta/interactions`, `Api-Revision: 2026-05-20`): synchronous unstored images, background video, inline or Files API output, safety refusals as `refusal`, the key sent only to the API host. `GeminiAdapter` implements the media methods; other adapters answer `unavailable`. |
| `providers/router.mark_key_failed(session, key_name, value, message)` | Marks a managed key FAILED after an auth failure (also the media router's). |

## Data and text (shared with `etl/crafts`)

| Name | Guarantee |
|---|---|
| `data/craft_master_loader`: `load_master`, `parse_master`, `master_categories`, `load_aliases`, `craft_aliases`, `with_alias`, `shared_codes`, `seed_plan`, `build_catalogue`, `master_is_current` | Pure reading of the vendored master list and alias files; `master_is_current` checks `shared/craft-master.sha1`. |
| `data/craft_master_loader.normalise`, `codes_normalise`, `token_set_ratio` | The craft-name normalisation the matcher and the catalogue share. |
| `data/craft_text`: `script_of`, `to_latin`, `to_latin_spoken`, `schwa_deleted`, `unaccent`, `fold`, `ascii_key`, `core_key` | Script detection and transliteration of Indic craft names into comparable keys. |
| `data/craft_text`: `alias_norm`, `alias_lang`, `SCRIPT_LANG` | The `CraftAlias.aliasNorm` key (ASCII key for Latin, case and spacing folded for Indic scripts) and an alias's language; shared by `etl/crafts` and the portal sync. |

## Developer tooling (`tools/hygiene/`)

| Name | Guarantee |
|---|---|
| `check.run_check(root, files, *, update_baseline=False) -> HygieneReport` | Runs every hygiene rule over the given files; `--update-baseline` refuses to raise a count. |
| `layers.LAYER_IMPORTS`, `layers.import_violations(sources)` | The allowed import edges in `backend/app`, and the edges that break them. |
| `text_files.encoding_violations(files)` | UTF-8 without a byte-order mark, LF only; binary files by suffix (`BINARY_SUFFIXES`). |
| `comments.comment_violations(sources)` | Python comments other than functional directives (`noqa`, `type: ignore`, `pragma:`, `fmt:`, a first-line shebang). |
| `budgets.measure_budgets(sources)` | Files over 400 lines, functions over 40 lines, functions with more than 5 positional parameters. |
