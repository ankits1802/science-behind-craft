# Shared code catalogue

Every shared backend component, with what it guarantees. Check here before writing a helper; if
what you need is close to something listed, extend it. A component enters this list when a
second real caller exists, and leaves it in the same change that deletes it.

Paths are under `backend/app/`. Last reviewed: 2026-11-16.

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

## core/roles.py: roles and capabilities

| Name | Guarantee |
|---|---|
| `MASTER_ADMIN`, `PROFESSOR`, `RESEARCHER`, `STUDENT`, `ROLE_RANK`, `ROLE_LABELS`, `ROLES_BY_RANK` | The role vocabulary and ranks (60, 40, 30, 15). |
| `Capability`, `CAPABILITY_MIN_ROLE` | Every capability and the lowest role that holds it. |
| `can(user_or_role, capability) -> bool` | Unknown roles hold nothing. |
| `capabilities_of`, `role_value`, `role_rank`, `has_rank`, `is_known_role`, `is_master_admin` | Read a role from a user object or a role string. |
| `assignable_roles(actor)`, `may_assign(actor, role)`, `may_manage_target(actor, target)` | The master admin assigns and manages every role; an actor with MANAGE_ACCESS only roles ranked below its own; anyone else none. |
| `requires_two_factor(user_or_role)`, `TWO_FACTOR_REQUIRED_ROLES` | Professor and master admin must have TOTP. |
| `daily_allowance(user_or_role, resource)`, `DAILY_ALLOWANCES` | Per-role daily limits; `None` means unlimited. |

## core/deps.py: request dependencies

| Name | Guarantee |
|---|---|
| `get_current_user` | The signed-in, active user whose token version matches; refuses with 401 or 403 and the contract headers when a password change or 2FA setup is pending. |
| `get_current_user_any_step` | Same, but allows the pending-step routes. |
| `require(capability)` | Dependency factory that refuses with 403 and a capability-specific sentence (`refusal_for`). |
| `require_master_admin` | Master admin only. |
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
| `sign_in_attempt_by_ip`, `sign_in_attempt_by_account`, `forgot_password_attempt`, `code_attempt`, `ask_attempt` and their `refund_*` | The named limits used by auth, two-step and asking. |
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

## research/: research and answering contracts

Shapes and rules are in `docs/contracts/research.md` (decision 0002).

| Name | Guarantee |
|---|---|
| `research/base`: `ContractModel`, `HttpsUrl`, `PartialDate` | Frozen, extra-forbidding models with camelCase JSON; https-only URLs; partial ISO dates. |
| `research/vocabulary`: literal types, `LEVEL_ORDER`, `LABEL_LEVELS`, `weakest_level(levels)` | Vocabulary built from `models/enums.py`; the one rule for combining evidence levels. |
| `research/quotes`: `normalise_quote_text`, `quote_key`, `quote_occurs`, `trivial_quote`, `quote_overlap`, `figures_in`, `unsupported_figures`, `QUOTE_MIN_CHARS`, `QUOTE_OVERLAP_MIN` | The verbatim-quote check on whole words and numbers, the minimum quote length, the sentence-to-quote overlap and the "every figure is cited" check (decision 0013). |
| `research/licences.open_licence(licence)` | Whether a licence string is an allow-listed open licence (CC0, CC BY, CC BY-SA, PDDL, public domain) by name or canonical URL; everything else is closed (decision 0013). |
| `research/crafts.craft_block(craft)` | The craft name and slug as one untrusted block for model prompts. |
| `research/vocabulary`: `ANSWER_LANGUAGES`, `ANSWER_LANGUAGE_LABELS`, `AnswerLanguage` | The answer languages offered by `/answers/config` and accepted by the ask route, plan and compose requests. |
| `research/crafts`: `CraftRef`, `CraftQuery`, `CraftResolution`, `CraftResolver`, `clear_winner` | Craft resolution types and the accept rule (0.85, margin 0.15). |
| `research/evidence`: `EvidenceItem`, `Quote`, `SearchQuery`, `SourceDocument`, `SourceAdapter`, `canonical_url`, `personal_data_in`, `DOI_PATTERN` | One adapter interface for every external source; quotes are backed by the document text. |
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
| `sources/reference/mediawiki`: `action_api(http, endpoint, params)`, `pages_in_order`, `page_revision`, `rights_text`, `primary_language`, `WIKIMEDIA_RATE` | The MediaWiki Action API for every Wikimedia adapter: JSON format 2 with plaintext errors, API errors inside a 200 raised as `ExternalFailure` with a kind, search pages in rank order, the latest revision id and date, the wiki's licence text, and a language tag reduced to its checked primary subtag (decision 0006). |
| `sources/reference/registry`: `reference_sources(client)` | Builds the Wikipedia, Wikidata (with its SPARQL pacing), PubChem and Wikimedia Commons adapters, each with its own pacing and cache. |
| `services/scholarly_keys.scholarly_keys(session)` | Reads `SCHOLARLY_KEY_NAMES` from the managed secrets and `RESEARCH_CONTACT_EMAIL` from settings. |
| `services/web_sources.web_search_config(session)` | The web search settings: `SEARXNG_URL` and the managed `BRAVE_SEARCH_API_KEY`. |
| `services/live_sources.live_sources(session, client)`, `DOI_SOURCE` | Every live source for the planner: scholarly, reference and web adapters, one `FetcherClient` (`FETCHER_URL`), the Unpaywall locator and Crossref for cited DOIs. Hold it for the process. |

## schemas/common.py: request and page shapes

| Name | Guarantee |
|---|---|
| `APIModel` | Base for request bodies: unknown fields refused, strings stripped, camelCase or field names accepted. |
| `normalize_pagination(page, page_size)`, `page_payload(items, total, page, page_size)`, `MAX_PAGE_SIZE` | One page shape (`items`, `total`, `page`, `pageSize`, `pages`) with size capped at 200. |

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
| `planner/plans`: `retrieval_plan`, `planned_queries`, `search_query`, `effective_mode`, `open_facets` | Pure: coverage and draft into a `RetrievalPlan`; query egress rules (craft anchor, personal data, withheld terms, dedupe, limit). |
| `planner/coverage`: `facet_coverage`, `covering_claims`, `stored_knowledge` | Stored searches for coverage and for the pack. |
| `planner/references`: `dois_in`, `cited_dois`, `follow_references` | DOIs cited in read text, followed through the DOI source. |
| `planner/failures`: `FailureLog` | Records `ExternalFailure`, `Refused` and timeouts of one live call as `ResearchFailure` and lets everything else raise. |
| `planner/policy`: `LIVE_BUDGETS`, `TierBudget`, the concurrency, timeout and reserve constants | Every live research budget, defined once. |

## composer/: answer composition (decision 0010)

| Name | Guarantee |
|---|---|
| `composer/composer`: `ModelComposer(*, model)`, `assembled_answer` | The `Composer`: one `COMPOSE` call, one retry for an unusable reply or one regenerate of failing sentences, checked sentences only, hypotheses as open questions, else the not-enough-evidence answer. |
| `composer/candidates`: `compose_request(pack, question)`, `research_summary`, `claim_candidate`, `document_candidate`, `WHOLE_TEXT_MAX_CHARS` | Pack to candidates: stored claims, read documents whole when short or by their verified quotes; what was searched. |
| `composer/prompt`: `COMPOSE_SYSTEM_PROMPT`, `REGENERATE_SYSTEM_PROMPT`, `compose_schema`, `regenerate_schema`, `compose_message`, `regenerate_message` | Rules in the system prompt; question, passages and failed sentences only inside `untrusted_block`. |
| `composer/drafts`: `parsed_answer`, `parsed_replacements`, `checked_sentence`, `free_text_problem` | Reply to checked draft sentences; cited ids come from the quotes; headings and follow-ups free of links, markup, personal data (headings also of figures). |

## Shared services

| Name | Guarantee |
|---|---|
| `services/audit.record(session, *, action, actor=None, target_type=None, target_id=None, detail=None, ip_hash=None)` | Adds an `AuditLog` row in the caller's transaction, with the request id, and logs the action without its detail. |
| `services/app_settings`: `load_all`, `get_value`, `set_value`, `public_view` | Admin-set settings stored in `AppSetting` (ceilings, prices, sign-up mode, domain allow-list), with the key names as constants. |
| `services/managed_secrets`: `get_secret`, `peek_secret`, `env_value`, `set_secret`, `delete_secret`, `test_secret`, `list_managed_secrets`, `describe_secret`, `hint`, `fingerprint`, `encrypt`, `decrypt` | Provider keys stored encrypted (Fernet) with the environment as fallback; responses carry a hint and fingerprint, never the value. |
| `services/ai_providers`: `AiProvider`, `AiTask`, `AiModel`, `ProviderSpec`, `spec_for`, `models_for`, `model_for`, `supports`, `allows_data`, `default_model_for`, `looks_like_key`, `catalogue` | The model catalogue, same shapes as the designer portal's: which provider serves which task with which model and price. |
| `services/users.serialize_user(user, *, access_status=None)` | The one user object of `docs/contracts/backend.md`. |
| `services/access_roster`, `services/credential_links` | The access roster and emailed password links, shared by the auth, access and users routes. |
| `services/two_factor` | TOTP, recovery codes, encrypted secrets and attempt budgets, shared by auth, two-step, secrets and users routes. |
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
| `services/answering`: `answer_question`, `AnswerAsk`, `AnswerPipeline`, `AnswerStore`, `KeptAnswer`, `status_message`; `services/answer_events`: `CitedClaims`, `cited_claims`, `stored_answer_events`, `composed_answer_events`; `services/answer_store`: `SqlAnswerStore`, `build_answer_pipeline` | The answer stream end to end (decision 0012): resolve, stored or researched answer, write-back, cited events, status steps, one error and `done`. |
| `services/coverage_selection`: `least_covered_crafts`, `open_questions`, `STANDARD_QUESTIONS`; `services/coverage_enrichment.run_coverage_enrichment` | The daily coverage job within `ENRICHMENT_DAILY_BUDGET_USD`, one `EnrichmentJob` per craft. |

## Providers (the AI adapter layer)

| Name | Guarantee |
|---|---|
| `providers/router.run(task, *, system, user, json_schema, max_tokens, temperature, texts, principal, request_budget_usd, session_factory) -> RouterResult` | The one way to call a model: reads the task's route order, reserves budget before the call, falls through on retryable failures, settles the actual cost in `UsageEvent`. Raises `RouterError` when no route can serve. |
| `providers/budget`: `evaluate`, `token_cost`, `unit_cost`, `token_price`, `unit_price`, `estimate_tokens`, `month_start`, `day_start`, `budget_today` | Pure spend rules: monthly ceiling, media cap, per-role daily cap, per-request budget, in the plan's budget time zone. |
| `providers/base`: `Adapter`, `ChatRequest`, `ChatResult`, `ProviderError` | The adapter interface every provider implements; failures are `ProviderError` (an `ExternalFailure`) with a kind. |
| `providers/registry.build_adapter(*, preset, kind, api_key, api_key_name, ...)` | Builds an adapter from a preset (`providers/presets.PRESETS`); refuses a key name that does not belong to the preset. |
| `providers/usage` | Read token usage from each SDK's responses (Retry-After hints: `core/retry_after`). |
| `providers/structured.router_structured_model(task, principal=None) -> StructuredModel` | A JSON-schema model call through `router.run`, returning the text and the router's degraded flag. |
| `providers/router.tagged_spend(session, *, request_id_prefix, since) -> Decimal` | Spend since a time of the `UsageEvent` rows whose request id starts with the prefix (reservations counted while fresh, as the ceiling does). |
| `providers/embedding.router_embedder(principal=None) -> TextEmbedder` | The one embedding adapter: embeds through `router.run(EMBED)` and checks the vector count and size (`EMBEDDING_DIMENSIONS`). |

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
