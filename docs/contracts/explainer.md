# Explainer contract

An answer becomes an explainer: ordered sections, each holding typed blocks, streamed as they
are ready and stored as knowledge pieces for later answers (`docs/plans/answer-experience.md`
sections 2.1 to 2.4, 2.7 and 2.8). The code is the typed models in `backend/app/research/`
(`explainer.py`, `blocks.py`, `blocks_place.py`, `blocks_matter.py`, `blocks_people.py`,
`terms.py`, `media_refs.py`, `subject_keys.py`, `knowledge_pieces.py`, `depth.py`,
`citations.py`) and the client types and runtime shapes in `frontend/lib/explainerContract.ts`
and `frontend/lib/explainerStream.ts`. Change a type only together with this page, the fixtures
and both sides' tests. Design choices: decision 0030.

Last reviewed: 2026-11-17.

## Ground rules

- Every fact carries a citation to a source or a dataset row. A block that cites nothing does not
  construct; a section that shows nothing ends `EMPTY` and says what it searched.
- Numbers, coordinates, districts and river paths come from claims or datasets, never from a
  model: a model chooses and orders, the server fills values. A ladder condition's `stated` text
  must occur in one of its citations' quotes.
- Sentences keep today's contract (`research/citations.AnswerSentence`: verbatim quotes,
  citations, levels computed by the server, the composer's figure checks). Facts only: a
  hypothesis is never a prose, ladder or term sentence; it is an open question.
- A block kind that is not built yet is refused wherever a reader would see it: the `block`
  event, the stored explainer, a stored piece and the client's parser (`BUILT_BLOCK_KINDS`).
- Shapes follow `docs/contracts/research.md`: `ContractModel`, camelCase JSON, unknown fields
  refused, https URLs only, instants with a time zone.

## The document (`Explainer`)

`Explainer {schemaVersion 1, answerId, question, understood, sections[ExplainerSection] (at
least one), sources[SourceRef], followUps[] (at most 5), createdAt}`.

A finished explainer is kept on its `Answer` row under `payload.explainer`
(`services/answer_store.EXPLAINER_PAYLOAD_KEY`): this document's JSON, in the answer language, as
the reader saw it. Listen reads it from there (decision 0035) and refuses one whose `answerId` is
another answer's; a `payload` without it (a voice turn's) holds no explainer.

- `understood` is the `Understood` shape of the stream event below.
- Sections are listed by `order`, 1 to n; ids are `s1`, `s2`, ... and unique. Order is the
  reading order and adapts to the question; section ids are only names.
- Block ids (`^[a-z0-9]+(?:[.-][a-z0-9]+)*$`, at most 80, for example `s1.b2`) are unique across
  the explainer.
- `sources` lists every source the blocks cite, once, in order of first citation walking the
  sections in order (`cited_source_ids`).
- At least one section is `READY`.

`ExplainerSection {id, discipline, title (1-120), original?, order >= 1, state, blocks[Block],
searched}`. Stored sections are `READY` (at least one block, `searched` null) or `EMPTY` (no
blocks, `searched` the one sentence of what was searched). `original` is the English title when
`title` is a translation. An image block may illustrate only claims another block of the same
section cites. Disciplines (`models/enums.DISCIPLINES`): `OVERVIEW`, `PROCESS`, `CHEMISTRY`,
`PHYSICS`, `MATERIALS`, `GEOGRAPHY` (geography and water), `GEOLOGY` (geology and soil),
`CLIMATE`, `ECOLOGY`, `BOTANY`, `HISTORY`, `ECONOMICS`, `DESIGN`, `HEALTH`.

## The block envelope

Every block is `{id, kind, version, reuse, ...fields}`; `kind` discriminates the union `Block`,
`version` is a literal per kind (all 1 today; a new version is a new model, never a reinterpreted
old one), `reuse` is null or `ReuseMarker {pieceId, storedAt}` when the block came from a stored
piece ("From earlier research" and its date). Each block says what it rests on:
`cited_claim_ids()`, `cited_source_ids()` (citation sources, then sources cited directly), and
`illustrated_claim_ids()` for images. Sentences in blocks are `ExplainerSentence`, today's
`AnswerSentence` plus `terms[TermSpan]`.

| Kind | Phase | Built |
|---|---|---|
| `prose`, `process_ladder`, `images` | A | yes |
| `region_story`, `map_layer`, `reaction_player`, `material_card`, `molecule_3d`, `expert_view`, `seasons`, `supply_map` | B | declared |
| `simulation`, `what_if`, `zoom_story`, `timeline_map` | C | declared |
| `quiz`, `compare`, `in_practice`, `open_questions` | D | declared |
| `artisan_voice` | E | declared |
| `designs` | deferred (owner, 2026-11-17) | declared |

A phase builds a kind by adding it to `BUILT_BLOCK_KINDS` (server and client, pinned by
`e2e/backend-vocabulary-unit.spec.ts`) and its client shape and renderer; the envelope does not
change.

### Built in phase A

- **`prose`** `{sentences[ExplainerSentence] (at least one)}`. Sentence ids unique in the block;
  levels `VERIFIED`, `REVIEWED` or `PROVISIONAL` only (`FACT_LEVELS`).
- **`process_ladder`** `{craft: CraftRef, processId, stages[LadderStage] (at least one)}`, stages
  by rising `ordinal`. `LadderStage {stageId, ordinal, name, stageType, level, sentences
  (at least one), materials[LadderMaterial], conditions[LadderCondition], reactionIds[]}`: the
  stage's level is the weakest of its sentences; `reactionIds` link the stage to the science
  engine's reactions on the craft page's Process tab (each once). `LadderMaterial {materialId,
  name, kind, role, citations (at least one)}`. `LadderCondition {label, stated, citations (at
  least one)}`: `stated` is the source's own words (`ten to fifteen days`), found by
  `quotes.quote_occurs` in one citation's quote. Ids are the stored `ProcessStage`, `Material`
  and `Reaction` rows of `docs/contracts/science.md`.
- **`images`** `{items[ImageItem] (1-8)}`, each media once. `ImageItem {media: MediaRef, claimIds
  (at least one, once each), relevance: TEXT | VISION}`: the claims the image illustrates and
  how its relevance was checked (claim text, or a vision call for top candidates).

### Declared for later phases

Fields are fixed now so the phases fill them without changing the envelope. `ExplainerSentence`
is written "sentence" below; every sentence is cited.

| Kind | Fields | Rules |
|---|---|---|
| `region_story` | `river {name?, datasetCode, reachIds[] (source to mouth, once each)}?`, `districts[{districtLgd, name, stateName}]`, `steps[{districtLgd?, sentence}]`, `layers[]` (map layer ids), `boundaryCaption` | steps narrate listed districts only; the caption is the region contract's `BOUNDARY_CAPTION` |
| `map_layer` | `layer`, `layerVersion`, `basis`, `datasetCodes[]` (at least one), `highlighted[]` (district LGD codes), `boundaryCaption` | cites datasets, not claims; values come from the map layer route |
| `reaction_player` | `steps[{reactionId, label, equation?, balanced, level, citations}]` | equations from the science engine only |
| `material_card` | `materialId?`, `name`, `formula?`, `pubchemCid?`, `wikidataId?`, `localNames[]`, `role?`, `facts[sentence]` (at least one), `handling[sentence]` | |
| `molecule_3d` | `pubchemCid`, `name`, `formula?`, `sourceId` (the PubChem record) | cites its compound record |
| `simulation` | `concept`, `title`, `model`, `createdAt`, `html`, `htmlSha256`, `values[{key, value, unit?, citations}]`, `hidden` | at most 200 KiB; each value once and cited (plan 2.6 adds the static check) |
| `what_if` | `changed`, `options[{label, outcome: sentence or null}]` (at least two) | an option without evidence has no outcome and is shown as unknown |
| `timeline_map` | `points[{label, yearFrom, yearTo, wikidataId, latitude, longitude, sentence}]`, `routes[{start, end, sentence}]` | coordinates from Wikidata; routes join two different listed points |
| `zoom_story` | `levels[{level, media?, districtLgd?, pubchemCid?, sentence}]` (at least two) | levels `DISTRICT`, `WORKSHOP`, `CLOTH`, `FIBRE`, `MOLECULE` in order, each once; a level is shown only with its district, licensed image or compound |
| `expert_view` | `seat`, `take[sentence]`, `agreesWith[seat]`, `differs[{seat, thisView, otherView}]` | seats from `EXPERT_SEATS` (plan 4.6); never its own seat |
| `seasons` | `rows[{stageId?, label, months[1-12], sentence}]`, `rainfall {districtLgd, datasetCode, period, millimetres[12]}?` | months once each, in order |
| `supply_map` | `links[{material, materialId?, origin, wikidataId?, latitude?, longitude?, sentence}]` | an origin is placed only with Wikidata coordinates |
| `compare` | `crafts[2]`, `rows[{aspect, left?, right?}]`, `pieceIds[]` | two different crafts |
| `in_practice` | `notes[{audience, sentences}]` | one note per audience (`AUDIENCES`) |
| `quiz` | `questions[{prompt, options (2-5, distinct), answer, explanation: sentence}]` (1-10) | the key is one of the options |
| `open_questions` | `items[{sentence, howToFindOut?}]` | a hypothesis; the way to find out carries no figures |
| `artisan_voice` | `quotes[{artisan {name, credentials[], village?, district?, state?, address?}, quote, language, sourceId, locator}]` | artisans quoted by name with their credentials and place (owner O4); no phone number, email address or identity number anywhere (`personal_data_in`) |
| `designs` | `designs[{id, title, workshop?, madeOn?, url, image?, sourceId}]` | deferred until the workshops hold designs |

## Terms and images

- **`TermSpan {text (1-120), termKey}`** marks a term in a sentence: `text` is found in the shown
  text (the first occurrence is underlined), each term once per sentence, spans never overlap.
  In a translated sentence the spans mark the translated text: the server keeps a span of the
  English sentence only where its `text` still occurs in the translation and that first
  occurrence overlaps no span kept before it (`research/terms.spans_still_shown`), and marks
  nothing anew (decision 0039).
- **`Term {schemaVersion 1, key, label, language, localNames[], craftSlugs[], wikidataId?, basis,
  summary[AnswerSentence] (1-3), sources[SourceRef], checkedAt}`** is the glossary row a tap
  opens, cached per key and language. `basis` is `STORED` (cited claims already held), else
  `WIKIPEDIA`, else `WEB_SEARCH`; the summary states facts only, and `sources` lists the cited
  ones in order of first citation. Local names and crafts are listed once each.
- **`MediaRef {id, display, provider, pageUrl, imageUrl, width?, height?, title, alt, author?,
  site, credit?, licence?, licenceUrl?, sourceId?, retrievedAt}`** is one stored picture.
  `INLINE` needs an open licence (`licences.open_licence` of the licence or its URL) and the
  author; anything else is a `LINK_CARD` with the source site's thumbnail as `imageUrl`, its
  `site` and `credit`, opening `pageUrl` (owner O2). `width` and `height` (the image's pixels)
  come together or not at all; `sourceId` names the stored source when the page is one.

### Pictures and terms as served (decision 0034)

- **Image sources.** Wikimedia Commons, Openverse (open licences with a creator only) and SearXNG
  image results, each an `ImageSource` (`research/images`). A SearXNG picture is kept only when
  the page's own site serves it (`same_site`: the page and `img_src` share a registrable name),
  never a search engine's thumbnail, never over http; it has no licence, so it is a link card.
- **Choosing.** A picture illustrates the claims (cited by the section's other blocks) whose
  content stems it shares at least two of, craft-name words left out (`image_relevance`); a
  section shows at most 4, inline first, at most 2 link cards, each original image once; no
  relevant picture is no `images` block. Each picture is stored once as a `MediaRef` row with its
  `MediaRefClaim` links.
- **Drawing.** Every picture loads with `referrerPolicy="no-referrer"`; a link card shows
  `imageUrl`, `title`, `site` and `credit` and opens `pageUrl`; an inline picture shows `alt`,
  `author`, `licence` (linked to `licenceUrl`) and `site`, and opens `pageUrl`. A picture that
  fails to load is not drawn. The site-wide CSP's `img-src` is the app, `data:`, the
  media bucket and `https:` (`IMAGE_SOURCES` in `frontend/next.config.ts`, decision 0039), so a
  move to `/ask` inside the app still shows pictures; no page allows plain http.
- **Glossary.** `Term` rows (seeded by `seed_claims`) hold the label, local names, the Latin
  spellings used to find the term, the matched Wikidata id and the crafts and concepts it belongs
  to. Spans are marked by the server (`research/term_marking.TermMarker`), never chosen by a model.
- **In the stream** (decision 0039, `services/section_enrichment`). Once per answer the craft's
  glossary (`glossary_entries`, the craft's own names left out) becomes one `TermMarker`; an
  answer for any craft reads none and marks nothing, and a glossary that cannot be read leaves
  the answer unmarked. Every English sentence of a section's `prose` and `process_ladder` blocks
  is marked before translation, and stored pieces keep the marked blocks. While those blocks are
  sent, the section's pictures are searched from the claims they cite (in order of first
  citation); the `images` block follows them as one more `block` (`<section>.b<n+1>`), before the
  open questions and `section_done`. Each image service has 6 s (`IMAGE_SEARCH_SECONDS`), the
  whole step 8 s (`PICTURES_WAIT_SECONDS`); a failure, a timeout or no relevant picture sends no
  `images` block and the section is still `READY`. Reused sections get pictures the same way from
  their placed blocks' claims. An `images` block is never stored as a piece.
- **`GET /api/terms/{key}?language=`** (signed in; 60 in 10 minutes, Master Admin unlimited)
  answers a `Term`: the cached summary while every claim it cites is visible, else `STORED`
  (each concept's defining claim), else `WIKIPEDIA` (verbatim lead sentences of the article for
  the term's Wikidata item or one of its names), else `WEB_SEARCH` (one search, up to 2 pages
  read, one `SUMMARISE` call whose sentences quote the pages). What was found is stored as quoted
  claims first, so every sentence cites stored claims. `language` is an answer language (default
  `en`); other languages translate the English summary sentence by sentence (a sentence that fails
  stays English). 404 for an unknown key or no cited summary; the client then shows no underline
  popover. 422 for an unknown language.

## Stream events (`research/stream.py`)

The explainer stream is the answer stream (`docs/contracts/research.md`) with six more events,
validated by `event_frame` like every other: a payload off the contract never reaches the wire.

| Event | Payload | Notes |
|---|---|---|
| `understood` | `Understood {crafts[CraftRef] (0-5), candidates[CraftRef] (0-5), depth, language}` | first. `crafts` empty is "Any craft"; several crafts is a comparison; `candidates` are the others offered, one tap to change. Each craft appears once across both lists |
| `trail` | `{key, stage, group, title, url?, publisher?, year?, sourceId?, storedAt?}` | a source found, read or quoted. `key` is the evidence id (`openalex:W...`), `source:<uuid>` for stored sources or `piece:<uuid>` for a reused piece; stored keys are group `STORED` and never `READ`; a piece carries `storedAt`; a stored source names `sourceId`. Groups: `PAPERS`, `ENCYCLOPAEDIA`, `DATASETS`, `WEB`, `STORED` (`TRAIL_GROUP_OF_SOURCE` maps every source type). A key's stage only moves forward: `FOUND`, `READ`, `QUOTED` |
| `section_started` | `{id, discipline, title, original?, order, state}` | `state` `RESEARCHING`, `WRITING` or `CHECKING` |
| `section_state` | `{sectionId, state}` | a later working state of a started section |
| `block` | `{sectionId, block}` | a built block only; every source it cites was sent as `source` first |
| `section_done` | `{sectionId, state, searched}` | `READY`, or `EMPTY` with what was searched |

Order: `understood`; reused pieces stream first (their `trail` with `storedAt`, `section_started`,
`block`, `section_done`); every researched section is then started (`RESEARCHING`) and the
sections run in parallel, so events of different sections interleave and `order` places them
(within a section: its trail, `WRITING`, `CHECKING`, sources and blocks, open questions,
`section_done`, then `trail` `QUOTED` for what it quoted; a section researching again goes back
to `RESEARCHING`); `follow_ups` or `not_enough_evidence`; `done {answerId}` last. A section's
`images` block, when it has one, is its last block. The researched
and stored answers no longer send `section` or `sentence` (decision 0032). The heartbeat stays: an
SSE comment after 60 s of silence (`HEARTBEAT_SECONDS`).

How today's events map:

| Today | In the explainer stream |
|---|---|
| `match` | `understood`: `RESOLVED` is `crafts=[craft]`; `AMBIGUOUS` no longer stops (the best candidate proceeds, the rest are `candidates`); `NONE` is `crafts=[]` (any craft) |
| `status` | kept for the one progress line; steps unchanged |
| `source` | kept; sent before the first block citing it |
| `section` | `section_started` |
| `sentence` | a sentence inside a `prose` or `process_ladder` block |
| `open_question` | kept until `open_questions` is built (phase D) |
| `reaction` | kept until `reaction_player` is built (phase B) |
| `follow_ups`, `not_enough_evidence`, `done`, `error` | kept |

## Depth by role (`research/depth.py`)

| Depth | Label | Research mode | Queries, documents | Sections | Experts | Default for |
|---|---|---|---|---|---|---|
| `BASIC` | Basic | `HYBRID` (stored first, light) | 2, 5 | 3-4 | 2 | Student |
| `DETAILED` | Detailed | `HYBRID` | 4, 10 | 5-7 | 4 | Researcher, Professor |
| `EXPERT` | Expert | `DEEP` | 8, 20 | all relevant (1-14) | 6-10 | Admin, Master Admin |

- `VERIFIED`, `HYBRID` and `DEEP` stay internal (`ANSWER_MODES`, `MODE_POLICIES`). `VERIFIED` is
  the stored-only answer that still works when spend is refused.
- Every known role may choose every depth (`selectable_depths`); an unknown role none.
- The ask screen draws `/answers/config`'s `depths` and starts at its `defaultDepth`, and sends
  the reader's choice as `depth` (null before the config is read: the role's default); it never
  sends `mode` (decision 0036).
- A depth researches within its mode: `research_budget(mode, depth)` is the smaller of the
  depth's and the mode's query and document limits, so a degraded Expert answer keeps Hybrid's.
- `core/roles.UNCAPPED_ROLES` is `MASTER_ADMIN` only: no per-answer cap, no daily cap, and the
  monthly ceiling never refuses or degrades their answers, and the ask, term and Listen
  throttles skip them (`is_uncapped`, decision 0038); their spend still shows on Usage. For
  every other role, past the degrade mark (80 % of the monthly ceiling) `EXPERT` becomes
  `DETAILED` (`effective_depth`, applied by the understanding step), and each answer is held to
  its depth's cap in the AI budget (`AI_ANSWER_CAP_USD`, `answerCapUsd` on `/settings/ai-budget`;
  decision 0031).
- The understanding step (`docs/contracts/research.md`, decision 0031) sends `understood` and
  keeps the fields the question touches and the expert seats on `Answer.understanding`.

## Stored pieces (`research/knowledge_pieces.py`)

`KnowledgePiece {schemaVersion 1, id, craftId?, kind, facet, topicKey, language, depth,
payload: Block, claimIds[] (sorted), sourceIds[] (sorted), contentHash, createdFromAnswerId?,
createdAt, staleSince?, supersededById?}` is one finished block kept for reuse. The table also
holds `embedding` (1536 dimensions, filled like claims, never sent).

- `craftId` is null for a cross-craft piece (a district's water story). `facet` is a
  discipline. `language` is always `en`; translations are cached apart, as today.
- The payload is stored as built: no reuse mark, a built kind, and `claimIds` and `sourceIds`
  exactly what it cites. `contentHash` is the SHA-256 of the payload's JSON without its placement
  fields (`id`, `reuse`), keys sorted, compact separators, UTF-8.
- Reusing places the payload in the new explainer: a new block `id` and `reuse {pieceId,
  storedAt = createdAt}`; everything else is unchanged.
- **Topic keys** (`subject_keys.topic_key(namespace, *subjects)`): `<namespace>:<subjects>`,
  namespace one of `TOPIC_NAMESPACES` (`craft`, `process`, `stage`, `material`, `reaction`,
  `compound`, `water`, `soil`, `climate`, `region`, `history`, `design`, `economy`, `health`,
  `ecology`, `concept`); each subject NFKD-decomposed, marks dropped, case-folded, every run of
  anything but `a-z0-9` one hyphen, ends trimmed; subjects deduplicated, sorted and joined by
  `+` (`water:kachchh`, `reaction:alizarin+alum`). A subject with no Latin letter or digit is
  refused. `term_key(label)` is the same slug without a namespace (`iron-acetate`).
- **Reuse rule** (`reuse_refusal(piece, ask, visible_claim_ids)`): a piece is reused for
  `ReuseAsk {craftId, facet, topicKey, depth}` when craft, facet and topic match, its depth is at
  least the asked depth, it is not stale or superseded, and every claim it rests on is still
  visible; otherwise the first failing reason (`CRAFT`, `FACET`, `TOPIC`, `DEPTH`, `STALE`,
  `SUPERSEDED`, `CLAIM_NOT_VISIBLE`). Research runs only for facets with no reusable piece, or
  when the reader asks for fresh research.
- **Staleness**: when a claim is retracted, hidden, changes level or changes text
  (`PIECE_STALE_CHANGES`), every piece that `rests_on` it gets `staleSince`; the next answer that
  would reuse it rebuilds the block instead, and the nightly job rebuilds stale pieces of the
  most-asked crafts.

### Stored pieces as served (decision 0033)

- **Table.** `KnowledgePiece` (migration `0015_knowledge_pieces`): the fields above, `claimIds`
  `uuid[]` (GIN), `sourceIds` `text[]`, both non-empty, `embedding` (1536). The trigger
  `kv_stale_resting_pieces` on `Claim` sets `staleSince` when a claim's status moves into `DRAFT`,
  `REJECTED` or `RETRACTED`, or its level, text or sensitivity changes, or it is deleted.
- **Topic keys** (`research/piece_topics`): the facet's namespace (`FACET_NAMESPACES`) and as
  subjects the glossary terms the question names (`TermMarker` over the craft's glossary), else for
  `GEOGRAPHY`, `GEOLOGY` and `CLIMATE` the craft's districts, else the craft's slug. A key longer
  than `TOPIC_KEY_MAX_CHARS` is no key: that facet neither reuses nor stores.
- **Storing** (`services/piece_store.SqlPieceStore.keep`, shielded): every English block of a
  researched section that cites claims and sources (`prose`, `process_ladder`; an `images` block
  rests on illustrated claims and is not a piece), id `uuid5("knowledge-piece:<answer>:<block>")`,
  sentence ids renumbered `p<first 12 hex of the piece id>.<n>` in reading order, then embedded
  (a failure is logged; `embed_knowledge` fills it). It supersedes every earlier current piece of
  the same craft, facet, topic and kind at the same or a lower depth. Storing writes no process
  rows: stage concepts a `PROCESS` section's prose cites stay concepts (decision 0038).
- **Reusing** (`reusable`): for a craft (any-craft answers reuse nothing), unless `fresh`, the
  pieces of that craft with the asked facets and topics; a set is the pieces one answer stored for
  one facet, placed `process_ladder`, `prose`, `images`, and it is reused only when every piece
  passes `reuse_refusal` with the claims visible as cited (`piece_reuse.visible_as_cited`: visible
  now, every shown citation still stored, at the shown level) and every ladder passes
  `science/ladder.ladder_problems` against the craft's process rows. Among several sets, the one
  whose piece is nearest the question's embedding (`task: search result | query:`), else the newest.
- **Streaming**: reused sections first, each `trail FOUND` per piece (`piece:<id>`, the shown
  section title, `storedAt`), `section_started WRITING`, sources, the placed blocks (block ids
  `<section>.b<n>`, translated like any block), its `images` block when pictures are found (no
  reuse mark: the pictures are searched for this answer), `section_done READY`; then the open
  sections. An answer made only of reused sections offers `answer_events.stored_follow_ups` for
  the headings of its pieces' claims (decision 0039).

## Listen (read by the explainer UI, decision 0037)

The explainer UI reads Listen as below (`frontend/lib/listen.ts`); the route that serves it is
Listen's lane (0035). `shared/listen.script.golden.json` is the script both sides check.

- `/answers/config` adds `listen {languages[code]}`: the answer languages Listen can speak. The
  Listen control is drawn only after `done`, with an answer id, in a listed language; absent or
  off the contract, it is not drawn.
- `GET /api/answers/{answerId}/listen?language=<code>` (the asker) answers `ListenScript
  {schemaVersion 1, answerId, language, tracks[ListenTrack] (at least one)}`, refused by the
  client unless `answerId` and `language` are the ones asked.
- `ListenTrack {blockId, audioUrl (https; the private media bucket's presigned URL), durationSeconds
  > 0, words[ListenWord] (at least one)}`, one per part of each `prose` or `process_ladder` block
  in reading order (sections by `order`, blocks in order); a block over 2,000 characters, or with
  sentences in two languages, has several tracks with the same `blockId`, in order (decision
  0035); the client plays them one after another. `?section=<id>` reads one section.
- `ListenWord {sentenceId, text, start, end}`: seconds from the track's start, `start` never
  decreasing, `end` at least `start`, `start` within the track. `text` is a word of the
  sentence's shown text in the answer language, found there in order from where the previous
  word of the same sentence ended (text, not character offsets, as term spans; decision 0030
  point 4). The sentence being read is highlighted, and the word too when it is found.

## Fixtures (`shared/`)

Hand-written from the seed claims and sources, so every citation resolves to a seeded claim
source (ids by `claim_seed.seed_id`), and from the science golden's stage, material and reaction
ids:

- `explainer.document.golden.json`: Kutch Ajrakh at Expert depth; a process ladder (stages 4,
  5, 6, 11), an image block (a CC BY-SA Commons photograph inline, a V&A link card), a reused
  water `prose` block and a chemistry `prose` block.
- `explainer.piece.golden.json`: the stored piece the water block was reused from.
- `explainer.term.golden.json`: the term `kut`, summarised from its stored claim.
- `explainer.stream.golden.sse`: the stream that reduces to the document.

The backend reproduces each byte for byte (`tests/contracts/test_explainer_*.py`,
`test_knowledge_piece_contract.py`); the client parses them (`e2e/explainer-contract-unit.spec.ts`)
and reduces the stream to the document (`e2e/explainer-view-unit.spec.ts`).

## Build status

Phase A is built against this page: the understanding step and depth (0031), the asking UI
(0036), pictures and terms (0034: adapters, tables, the glossary, the term route; called from the
answer stream since 0039), the explainer UI (0037: the explainer stream, the built blocks, the
term sheet and the Listen client), Listen's route and audio (0035: `GET
/api/answers/{answerId}/listen`, `docs/contracts/voice.md` Listen,
`shared/listen.script.golden.json`), sectioned composition (0032: sections researched and composed
in parallel, `prose` and `process_ladder` blocks built by the server and checked, the trail,
per-block translation, the explainer kept under `Answer.payload.explainer`; the flow is
`docs/contracts/research.md`, the answering service) and stored pieces with reuse (0033: the
table, staleness, topic keys, reuse before planning, Research again, the nightly rebuild). The
kinds of later phases stay declared until their phase builds them.

### How the server fills the phase A blocks (decision 0032)

- A section is a field the question touches (`Understanding.disciplines`, most important first,
  at most the depth's `maxSections`; `OVERVIEW` when the understanding names none), titled by
  `research/sections.DISCIPLINE_TITLES`.
- `prose`: the composer's sentences that passed its checks, each with the visible citations of
  the stored claims it rests on (written back first for live evidence); the whole block is refused
  when one sentence cites no stored claim, is not a fact or states a figure that none of its
  claims' texts and quotes holds.
- `process_ladder`: only in a `PROCESS` section of a known craft. The model chooses stage ids from
  the stored stages offered to it; the server builds every stage from the stored rows
  (`science/ladder`) and refuses the ladder unless each stage, sentence (a stored claim of that
  stage, as stored or as its translation's `original`), material, condition and reaction is a
  stored row of that stage.
- `images`: after the section's other blocks, from the claims they cite (decision 0039, above).
- A refused block is dropped and logged; a section left without blocks ends `EMPTY` with what it
  searched. Translation runs per checked block; ladder names and conditions stay as stored; an
  `images` block is not translated.
