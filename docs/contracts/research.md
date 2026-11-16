# Research and answering contract

The interfaces between the lanes that resolve crafts, plan retrieval, search and fetch sources,
compose answers, write findings back as claims, and stream the answer to the web client. The
code is the typed models, protocols and error types in `backend/app/research/` and
`backend/app/core/errors.py`; this page says what they mean. Build adapters, planners, composers
and writers against these types and change a type only together with this page and its tests
(`backend/tests/research/`). Design choices: decision 0002.

Last reviewed: 2026-11-16.

## Ground rules (PLAN section 0 and the bindings)

- Knowledge grows: when stored claims cannot answer, live research runs and what it finds is
  written back as cited claims. Accuracy over speed; a learner can wait.
- Research is not limited to the sources named in the plan. Any reachable scholarly, government,
  museum, archive or open-web source may be an adapter, and the answer cites what was used.
- Every crafts lookup covers every `Craft` row: the 455 master crafts and the crafts synced from
  the designer and documentation portals. A craft is named by its `slug` (case as stored, for
  example `Kutch-Ajrakh`).
- Every sentence shown is cited; every number and formula in it appears in a cited claim or
  quote. No review gates: evidence levels are labels, nothing waits for approval.
- Retrieved text, search results and model output are data, never instructions.

## Shape conventions

- Models derive from `research.base.ContractModel`: unknown fields refused, frozen, strings
  stripped, Python names in snake_case, JSON in camelCase (`craft_slug` is `craftSlug`). Both
  spellings are accepted on input; output is always camelCase.
- URLs are `https://` only (`HttpsUrl`), at most 2048 characters, no whitespace.
- Dates of publication are partial ISO dates (`PartialDate`): `YYYY`, `YYYY-MM` or `YYYY-MM-DD`.
  Instants (`retrievedAt`, `fetchedAt`) carry a time zone.
- Vocabulary comes from `research/vocabulary.py`, which builds its literal types from
  `models/enums.py` (one home): `AnswerMode` (`VERIFIED`, `HYBRID`, `DEEP`), `EvidenceLevel`,
  `ShownLevel` (the levels plus `UNAVAILABLE`), `RetrievalTier` (`T0`-`T4`), `LiveTier`
  (`T3`, `T4`), `TrustTier` (reliability `A`-`D`), `SourceType` (`SourceKind`), `FacetType`
  (`ConceptType`), `QuoteCheck`, `SourceRelation`, and `EvidenceLabel` (`QUOTED`, `INFERRED`).
- `weakest_level(levels)` is the one rule for combining levels (VERIFIED > REVIEWED >
  PROVISIONAL > HYPOTHESIS); a sentence or derived artefact takes the weakest of its inputs.

## Errors (`core/errors.py`)

One hierarchy for the whole backend; catch by category.

| Class | Meaning | Existing equivalent |
|---|---|---|
| `AppError` | base of everything below | |
| `InvalidInput` (also a `ValueError`) | the caller sent something the contract refuses | 422; `RouterError("bad_request")` |
| `Refused(reason, message)` | a guard said no; `reason` is a stable code | `RouterError("ceiling", reason=...)` |
| `NotConfigured(name, message)` | a key, setting or route is missing | `RouterError("no_route")`, `SettingsError` |
| `ExternalFailure(message, kind=, retryable=, status=, retry_after=, service=)` | a call to another service failed | `ProviderError` is now a subclass |

`ExternalFailure.kind` is one of `FAILURE_KINDS`: `rate_limit`, `unavailable`, `auth`,
`not_found`, `error` (try the next adapter or route: `NEXT_ROUTE_KINDS`, `tries_next`) and
`refusal`, `bad_request` (stop: `STOP_KINDS`, which the AI router imports). Any other kind is a
`ValueError` at construction. `RouterError` derives from `AppError`. `failure_kind(status)` is
the one mapping from an HTTP status to a kind (429 `rate_limit`, 5xx `unavailable`, 401 and 403
`auth`, 404 and 410 `not_found`, 400 and 422 `bad_request`, anything else `error`), and
`RETRYABLE_KINDS` (`rate_limit`, `unavailable`) are the kinds marked retryable.

## Craft resolution (`research/crafts.py`)

`CraftResolver.resolve(CraftQuery) -> CraftResolution`.

- `CraftQuery {text (1-1000), craftSlug?, language?}`. `text` is in any script; the resolver
  normalises it with `data/craft_text` and `data/craft_master_loader.normalise` (PLAN 5.2).
- `CraftRef {slug, name, path}`; `path` is always `/crafts/<slug>`. This is the stream's craft
  shape.
- `CraftCandidate {craft, score 0-1, reasons[MatchReason] (at least one)}`;
  `MatchReason {kind, matched, score}` with `kind` one of `EXACT_SLUG`, `EXACT_NAME`,
  `EXACT_ALIAS`, `EXACT_SPELLING`, `MERGED_REDIRECT`, `FUZZY`, `SEMANTIC`, `PLACE`, `FAMILY`,
  `MODEL_CHOICE`, and `matched` the alias, spelling or place that matched.
- `CraftResolution {status, craft, candidates (at most 5, highest score first), normalised,
  script}`. `RESOLVED`: `craft` is the top candidate. `AMBIGUOUS`: no craft, 1-5 candidates
  (the pills; one pill is a "did you mean"). `NONE`: no craft, no candidates. `normalised` is
  `craft_text.core_key(text)`; `script` is `craft_text.script_of` (`Latn`, `Deva`, `Zyyy`, ...).
- Decision constants (PLAN 5.2): accept when `clear_winner(candidates)`: top score at least
  `ACCEPT_SCORE` 0.85 and at least `ACCEPT_MARGIN` 0.15 above the runner-up;
  `FUZZY_MIN_SIMILARITY` 0.85 (rapidfuzz `ratio`, not `pg_trgm`; decision 0004);
  `MAX_CANDIDATES` 5.
- `stream.match_event(resolution)` turns a resolution into the `match` event.

### The resolver (`services/craft_resolver.py`, decision 0004)

`DatabaseCraftResolver(session, store=CraftIndexStore, embed=TextEmbedder)` implements
`CraftResolver` over every `Craft` row. The pure index and ranking are `services/craft_index.py`
and `services/craft_matching.py`; the answer flow builds one per request with
`providers/embedding.router_embedder(principal)`, which embeds through the AI router (`EMBED`).
The embedding protocol is `research/embedding.py`: `TextEmbedder` (texts in, one vector each
out) and `checked_vectors(vectors, expected=)`, which raises `ExternalFailure` (service
`embeddings`) unless there is one vector per text of `EMBEDDING_DIMENSIONS` (1536).

- **Index** (`load_index`, cached by `CraftIndexStore` for `INDEX_TTL_SECONDS` 300): every
  `ACTIVE` craft; a `MERGED` craft's names point at the end of its `mergedIntoId` chain (at most
  `MAX_REDIRECT_HOPS` 5); `LEGACY` crafts and unfinished chains are left out. Names come from
  `Craft.name` (`EXACT_NAME`), `Craft.localName` and `ACTIVE` `CraftAlias` rows (`EXACT_ALIAS`),
  and `CraftSpelling` labels through `craftCode` (`EXACT_SPELLING`). Each is keyed by
  `core_key(text)` and `core_key(to_latin_spoken(text))`, at least `MIN_KEY_CHARS` 4 long.
  Places are `stateOfPractice`, `stateOfOrigin`, and each `CraftLocation`'s label, district and
  state name (`All India` is not a place). Catch-all crafts are reachable only by slug.
- **Slug** (`craftSlug` given): exact, case as stored; score 1.0, `EXACT_SLUG`, or
  `MERGED_REDIRECT` for a merged slug. An unknown slug is `NONE`; text is not tried.
- **Exact**: every phrase (1-8 tokens) of the question's key is looked up; a hit inside a longer
  hit is dropped (`Kutch Ajrakh` beats `Ajrakh`). Scores: name or slug 1.0, alias or merged
  redirect 0.97, spelling 0.95. For Indic text the reading (inherent-vowel or spoken Latin)
  with the most tokens matched exactly is used.
- **Fuzzy**: phrases not covered by an exact hit or a place, rapidfuzz `ratio` against every key
  (`FUZZY`, weight 0.95) and against every distinctive name token (`FAMILY`, weight 0.7; a token
  of at most 8 crafts and not in `GENERIC_TOKENS`, so `dhokra` offers the Dhokra crafts), at
  least `FUZZY_MIN_SIMILARITY`, top 10 per phrase.
- **Semantic**: only when the lexical ranking has no clear winner and at least one craft has a
  `descriptorEmbedding`: the question is embedded and the 10 nearest `ACTIVE`, non-catch-all
  crafts by cosine are taken; similarity at least 0.6, weight 0.8, so semantic alone never
  resolves. `descriptor_text` (name, local name and aliases joined by `; `) is what
  `fill_descriptor_embeddings` embeds (`app/scripts/embed_craft_descriptors.py`).
- **Fusion**: a candidate's score is its best weighted reason plus 0.05 for each further kind
  of signal (exact, fuzzy or family, semantic), at most 1. When the question names a place
  (outside any craft name) and at least one candidate is practised there, every candidate's
  score becomes `0.8 * score + 0.2 * (named place matches)`, with a `PLACE` reason. Ranked by
  score, then name; at most 5; reason scores and candidate scores are rounded to 6 places.
- **Decision**: `clear_winner` gives `RESOLVED`; otherwise any candidates give `AMBIGUOUS`;
  none give `NONE`. The model choice of PLAN 5.2 step 6 is not built (`docs/TECH_DEBT.md`).
- **Failures**: an embedding failure is an `ExternalFailure` (or the router's `RouterError`);
  the answer stream turns any `AppError` from the resolver into one `error` event and `done`.

## Evidence and source adapters (`research/evidence.py`)

One adapter per external service (OpenAlex, Crossref, Semantic Scholar, CORE, Unpaywall,
Wikipedia, Wikidata, PubChem, SearXNG, Brave, any later source), each implementing:

```
class SourceAdapter(Protocol):
    name: str            # ^[a-z][a-z0-9_]{1,39}$, e.g. "openalex"
    tier: LiveTier       # T3 scholarly and reference APIs, T4 open-web search
    async def search(self, query: SearchQuery, k: int) -> list[EvidenceItem]
    async def fetch(self, item_id: str) -> SourceDocument
```

- `SearchQuery {text (2-300), facet?, language="en", freshnessDays?}`. Construction refuses
  text carrying an email address, a phone-like run of 10+ digits or an Aadhaar-like 12-digit
  run (PLAN 6, search egress). Queries are built from the resolved craft name, sub-category
  and facet targets; anything else passes this scrub first.
- `search` returns at most `k` items (`1 <= k <= SEARCH_MAX_K` 50), each `tier` equal to the
  adapter's, best first. No hits is `[]`, not an error.
- `EvidenceItem {id, adapter, tier, sourceType, url, title, authors[], published?, retrievedAt,
  licence?, attribution?, doi?, publisher?, trust, quotes[Quote], externalIds{}}`.
  `id` is `<adapter>:<id at the service>` (`openalex:W2741809807`). `trust` is the reliability
  tier the adapter assigns (A peer-reviewed or official, B reputable reference, C general web,
  D unknown). `quotes` are verbatim passages (`Quote {text (1-300), locator?}`; locator such as
  `p. 12`, `section 3.2`, `para 4`); a search hit may have none.
- `item.source_key` is the source identity for dedupe: `doi:<lowercased doi>`, else
  `url:<canonical url>` (lowercased scheme and host, default port and fragment dropped,
  trailing slash removed except the root).
- `fetch(item_id)` returns `SourceDocument {item, text, textSha256, truncated, content}`:
  `text` is the cleaned plain text the quotes were taken from, `textSha256` its SHA-256 in
  UTF-8, `content` one of `FULL_TEXT`, `ABSTRACT`, `EXCERPT`. Construction fails unless every
  quote in `item.quotes` occurs in `text` (`quotes.quote_occurs`). Only `T4` adapters and
  full-text fetches go through the fetcher sandbox; API adapters fetch their own JSON.
- Failures: `ExternalFailure` with a kind (an unknown id is `not_found`), `NotConfigured` for a
  missing key, `Refused` for a guard. Adapters never log keys or raw responses.

### Open-access locator

```
class OpenAccessLocator(Protocol):
    name: str
    async def locate(self, doi: str) -> OpenAccessLocation
```

`OpenAccessLocation {doi, status, landingUrl?, pdfUrl?, licence?, version?, hostType?,
checkedAt}`; `status` is one of `OPEN_ACCESS_STATUSES` (`GOLD`, `DIAMOND`, `HYBRID`, `BRONZE`,
`GREEN`, `CLOSED`), `isOpen` is any status but `CLOSED`, and a `CLOSED` location carries no
URL or `hostType` (`PUBLISHER`, `REPOSITORY`). URLs are https only, so an open work may carry
none. A text that is not a DOI is `InvalidInput`; an unknown DOI is `not_found`. Unpaywall is
the locator: its title search is retired (decision 0005), so it is not a `SourceAdapter`.

### Scholarly adapters (`app/sources/`, decision 0005)

`sources.scholarly.registry.scholarly_sources(keys, client) -> ScholarlySources {adapters,
locator, unconfigured}` builds every T3 scholarly adapter; `services/scholarly_keys.
scholarly_keys(session)` reads the keys from the managed secrets and `RESEARCH_CONTACT_EMAIL`.
The caller holds the result for the process (each adapter paces itself and caches for 600 s).

| Adapter `name` | Service | Key | Id after the colon | `fetch` content |
|---|---|---|---|---|
| `openalex` | OpenAlex works | `OPENALEX_API_KEY` optional | `W…` | `ABSTRACT` |
| `crossref` | Crossref works (polite pool, abstracts only) | none | DOI | `ABSTRACT` |
| `semantic_scholar` | Semantic Scholar Graph | `SEMANTIC_SCHOLAR_API_KEY` optional | paper id | `ABSTRACT` |
| `core` | CORE v3 | `CORE_API_KEY`; without it left out and listed in `unconfigured` | work id | `FULL_TEXT`, else `ABSTRACT` |
| `europe_pmc` | Europe PMC REST | none | `<SRC>:<id>` | `ABSTRACT` |
| `arxiv` | arXiv API | none | arXiv id with version | `ABSTRACT` |
| `doaj` | DOAJ v4 articles | none | 32 hex | `ABSTRACT` |
| `elsevier` | Scopus search and abstract | `ELSEVIER_API_KEY` (+ `ELSEVIER_INSTTOKEN`); dormant, left out silently | Scopus id | `ABSTRACT` |
| `springer_nature` | Springer Nature open access | `SPRINGER_NATURE_API_KEY`; dormant, left out silently | DOI | `ABSTRACT` |

Search hits carry no quotes; `fetch` returns the text quotes are taken from. A record with no
text to return is `not_found`. Trust: journal articles, books and chapters `A`; preprints,
repository copies, datasets, theses and reports `B`; anything else `C`. `freshnessDays` keeps
dated items whose latest possible day is on or after the cutoff.

### Reference adapters (`app/sources/reference/`, decision 0006)

`sources.reference.registry.reference_sources(client) -> tuple[HttpSourceAdapter, ...]` builds
the four T3 reference adapters; none needs a key.

| Adapter `name` | Service | Id after the colon | `fetch` content | Source type, trust | Licence |
|---|---|---|---|---|---|
| `wikipedia` | Action API search and TextExtracts | `<language>:<page id>` | `FULL_TEXT` | `ENCYCLOPEDIA`, `B` | the wiki's rightsinfo text, read live |
| `wikidata` | `list=search`, `wbgetentities`, SPARQL statements | `Q…` | `EXCERPT` | `DATASET`, `B` | `CC0 1.0` |
| `pubchem` | PUG REST (names, formulas, properties), PUG View (GHS) | `<CID>` or `<CID>:ghs` | `EXCERPT` | `COMPOUND_RECORD`, `A` | NCBI policy URL; for `:ghs` the reporting sources' licence URLs |
| `wikimedia_commons` | Action API file search with `extmetadata` | page id | `EXCERPT` | `OTHER`, `C` | the file's licence short name |

- `SearchQuery.language` picks the Wikipedia (`WIKIPEDIA_LANGUAGES`: English and the Indian
  languages with a Wikipedia; another language is `InvalidInput`), the Wikidata label language
  (with fallback) and the Commons metadata language. Fetches of Wikidata and Commons render
  in English.
- Wikipedia items carry `externalIds` `wikipedia`, `revision` and `wikidata`; Wikidata items
  `wikidata`, `revision` and, on fetch, `pubchem_cid`, `cas_number`, `chebi` when stated;
  PubChem items `pubchem_cid` and `inchikey`; Commons items `commons_file`, `commons_media`
  and `revision`. Attributions name the revision read (Wikimedia) or the reporting source
  (PubChem hazards).
- A PubChem query that is a molecular formula (real element symbols) searches by formula;
  anything else by complete name, then by words, exact matches first. The hazards of a
  compound are `fetch("pubchem:<cid>:ghs")`; a compound without attributed GHS data is
  `not_found`.
- MediaWiki errors returned inside a 200 are `ExternalFailure`: unknown entity, title or page
  `not_found`, rate limits `rate_limit`, read-only `unavailable`, anything else `error`.
- Commons files without a licence are left out of results. Wikidata time values coarser than a
  year, and deprecated statements, are left out of the text.

### Web search adapters (`app/sources/web/`, decision 0007)

| Adapter `name` | Service | Key | Id after the colon | `fetch` content | Source type, trust |
|---|---|---|---|---|---|
| `searxng` | SearXNG JSON API at `SEARXNG_URL` | none | the https URL | `FULL_TEXT` through the fetcher | `WEB_PAGE` (`OTHER` for a PDF), `C` |
| `brave` | Brave Web Search API | `BRAVE_SEARCH_API_KEY`; without it left out silently | the https URL | `FULL_TEXT` through the fetcher | `WEB_PAGE` (`OTHER` for a PDF), `C` |

- Hits carry no quotes (snippets are not verbatim). Plain-http hits and URLs that would make an
  id longer than `EVIDENCE_ID_MAX_CHARS` (500) are left out. SearXNG maps `freshnessDays` to the
  narrowest `time_range` that covers it (day, week, month, year); Brave sends the exact date
  window; the date filter of the scholarly adapters then applies to both. Brave asks for at
  most 20 results.
- `fetch` sends a `FetchRequest` for the URL in the id and returns the page text with the item
  rebuilt from the page: `url` is the final URL, title (else the final URL), authors,
  published, licence and site name (as `publisher`) from the page metadata, `retrievedAt` the
  fetch time, `externalIds.sha256` the raw body's hash. `truncated` carries the fetcher's.
- `sources.web.fallback.WebSearch` (`name` `web`, `T4`) is the one web search the planner
  calls: SearXNG first; when it returns fewer than `min(WEB_FALLBACK_MIN_HITS, k)` hits (3) or
  fails, Brave (if configured) is asked and its hits new by `source_key` are appended, at most
  `k`. A SearXNG failure without Brave is raised; both failing raises Brave's failure chained to
  SearXNG's; a Brave failure after some SearXNG hits keeps them. `fetch` goes to the adapter
  the id names. Built by `sources.web.registry.web_search(WebSearchConfig, client, fetcher)`;
  `services.web_sources.web_search_config(session)` reads `SEARXNG_URL` and the managed Brave
  key, and `services.live_sources` passes the one fetcher client (below).

### Quote matching (`research/quotes.py`)

`normalise_quote_text`: NFKC, soft hyphens removed, a hyphen at a line break joined, typographic
dashes and quotation marks folded to ASCII, whitespace collapsed. `quote_occurs(quote, text)`
compares with `quote_key`, which also drops hyphens between letters (`dye-stuff` matches
`dyestuff`). Case is kept: a quote is verbatim. A quote starts and ends on a word boundary when
its edge is a letter or digit, and never inside a decimal: `50` does not occur in `1500`, nor `1`
in `1.5`. `trivial_quote(quote)` is true below `QUOTE_MIN_CHARS` (20) folded characters.
`quote_overlap(text, quotes)` is the share of the text's content words (four or more letters, not
a stop word, compared by their first four letters) that occur in the quotes (decision 0013).

## Fetcher (`research/fetcher.py`)

`Fetcher.fetch(FetchRequest) -> FetchedPage`, run by the sandboxed `kv-fetcher.service`.

- `FetchRequest {url (https), timeoutSeconds <= 10, maxBytes <= 3 MiB}`: a caller may tighten
  the caps, never loosen them.
- `FetchedPage {url, finalUrl, redirects[] (at most 3), status 2xx, contentType, bytes,
  sha256 (of the raw body), fetchedAt, text (at most 200,000 characters), truncated,
  metadata}`; `finalUrl` is the last redirect, or `url` when none.
  `PageMetadata {title?, authors[], published?, licence?, canonicalUrl?, siteName?, language?}`.
- `contentType` is `text/html`, `application/pdf` or `text/plain`.
- Sandbox rules (PLAN 6): https only; every resolved A/AAAA address checked and refused when
  private, loopback, link-local, CGNAT, ULA or metadata; connect to the pinned address and
  verify the certificate for the original host; each redirect re-checked; robots.txt honoured;
  PDF parse capped at `PDF_MAX_PAGES` 50 and `PDF_MAX_DECOMPRESSED_BYTES` 20 MiB; scripts,
  styles and hidden text dropped. The fetcher has no database and no AWS credentials.
- A rule that stops a fetch raises `FetchRefused(url, reason, detail)` (a `Refused`); `reason`
  is one of `NOT_HTTPS`, `BAD_URL`, `PRIVATE_ADDRESS`, `TLS_MISMATCH`, `TOO_MANY_REDIRECTS`,
  `ROBOTS_DISALLOWED`, `CONTENT_TYPE`, `TOO_LARGE`, `TIME_LIMIT`, `PDF_LIMIT`, `PARSE_FAILED`,
  and is stored in `WebFetch.blockedReason`. What the remote side does (DNS failure, 4xx, 5xx,
  reset) is an `ExternalFailure`.

### The fetcher service (`app/fetcher/`, decision 0007)

`python -m app.fetcher` serves `create_app(SandboxFetcher.build())` on `FETCHER_HOST:FETCHER_PORT`
(`127.0.0.1:8090`). The API reaches it with `sources.fetcher_client.FetcherClient(FETCHER_URL,
client)`, which implements `Fetcher`.

| Request | Answer |
|---|---|
| `POST /fetch` (`FETCHER_PATH`), body a `FetchRequest` | 200 and a `FetchedPage`; 403 (`FETCHER_REFUSED_STATUS`) and `FetchRefusalBody {url, reason, detail}`; 502 (`FETCHER_FAILURE_STATUS`) and `FetchFailureBody {kind, message, retryable, status?, retryAfter?}`; 422 for a body off the contract |
| `GET /health` (`FETCHER_HEALTH_PATH`) | 200 `{"status": "ok"}` without fetching |

The client turns 403 back into `FetchRefused` and 502 into `ExternalFailure` with the same
fields; it waits the fetch's `timeoutSeconds` plus `FETCHER_MARGIN_SECONDS` (5); an unreachable
fetcher is `unavailable`, and any other answer, or a body that does not validate, is an
`ExternalFailure`, never a page. At most `FETCH_CONCURRENCY` (8) fetches run at once.

How the sandbox applies the rules:

- URL: `https` on port 443 only (`NOT_HTTPS`, `BAD_URL`); no credentials; at most 2048
  characters; international hosts in punycode; the fragment dropped.
- Address: the host is resolved by the fetcher; if any answer is not global unicast (private,
  loopback, link-local, CGNAT, ULA, documentation, benchmark, reserved, multicast, the cloud
  metadata addresses `169.254.169.254`, `169.254.170.2`, `100.100.100.200`, `fd00:ec2::254`,
  or an IPv4 address of those kinds inside a mapped, 6to4 or NAT64 IPv6 address) the fetch is
  `PRIVATE_ADDRESS`. It then connects to a vetted address (IPv4 first, next one on a connection
  failure) with `Host` and TLS SNI set to the original host, so the certificate is verified for
  that host (`TLS_MISMATCH` when it is not).
- Redirects: 301, 302, 303, 307, 308, at most `FETCH_MAX_REDIRECTS` (3), each target checked
  again before it is requested.
- robots.txt (RFC 9309), agent `KalaVigyan`: read for each host the fetch touches and cached for
  an hour; 4xx other than 429 allows all; 429, 5xx, an unreachable server or an unreadable file
  disallows all (`ROBOTS_DISALLOWED`) and is not cached.
- Size and time: one time limit for the whole fetch including robots and redirects
  (`TIME_LIMIT`); a declared or streamed body over `maxBytes` is `TOO_LARGE`.
- Content: `text/html` and `application/xhtml+xml` (reported as `text/html`), `application/pdf`
  and `text/plain`; anything else `CONTENT_TYPE`. HTML main text by trafilatura after scripts,
  styles, `noscript`, `template`, embeds and hidden elements are removed; metadata from the page
  head, its licence link and `<html lang>`. PDF text by pypdf from the first `PDF_MAX_PAGES`
  pages (`truncated` when more), `PDF_LIMIT` past `PDF_MAX_DECOMPRESSED_BYTES` of page content;
  encrypted, broken or text-less documents, and pages with no main text, are `PARSE_FAILED`.

### Retrieved text is untrusted (`research/untrusted.py`)

Retrieved text, search results and metadata are data, never instructions. Nothing fetched is
run. `clean_untrusted_text(text)` is applied to every text and metadata string the fetcher
returns: C0 and C1 controls, bidirectional embeddings, overrides and isolates, zero-width
space, invisible operators, the byte-order mark, interlinear annotation marks and the Unicode
tag block are removed; ZWJ and ZWNJ are kept (Indic spelling); runs of spaces and of blank
lines collapse. `untrusted_block(ref, label, text)` is how the composer puts any retrieved text
into a prompt: `<untrusted_source ref="..." label="...">`, the cleaned text, and the closing
tag, with any copy of the tag inside the text defused so the block cannot be closed from
inside. Retrieved text never goes into a system or tool message.

## Stored-knowledge retrieval (`research/retrieval.py`, decision 0008)

`KnowledgeRetriever.search(KnowledgeQuery) -> KnowledgeHits`: the T1 (claims) and T2 (corpus
chunks) tiers. `retrieval.hybrid.StoredKnowledgeSearch(session, embed=TextEmbedder)` implements
it; the answer flow passes `providers/embedding.router_embedder(principal)`.

- `KnowledgeQuery {craftSlug, text (1-1000), mode, facets[FacetType] (distinct), chunkAcls
  (distinct, default ["PUBLIC"]), limit (1-50, default 12)}`. The caller passes the ACLs the
  reader may see (`RESEARCHER` for researchers and above); nothing widens them. An unknown slug
  is `InvalidInput`.
- `KnowledgeHits {craftSlug, claims[ClaimHit], chunks[ChunkHit]}`, each at most `limit`, best
  first. `ClaimHit {claimId, text, level, subjectType (CONCEPT, EDGE), subjectId, score,
  lexicalRank?, vectorRank?}`; `ChunkHit {chunkId, sourceId, ordinal, locator?, text, score,
  lexicalRank?, vectorRank?}`. A rank is the 1-based place in that ranking, absent when the row
  was not in it.
- What each mode reads (`MODE_CLAIM_LEVELS`, `MODE_CLAIM_STATUSES`): `VERIFIED` reads
  `VERIFIED` and `REVIEWED` claims with status `APPROVED` and no chunks; `HYBRID` and `DEEP` read
  every level and every status except `HIDDEN_CLAIM_STATUSES` (`DRAFT`, `REJECTED`,
  `RETRACTED`), and chunks (the modes whose `MODE_POLICIES` tiers include `T2`).
- Scope, in SQL before any limit: claims on the craft's concepts and its sub-category's shared
  concepts, or on concept edges touching them; concept and claim `OPEN`
  (`VISIBLE_SENSITIVITY`), cited by at least one source that is not `RESTRICTED`. Chunks: of
  the sources those claims cite, within `chunkAcls`, chunk and source not `RESTRICTED`.
  `facets` keeps concepts of those types (and so the chunks of their sources).
- Ranking: full text (the question's distinct Latin words of 3+ characters, at most 40, ORed
  through `to_tsquery('english')`, ordered by `ts_rank_cd`, then id) and vector (cosine distance
  to the embedded question over the scoped rows, exact, then id), each the best
  `RANKING_DEPTH` (30). Fused by reciprocal rank fusion, `score = sum(1 / (RRF_K + rank))` with
  `RRF_K` 60; equal scores order by the best single rank, then id. A question with no Latin
  words is ranked by the vector alone.
- The question is embedded as `task: search result | query: <text>`; stored claims as
  `title: none | text: <text>` and chunks as `title: <source title> | text: <text>`
  (`retrieval/text.py`). An embedding failure is raised, never replaced by text-only results.
- Indexing (`retrieval/indexing.py`): `replace_source_chunks(session, source_id, text, *,
  lang="en", acl="PUBLIC")` chunks a source's text (`retrieval/chunking.chunk_text`: paragraphs
  packed up to 1,200 characters, long ones split at sentences, the last paragraph of a full chunk
  repeated when at most 300 characters, locator `para N` or `paras N-M`), keeps unchanged
  chunks' vectors, and gives chunks the source's sensitivity. `embed_pending(session, embed)`
  fills missing vectors of `OPEN`, non-hidden claims and of chunks whose chunk and source are
  not `RESTRICTED` (`python -m app.scripts.embed_knowledge`, run daily by the Coverage
  enrichment workflow before it enriches). `embed_written(session, embed, *, claim_ids,
  source_ids)` applies the same rules to the given claims and the chunks of the given sources
  only; the write-back uses it.

## Retrieval plan and planner (`research/planning.py`)

`Planner.plan(PlanRequest) -> RetrievalPlan`. The planner runs after a craft is resolved.

- `PlanRequest {question, mode, craft, language="en"}`.
- `RetrievalPlan {schemaVersion 1, mode, craft, intent, language, needsRegion,
  facets[Facet] (1-8), tiers[], queries[PlannedQuery], maxFetches}`; stored in `Answer.plan`.
  `intent` is one of `OVERVIEW`, `MATERIALS`, `PROCESS`, `SCIENCE`, `PLACE`, `HISTORY`,
  `COMPARISON`, `OTHER`. `Facet {type: FacetType, target}`.
  `PlannedQuery {tier: LiveTier, facetIndex, query: SearchQuery}`.
- Each mode's limits (`MODE_POLICIES`):

| Mode | Tiers | Live tiers run | Queries | Fetches |
|---|---|---|---|---|
| `VERIFIED` | T0, T1 | never | 0 | 0 |
| `HYBRID` | T0-T4 | only for facets the stored tiers left without a claim | 4 | 10 |
| `DEEP` | T0-T4 | always | 8 | 20 |

  A plan outside its mode's tiers, query or fetch limits, with tiers out of order or repeated,
  a query on a tier the plan does not run, or a query naming a missing facet, does not
  construct. Past 80% of the monthly ceiling the router degrades and the planner plans DEEP as
  HYBRID.
- `PlanRequest.withheldTerms` (at most 20, each 2-200 characters): words a search query must
  never carry, such as the asker's own names (PLAN 6, search egress).
- Coverage: `FacetCoverage {facetIndex, claimIds[]}` is `covered` when it holds at least
  `FACET_COVERED_MIN_CLAIMS` (2) claims. A claim covers a facet when a stored search for the
  facet's target, filtered to its concept type, ranks it by full text (`lexicalRank` set) and
  its level is in `COVERING_LEVELS[mode]` (the mode's `MODE_CLAIM_LEVELS` without
  `HYPOTHESIS`). `HYBRID` sends live queries only for uncovered facets; `DEEP` for every facet.

### Model calls (`research/structured.py`)

`StructuredModel(system=, user=, schema=) -> StructuredReply {text, degraded}`: one model call
that should answer one JSON object. `providers/structured.router_structured_model(task,
principal)` runs it through the AI router (`router.run` with `json_schema`), so the routes of
the Settings hub, the spend reservation and the monthly ceiling apply; `degraded` is the
router's own flag. `reply_object(reply)` reads the object (a Markdown code fence around it is
accepted) and raises `ExternalFailure` (service `model`) for anything else; the caller still
validates the object against its own model.

### The planner (`app/planner/`, decision 0009)

`planner.orchestrator.ResearchPlanner(model=, retriever=, sources=LiveSources)` implements
`Planner` and adds `research(PlanRequest, *, progress=None) -> EvidencePack`. `progress` is a
`stream.ResearchProgress` (`async (step, count)`), called with `SEARCHING_STORED` (facet count)
before the stored search, `RESEARCHING` (query count) before live search and `READING`
(evidence count) before reading when anything was found.

- **Draft**: one `PLAN` call with `plan_schema(max_queries)` (intent from `PLAN_INTENTS`, facet
  types from `CONCEPT_TYPES`, tiers from `LIVE_TIERS`); the question goes in an
  `untrusted_block`. An unusable reply is retried once (`PLAN_DRAFT_RETRIES`), then raised. A
  `degraded` reply turns `DEEP` into `HYBRID` (`DEGRADED_MODES`).
- **Plan**: coverage per facet (above), then queries: the first query of each open facet
  (the craft name and the facet target when the model gave none, on `T3`), then the model's
  others, in order; a query not naming the craft gets the craft name in front; queries with
  personal data or a withheld term are left out; duplicates (tier and case-folded text) are
  dropped; at most the mode's limit. `tiers` are the mode's stored tiers plus the live tiers
  the queries use; `maxFetches` is the mode's when there are queries, else 0.
- **Search**: each query on every searcher of its tier at once,
  `LIVE_BUDGETS[mode][tier].results_per_source` results each (`HYBRID` T3 5, T4 8; `DEEP` T3
  10, T4 15), at most `SEARCH_CONCURRENCY` (12) at a time, each within `SEARCH_TIMEOUT_SECONDS`
  (30). A failure is recorded; all failing raises `ExternalFailure` (service `live_research`,
  `unavailable`); a query tier with no searcher is `NotConfigured`.
- **Dedupe and rank**: hits merge by `source_key` and id into `PackedEvidence`; the kept item
  is the most trusted, then the one with quotes, then the best ranked. Order: trust, then hits
  (distinct searcher-and-query pairs), then best rank, then id.
- **Read**: the best item per facet first, then by rank, through the searcher that found it
  (`foundBy[0]`; `web` dispatches to SearXNG or Brave, which read through the fetcher), until
  `maxFetches` documents or `READ_ATTEMPT_FACTOR` (2) attempts per allowed document, at most
  `READ_CONCURRENCY` (8) at once, each within `DOCUMENT_TIMEOUT_SECONDS` (45). Where the tier's
  budget has `open_access` (`DEEP` T3), an item with a DOI and no quotes is first located with
  the `OpenAccessLocator`; an open copy (PDF, else landing page) is read through the `Fetcher`
  as `FULL_TEXT`, with the copy's own licence (none when the locator gives none, never the
  record's) and `externalIds.open_access_url` and `sha256`.
- **Follow references** (`DEEP`, with a `doi_source`): `DEEP_REFERENCE_RESERVE` (6) of the
  fetches wait while the primary items are read; then DOIs cited in documents whose tier
  `follows_references` (at most `REFERENCES_PER_DOCUMENT` 5 new per document, in text order)
  are fetched as `<doi_source>:<doi>` and opened like any scholarly item. They join the
  evidence after the searched items with `followedFrom` set and the parent's facets.

`LiveSources {searchers (distinct names), fetcher?, locator?, doi_source?}` (a dataclass);
`services.live_sources.live_sources(session, client)` builds it from every scholarly adapter,
the reference adapters and `WebSearch` (one `FetcherClient` shared by the web adapters and the
open-access reads), the Unpaywall locator and `crossref` as the DOI source. Hold it for the
process: each adapter paces and caches itself.

### Evidence pack (`research/evidence_pack.py`)

`EvidencePack {schemaVersion 1, plan, degraded, stored: KnowledgeHits, coverage[FacetCoverage],
evidence[PackedEvidence], documents[SourceDocument], failures[ResearchFailure]}`.

- `stored` is the question's stored search (limit `STORED_PACK_LIMIT` 20) for the plan's craft
  and mode; `coverage` lists every facet once, in facet order.
- `PackedEvidence {item, facetIndexes (at least one, each a plan facet), foundBy (searcher
  names), hits >= 1, bestRank >= 1, followedFrom?}`; ids and source keys are unique, and
  `followedFrom` names packed evidence.
- `documents` read packed evidence only, each once, at most `plan.maxFetches`.
- `ResearchFailure {stage (SEARCH, LOCATE, FETCH, FOLLOW), service, target (query text, id, DOI
  or URL), kind, reason?, message}`: `kind` is a failure kind or `refused`, and only a refusal
  carries its reason code (for example `ROBOTS_DISALLOWED`).

## Composer (`research/composition.py`)

`Composer.compose(ComposeRequest) -> ComposedAnswer`.

- `ComposeRequest {question, language, craft, candidates[ComposeCandidate] (unique ids, may be
  empty), searched: ResearchSummary (same craft)}`; `request.allowed` maps id to candidate.
- `ComposeCandidate {id, kind, text, quotes[], sourceLabel, level}`. `CLAIM`: `id` is the claim
  UUID, `text` the claim text, `quotes` its citation quotes. `EVIDENCE` (a live item not yet
  written back): `id` is `<adapter>:<id>`, `text` and `quotes` verbatim passages of the read
  document. `cited_texts` (`text` and `quotes`) is what a quoted span is checked against. The
  model sees each passage as data in a user-role message, never a reader's paraphrase, each
  wrapped by `untrusted.untrusted_block` with the candidate id as `ref`.
- `ResearchSummary {craft, mode, storedClaims, storedPassages, queries[SearchedQuery {tier,
  text}], services[], evidenceFound, documentsRead, failures}`: what was searched for the
  question. `not_enough_evidence_message(summary)` is the one user-facing sentence that lists
  it.
- `ComposedAnswer {sections[{heading (1-120), sentences[ComposedSentence] (at least one)}],
  openQuestions[ComposedSentence], followUps[] (at most 5), notEnoughEvidence?}`: either cited
  sentences (sections or open questions) or `notEnoughEvidence`, never both, never neither.
- `ComposedSentence {text (1-600), claimIds[uuid], evidenceIds[], spans[QuotedSpan]}`;
  `QuotedSpan {ref (a cited id), text (20-300)}` is the passage of that source the sentence
  rests on.
- Post-checks, `sentence_violations(sentence, allowed)`; any violation drops the sentence
  after `COMPOSE_RETRIES` (1) retry:
  - `UNCITED`: no claim or evidence id.
  - `UNKNOWN_ID`: an id outside the allowed set.
  - `UNQUOTED`: no quoted span. Every sentence quotes at least one passage of a cited source.
  - `UNSUPPORTED_FIGURE`: a number or chemical formula in the sentence that none of its own
    spans that passed the source check contains (`quotes.unsupported_figures`; formulas must
    match whole, digits inside a formula do not support a standalone number, `1,200` equals
    `1200`). A figure elsewhere in the cited source does not count.
  - `SPAN_NOT_CITED`, `SPAN_NOT_IN_SOURCE`: a span whose ref is not cited, or whose text is not
    in that candidate's text or quotes (`quotes.quote_occurs`).
  - `TRIVIAL_QUOTE`: a span shorter than 20 characters once folded (`quotes.trivial_quote`).
  - `UNRELATED_QUOTE`: the verified spans carry fewer than half of the sentence's content words
    (`quotes.quote_overlap`, `QUOTE_OVERLAP_MIN`).
- `sentence_level(sentence, allowed)` is the weakest level of the cited candidates, computed by
  the server, never by the model. Hypothesis-level sentences go to `openQuestions`.
- Reactions are not composer output: they come from stored `Reaction` rows checked by the
  science engine (coefficients never from a model).

### The composer (`app/composer/`, decision 0010)

`composer.composer.ModelComposer(model=StructuredModel)` implements `Composer`; the answer flow
passes `providers/structured.router_structured_model(AiTask.COMPOSE, principal)`, so the
`COMPOSE` routes apply (Claude Sonnet first; a missing key fails `auth` and the router moves to
Gemini).

- **Candidates**: `composer.candidates.compose_request(pack, question)`: every stored claim hit
  as `CLAIM` (its level, label `stored claim, <level>`), then every read document as `EVIDENCE`
  (level `PROVISIONAL`, `LABEL_LEVELS["QUOTED"]`): the whole text when at most
  `WHOLE_TEXT_MAX_CHARS` (4,000) characters, else its item's quotes; a long document without
  quotes, and evidence not read, are left out. Label `<title> (<publisher or adapter>, <year or
  undated>, <content>)`. `research_summary(pack)` fills `searched`; `services` are the searchers
  that returned evidence and the services that failed, sorted.
- **Call**: system `COMPOSE_SYSTEM_PROMPT` (rules only), user `compose_message(request)`
  (language, the craft name and slug in a block (`crafts.craft_block`), one block per passage,
  the question in a block), schema `compose_schema()` (each quote 20-300 characters):
  `{sections[{heading, sentences[{text, quotes[{source, quote}] (at least one)}]}] (at most 6),
  followUps[]}`. The cited ids of a sentence are its quotes' sources, in order, split into
  `claimIds` (allowed `CLAIM` candidates) and `evidenceIds` (anything else).
- **Unusable reply** (not a JSON object; `sections`, `sentences` or `followUps` missing or not a
  list; a heading empty, over 120 characters, or carrying a figure, a link, markup or personal
  data): asked again once, then `ExternalFailure` (service `model`). Follow-ups with a link,
  markup or personal data are dropped.
- **Regenerate**: when a usable reply has failing sentences (a violation, or a sentence that
  does not construct, `MALFORMED`) and no retry was spent, one call with
  `REGENERATE_SYSTEM_PROMPT`, `regenerate_message` (each failed sentence numbered, with its
  problems, its text inside a block) and `regenerate_schema(n)` (`sentences[{index, text,
  quotes}]`). A replacement takes the failed sentence's place if it passes; an omitted or
  failing one is dropped; an unusable reply drops them all. At most two model calls per answer.
- **Result**: passing sentences by section, hypothesis-level ones to `openQuestions`, empty
  sections dropped. No candidates: no call, `notEnoughEvidence`. Nothing passing:
  `notEnoughEvidence`.

## Write-back of live research (`research/write_back.py`)

`ClaimWriter.write(Sequence[ClaimWriteBack]) -> list[WriteBackResult {dedupeKey, claimId,
created}]`. What live research found becomes stored, cited claims so the next answer is
faster.

- `ClaimWriteBack {schemaVersion 1, craftSlug, subject, predicate, text, textLang="en",
  valueNum?, valueUnit?, label, levelReason, citations[WriteBackCitation] (at least one),
  foundBy, answerId?}`.
- `subject = WriteBackSubject {conceptId?, conceptType, conceptName}`: the writer attaches the
  claim to that craft's concept of that type and name, creating it when absent, so the stored
  answer path (`knowledge_view.claims_for`, which reads `retrieval/statements.claim_conditions`)
  finds it.
- `WriteBackCitation {evidence: EvidenceItem, quote: Quote?, quoteCheck, relation}`: the
  source row is found or created by `evidence.source_key` with `origin=LIVE_RESEARCH`; the
  quote must be one of `evidence.quotes` (already matched against the document); no quote
  means `quoteCheck=NA`, a quote means `PASS` or `FAIL`.
- Labels and stored levels (never inferred from model text): `QUOTED` needs at least one
  citation whose quote passed the check and is stored `PROVISIONAL`; `INFERRED` is a model or
  reader inference, stored `HYPOTHESIS`. Live research never stores a level above
  `PROVISIONAL`; only a professor or master admin `ReviewEvent` raises one.
- Every figure in `text` and `valueNum` must appear in a quote that passed; a unit needs a
  value. `foundBy` is `ANSWER` (with `answerId`) or `BACKGROUND` (the coverage job, no
  `answerId`).
- Stored as `Claim.origin=LIVE_RESEARCH`, `status=APPROVED` (`WRITE_BACK_ORIGIN`,
  `WRITE_BACK_STATUS`), `createdByKind=SYSTEM`, with one `ReviewEvent` (`actorKind=SYSTEM`,
  `systemActor=live_research`).
- `dedupeKey` is the SHA-256 of `claim-write-back/v1`, craft slug, concept type, folded concept
  name, predicate and folded text joined by U+001F (folded: quote-normalised, case-folded,
  trailing full stop dropped). A second write with the same key adds its new citations to the
  existing claim and answers `created=false`; it never creates a duplicate. Citations dedupe on
  (claim, source key, quote).

### The writer and the coverage job (decision 0011)

- `services/write_back_plan.write_back_plan(pack, answer, *, found_by, answer_id) ->
  WriteBackPlan {claims, skipped, sentence_keys}`: one write-back per composed sentence that
  cites a read document of the pack. `sentence_keys` has one entry per sentence in
  `composed_sentences(answer)` order (sections, then open questions; each with its heading,
  `None` for an open question): the dedupe key of the claim written for it, or `None`. Sections give `QUOTED` (relation `DIRECT`) when a span of the sentence
  is in the cited document's text, else `INFERRED`; open questions are `INFERRED` (relation
  `CONTEXTUAL`). The passing span is the citation quote and joins the item's quotes. Subject:
  the plan facet of the first cited evidence; predicate `WRITE_BACK_PREDICATE` (`states`).
  Sentences citing stored claims only, or breaking the contract, are `skipped` with a reason.
- `services/claim_writer.SqlClaimWriter(session)` implements `ClaimWriter`. Claim id
  `uuid5(ID_NAMESPACE, "claim-write-back:" + dedupeKey)`; citation id from claim, source key and
  `quote_key(quote)`; inserts never duplicate. The concept is the given `conceptId` (of the
  craft or its sub-category, same type, else `InvalidInput`), else the craft's
  `ProcessStage` of that name for `PROCESS_STAGE`, else the craft's (then the sub-category's)
  concept of that type and folded name, else a new craft concept. A quoted write raises a
  `HYPOTHESIS` claim to `PROVISIONAL` unless it is rejected or retracted, with a `ReviewEvent`.
- `ClaimSource` carries the provenance of each citation: `foundBy`, `answerId` (the question),
  `retrievedAt`, and `checkedAt` when a quote was checked; `chunkId` and `locator` point at the
  stored chunk holding the quote.
- `services/live_source_store.keep_document(session, document) -> source id` stores a read
  document before its claims: source found by derived id, DOI or URL, else created with
  `origin=LIVE_RESEARCH`; its text chunked (`replace_source_chunks`) unless an imported
  source already has chunks or richer live text is stored. `chunk_acl`: abstracts and excerpts
  are `PUBLIC`; full text is `PUBLIC` only when `research/licences.open_licence` accepts the
  item's licence (CC0, CC BY, CC BY-SA, PDDL, public domain, by name or canonical URL) and the
  item is not a T4 page declaring its own licence; else `RESEARCHER` (decision 0013).
- `services/research_write_back.store_live_research(session, pack, answer, *, embed, found_by,
  answer_id=None) -> StoredResearch {source_ids, results, skipped, embedded, sentence_keys,
  embedding_error}` keeps the documents, writes the claims, commits, then embeds only the claims
  and chunks it wrote (`embed_written`). An embedding failure after the commit is logged and
  kept in `embedding_error` (`embedded` zero); the rows wait for `embed_knowledge`.
  `sentence_claim_ids(answer, stored)` gives each composed sentence its stored claim ids, then
  the claim written for it (`stored` None: stored claims only); keys that do not match the
  answer's sentences are `InvalidInput`.
- The coverage job (`python -m app.scripts.enrich_coverage`, daily by
  `.github/workflows/coverage-enrichment.yml`): `services/coverage_selection.least_covered_crafts`
  picks active, non-catch-all crafts of every source without a job in the last 7 days, fewest
  visible claims first; `STANDARD_QUESTIONS` (one per facet) run while the facet has fewer than
  `FACET_COVERED_MIN_CLAIMS` claims, as `HYBRID` planner, composer and `BACKGROUND` write-back.
  `ENRICHMENT_DAILY_BUDGET_USD` (2.50) bounds the day, measured from `UsageEvent` rows tagged
  with the request id `enrichment-<job id>` (`providers/router.tagged_spend`); each craft gets an
  `EnrichmentJob` row. The report is one JSON object; any failed craft exits 1.

## Answer stream (`research/stream.py`)

`POST /api/answers/stream` answers `text/event-stream`. Each frame is `event: <name>`, one
compact JSON `data:` line and a blank line (`sse_frame`); `event_frame(name, payload)` validates
the payload against the event's model first and raises `InvalidInput` when it breaks the
contract, so an uncited sentence can never reach the wire. Payloads are dumped with only the
fields that were set.

| Event | Payload | Notes |
|---|---|---|
| `match` | `{status:"RESOLVED", craft}` / `{status:"AMBIGUOUS", candidates (1-5)}` / `{status:"NONE"}` | first; AMBIGUOUS is followed only by `done` |
| `status` | `{step, message}` | new; progress while research runs. `step` one of `RESOLVING`, `PLANNING`, `SEARCHING_STORED`, `RESEARCHING`, `READING`, `COMPOSING`, `WRITING_BACK`; `message` a short user-facing sentence |
| `source` | `SourceRef {id, kind, title, authors[], year, doi, url, publisher, licence, attribution, reliability}` | before the first citation naming it; `url` https or null |
| `section` | `{id, heading}` | |
| `sentence` | `{sectionId, sentence: AnswerSentence}` | |
| `open_question` | `{sectionId, heading?, sentence}` | hypothesis-level sentences |
| `reaction` | `{id, label, equation, balanced, level, conditions, citations (at least one)}` | |
| `follow_ups` | `{items[]}` | |
| `not_enough_evidence` | `{message}` | new; nothing cited could be shown. `message` is `not_enough_evidence_message` (what was searched); followed only by `done` |
| `done` | `{answerId}` | last |
| `error` | `{message}` | shown verbatim; never internal detail |

`AnswerSentence {id, text, level, citations (at least one), translated?}`;
`Citation {id, claimId, sourceId, quote (at most 300) | null, locator, context, evidence
(QUOTED or INFERRED), level}`. Levels are `ShownLevel`.

Heartbeat: while no event has been sent for `HEARTBEAT_SECONDS` (60), the server sends the SSE
comment `HEARTBEAT_FRAME` (`: keep-alive` and a blank line). `event_stream(produce, *,
heartbeat_seconds=HEARTBEAT_SECONDS)` is the one implementation: it runs `produce(emit)` as a
task, `emit(name, payload)` validates through `event_frame` and queues the frame, and the
response reads the queue and sends the heartbeat on each silent interval; closing the response
cancels the producer, and a producer failure is raised after the frames sent before it. It is under CloudFront's
`origin_read_timeout` (120 s) and nginx's `proxy_read_timeout` (300 s); a test reads both from
`infra/terraform` and fails if either drops to 60 s or less.

Compatibility: the web client (`frontend/lib/answerStream.ts`) ignores comment lines and event
names it does not know; it shows `status` as the progress line and `not_enough_evidence` as the
empty state. Shared fixtures, each parsed and reduced by `e2e/answer-stream-golden-unit.spec.ts`:
`shared/answer-stream.golden.sse` (every event kind; the backend validates each event against
these models), `shared/answer-stream.research.golden.sse` and
`shared/answer-stream.not-enough.golden.sse` (written by hand; the backend answering flow must
produce them byte for byte, `tests/answering/test_answer_flow.py`). Change the fixtures, the
models and the client together.

### The answering service (`services/answering.py`, decision 0012)

`answer_question(AnswerAsk, AnswerPipeline, emit)`; `AnswerAsk {question, mode, craft_slug?,
language?, user_id?, withheld_terms}`; `AnswerPipeline {resolve, research(PlanRequest,
ResearchProgress), compose(ComposeRequest), store: AnswerStore}`; `AnswerStore {stored_claims
(slug, question, mode), keep(ask, pack, answer) -> KeptAnswer {answer_id, claims_of},
cited(claim_ids)}`, the reads returning `answer_events.CitedClaims {views, sources}`.
`answer_store.build_answer_pipeline(sessions=, index=, live=, plan_model=, compose_model=,
embed=)` wires the database resolver, `ResearchPlanner` over `retrieval.hybrid.
SessionScopedSearch` and the process-held `live_sources.LiveSourcesStore` (rebuilt every
`LIVE_SOURCES_TTL_SECONDS` 600 on one HTTP client), `ModelComposer` and `SqlAnswerStore`. No
database session is held across a model call or the stream: each step opens its own.

1. `status RESOLVING`, resolve. A resolver failure is `error` (`RESOLVER_FAILED_DETAIL`, or
   the router's own words for a spend-cap refusal); a
   given slug that does not resolve is `error` (`NOT_FOUND_DETAIL`) with no `match`; otherwise
   `match`; `AMBIGUOUS` stops; `NONE` is `error` (`NO_CRAFT_DETAIL`).
2. `VERIFIED`: `status SEARCHING_STORED`, the craft's `VERIFIED` and `REVIEWED` `APPROVED`
   claims (`retrieval/statements.claim_conditions`, the scope T1 also reads) ranked by any
   word of the question (`ts_rank_cd` over the OR query), at most 14
   findings by concept section and 4 hypotheses; no model call; `answerId` null.
3. `HYBRID`, `DEEP`: `status PLANNING`, `research` (which reports its own steps), `status
   COMPOSING` (candidate count, when there are candidates), compose, `status WRITING_BACK`
   (document count, when documents were read), `keep` (an `Answer` row, then
   `store_live_research` with `found_by=ANSWER` and its id), then the citations of every claim
   the sentences rest on (`knowledge_view.claims_by_id`). Each sentence keeps the visible
   citations of its claims in order; one without any is dropped; its level is the weakest of
   its claims' stored levels; a `HYPOTHESIS` sentence is an `open_question` (section `open`,
   heading `Open questions`). Section ids `s1`, `s2`, ... in heading order; sentence ids
   `<section>.<n>`. A `source` event precedes the first sentence citing it; `follow_ups` are
   the composer's.
4. Nothing shown: `not_enough_evidence` with the composer's summary, or the pack's.
5. Any `AppError` after the match is one `error`: a router `ceiling` refusal in its own words,
   anything else `RESEARCH_FAILED_DETAIL`; any other exception is logged and `UNEXPECTED_DETAIL`.
   `done {answerId}` always ends the stream.

Status messages (`status_message(step, count, craft)`): `Finding the craft`, `Planning the
research on <craft>`, `Searching stored findings`, `Searching <n> live queries`, `Reading the
best of <n> sources found`, `Writing a cited answer from <n> passages`, `Saving <n> sources for
the next question` (singular for one).

Route (`api/routes/knowledge.py`): `VERIFIED` and `HYBRID` need `ASK_STANDARD`, `DEEP` needs
`ASK_DEEP` (403 with `refusal_for`, before any work; an unknown role has neither); then the ask
window (429). Model calls run as the asker's `Principal`, so the per-role daily cap and the
monthly ceiling apply. The asker's name is a withheld search term. `/answers/config` lists the
modes the asker may use, default `HYBRID`.

## Not built yet

The craft resolver, the scholarly adapters, the reference adapters (Wikipedia, Wikidata,
PubChem, Wikimedia Commons), the SearXNG and Brave adapters, the fetcher service,
stored-knowledge retrieval (T1, T2), the planner with tiered live research, the composer with
its retry loop, the claim writer and the coverage job are built (above). So are the answering
service, the streamed events with the heartbeat, and the client's handling of `status` and
`not_enough_evidence` (decision 0012). Still to build against these types: the T0 craft profile
tier and the reader that takes verbatim quotes from the pack's documents (`WEB_READ`).
