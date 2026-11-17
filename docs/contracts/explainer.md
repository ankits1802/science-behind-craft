# Explainer contract

An answer becomes an explainer: ordered sections, each holding typed blocks, streamed as they
are ready and stored as knowledge pieces for later answers (`docs/plans/answer-experience.md`
sections 2.1 to 2.4, 2.7 and 2.8). The code is the typed models in `backend/app/research/`
(`explainer.py`, `blocks.py`, `blocks_place.py`, `blocks_matter.py`, `blocks_people.py`,
`terms.py`, `media_refs.py`, `subject_keys.py`, `knowledge_pieces.py`, `depth.py`,
`citations.py`, and for phase B `datasets.py`, `rivers.py`, `calendar.py`, `reactions.py`,
`expert_panel.py`), the block builder registry `backend/app/services/block_builders.py` and the
interface its builders implement `backend/app/services/builder_interface.py`, and the
client types and runtime shapes in `frontend/lib/explainerContract.ts`, `explainerBlockBase.ts`,
`explainerPlace.ts`, `explainerMatter.ts`, `explainerExperts.ts` and `explainerStream.ts` with the
renderer registry `frontend/components/answer/blockRenderers.ts`. Change a type only together
with this page, the fixtures and both sides' tests. Design choices: decisions 0030 and 0042.

Last reviewed: 2026-11-18.

## Ground rules

- Every fact carries a citation to a source or a dataset row. A block that cites nothing does not
  construct; a section that shows nothing ends `EMPTY` and says what it searched.
- Numbers, coordinates, districts and river paths come from claims or datasets, never from a
  model: a model chooses and orders, the server fills values. A ladder condition's `stated` text
  must occur in one of its citations' quotes; a name a model picks (a river, a supply origin, a
  material word) must be stated by a cited sentence or its quote (`blocks.named_in`).
- A value drawn from a dataset cites the dataset row (`DatasetRef`, `research/datasets.py`, the
  region contract's dataset shape); every map carries `BOUNDARY_CAPTION` word for word and cites
  `DR_DISTRICT_SHAPES`.
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
| `expert_view` | B | yes (0046) |
| `region_story`, `map_layer` | B | yes (0044) |
| `seasons`, `supply_map` | B | yes (0047) |
| `reaction_player`, `material_card`, `molecule_3d` | B | yes (0050) |
| `simulation`, `what_if`, `zoom_story`, `timeline_map` | C | declared |
| `quiz`, `compare`, `in_practice`, `open_questions` | D | declared |
| `artisan_voice` | E | declared |
| `designs` | deferred (owner, 2026-11-17) | declared |

A phase builds a kind by adding it to `BUILT_BLOCK_KINDS` (server and client, pinned by
`e2e/backend-vocabulary-unit.spec.ts`) and its client shape and renderer; the envelope does not
change. The lane that completes a kind (its builder entry and its renderer both present) adds it
on both sides in one change: `tests/answering/test_block_builders.py` requires a builder entry
for every built later-phase kind and `e2e/explainer-phase-b-unit.spec.ts` a renderer for every
built kind.

Each block model declares `SENTENCES`, the one map of where its sentences sit (for example
`steps[].sentence`, `take[]`, `differs[].thisView`). `cited_sentences()`, the payload walk that
translation and term marking use (`explainer.payload_sentences`, `with_payload_sentences`) and
the stored piece's sentence ids all read it, in reading order. `shown_labels()` are the stored
names a block shows besides sentences (a material, a river, a district); a piece's vector embeds
both.

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

### Phase B blocks (decision 0042)

`ExplainerSentence` is written "sentence"; every sentence is a cited fact (never `HYPOTHESIS`),
listed once per block. "Server" is what the builder fills from stored rows or datasets; "model"
is all a model may do. Every validator below fails closed: a block that breaks one does not
construct, and the builder that made it adds nothing.

- **`region_story`** `{river: RiverPath?, districts[DistrictRef] (1+), steps[{districtLgd?,
  sentence}] (1+), layers[layer id], datasets[DatasetRef] (1+), boundaryCaption}`.
  `RiverPath {datasetCode "HYDRORIVERS_1_0", mainRiv, reachIds[] (source to outlet, once each,
  the last is `mainRiv`), districtLgds[] (districts reached, path order, once each), name?}`;
  `DistrictRef {districtLgd, name, stateName}`. Server: the trace (`docs/contracts/region.md`,
  Rivers), the districts (the river's first, in path order, then the story's others) with names
  from the LGD register, the dataset rows (`DR_DISTRICT_SHAPES`, and `HYDRORIVERS_1_0` with a
  river), the caption. Model: which offered basin (by `mainRiv`) or none, which claims become
  steps, their order and district, which offered layers. Rules: the caption is
  `BOUNDARY_CAPTION`; each district, layer and dataset once; steps narrate listed districts, and
  a step names its district only when its sentence or quotes name it (`blocks.named_in`, decision
  0050); the
  river's districts lead `districts` in path order; a river `name` is stated by a step sentence or
  its quote; the builder checks the trace against the stored reaches (`rivers.trace_problems`).
  Cites the steps' claims and the dataset rows. **Piece:** cross-craft (`craftId` null), the
  section's facet, topic `<facet namespace>:basin-<mainRiv>`, else `<namespace>:lgd-<code>` for
  each district (`knowledge_pieces.piece_slot`).
- **`map_layer`** `{layer, layerVersion, title, datasets[DatasetRef] (exactly 2), highlighted[]
  (district LGD codes, 1+), boundaryCaption}`. Server: everything, from `geo/layers.MAP_LAYERS`
  and the layer route (`GET /api/map/layers/{layer}`: id, the version it answered, title, its
  dataset row then `DR_DISTRICT_SHAPES`). Model: which offered layer, which listed districts to
  highlight. The client draws the route's current values and classes under the caption; a newer
  version is still drawn (values are dataset rows, not claims). **Piece:** none (it cites no
  claim); rebuilt each time.
- **`reaction_player`** `{steps[ReactionStep] (1+)}`, `ReactionStep {reactionId, stageId?,
  kind, label, species[ReactionSpecies] (2+), equation?, balanced, level, citations (1+)}`.
  Server: every value from the stored `Reaction` rows and their citations (the Process tab's
  reaction view). Model: which offered reactions, their order. Rules: a reactant and a product;
  `equation` is `mhchem_equation(species)`; balanced only with every formula; `level` is
  `reaction_level` of the citations (an unbalanced reaction with every formula is capped at
  `HYPOTHESIS`); each reaction once. The builder re-checks steps against the process rows, as
  ladders are (`reaction_player_problems`, decision 0045). Replaces the stream's `reaction` event,
  which no server path emits and which stays declared until removed (`docs/TECH_DEBT.md`). **Piece:** the section's slot; reuse re-checks against the process rows.
- **`material_card`** `{materialId?, compoundId?, termKey?, name, materialKind?, role?, formula?,
  pubchemCid?, wikidataId?, localNames[], facts[sentence] (1+), handling[sentence]}`. Server: name,
  kind and role from the stored `Material` (and its stage role), formula and CID from its
  `Compound` (CID filled by `link_compounds`), local names and Wikidata id from the glossary
  `Term`. Model: which claims are facts and which are handling. Rules: kind or role only with a
  material id, formula or CID only with a compound id, local names or Wikidata only with a term
  key; local names once each. **Piece:** the section's slot.
- **`molecule_3d`** `{compoundId, pubchemCid, name, formula?, sourceId}`. Server: everything from
  the stored `Compound` and its `COMPOUND_RECORD` source (`compound_lookup.record_source_id`).
  Model: which compound of the section's blocks. The conformer comes through the PubChem adapter:
  `GET /api/molecules/{pubchemCid}/conformer` (signed in) answers the 3D SDF, cached in the
  private media bucket, 404 without a 3D conformer; the builder adds a molecule only for a
  compound with a kept conformer (decision 0045). Cites its record. **Piece:** none (it cites no
  claim).
- **`expert_view`** `{seat, take[sentence] (1+), agreesWith[seat], differs[{seat, thisView,
  otherView}]}`. Server: the seat (from `Understanding.seats`, `expert_panel.speaking_seats` of
  the section's field), the take's citations from stored claims, both sides of a difference as
  the claims stand stored, the agreements (a shared cited claim). Model: composes the take from
  the seat's brief, choosing claims; proposes differences, which the server keeps only on two
  stored facts about one subject from two sources (decision 0046). Rules: never its own
  seat; each other seat once; a difference rests each view on its own claims and its own
  sources. In a section (`expert_pairing_problems`, checked by `ExplainerSection`): one view per
  seat; an agreement is mutual; a difference is "Experts differ" only when the other seat states
  the mirrored difference (its `thisView` cites this view's `otherView` claims and the other way
  round). The client draws one "Experts differ" card per pair with both citations
  (`expertsDiffer`). **Piece:** the section's slot; the views of a section are one reuse set.
- **`seasons`** `{rows[{stageId?, label, months[], season?, sentence}] (1+), rainfall:
  MonthlyRain?, datasets[DatasetRef]}`, `MonthlyRain {district: DistrictRef, datasetCode, period,
  millimetres[12]}` (the district by its register name and state, decision 0050). Server: the label (the stored stage's name, else the claim's subject), the
  months and season read from the sentence and its quotes (`calendar.months_named`,
  `seasons_named`: capitalised month names and ranges, `MONSOON`, `WINTER`, `SUMMER` from their
  words), the rainfall from the CHIRPS monthly normals of the craft's district (decision 0043's
  rows, read by `services/monthly_rain.district_rainfall`) and its dataset row. Model: which
  claims become rows, their order. Rules: months 1-12 once each in order; a row has months or a
  season, each named by its sentence or quotes, unless it is a stored stage (`stageId`) listed
  without them (decision 0047); `datasets` is the rainfall's dataset row exactly when there is
  rainfall. **Piece:** the section's slot.
- **`supply_map`** `{links[{material, materialId?, termKey?, origin, wikidataId?, latitude?,
  longitude?, sentence}] (1+)}`. Server: `material` is the glossary term's label or the stored
  material's name, else words the sentence states; coordinates are the Wikidata item's (P625) for
  the origin. Model: which claims, which material and origin words. Rules: the origin is stated
  by the sentence or its quotes; an unstored material too; an origin is placed only with a
  Wikidata id and both coordinates; each origin of a material once. **Piece:** the section's slot.

Pieces of one answer never supersede each other: a section may store several pieces of one kind
(material cards, expert views), and only pieces from earlier answers are superseded
(`piece_store._supersede`, decision 0045).

### The expert panel (`research/expert_panel.py`)

The 18 seats of plan section 4 feature 6 are `EXPERT_PANEL`, in `EXPERT_SEATS` order, each a
`SeatBrief {seat, label, brief, sourceKinds[], fields[]}`: the label the client shows
(`EXPERT_SEAT_LABELS`, pinned to the panel), the role brief a compose prompt gives the seat, the
source kinds it prefers (most preferred first), and the fields (disciplines) it speaks to. Every
field has at least one seat. The understanding step seats experts by the depth's range
(`DepthPolicy`: Basic 2, Detailed 4, Expert 6 to 10; plan 2.4); a seated expert gives a view in each
section whose field it speaks to (`seats_for`), from the same evidence as the section.
`speaking_seats(discipline, seated, depth=)` is the seats a section hears: the seated ones once
each, the depth's first `max_experts`, those whose fields hold the section's, never a
`TESTIMONY_SEATS` seat (the artisan's voice, which speaks only from phase E's field testimony).
`PANEL_FIELDS` is every field a speaking seat covers.

### Block builders (`services/block_builders.py`)

`BLOCK_BUILDERS` is the registry; later lanes add `BuilderEntry {kind, disciplines, make,
wait_seconds}` entries and nothing else. The interface a builder implements is
`services/builder_interface.py`, which builder modules import (the registry imports the builders,
so importing the registry from a builder would be a cycle; decision 0045). `make(BuilderTools)`
returns a builder (`async build(BuildAsk) -> Built`); `from_registry` makes builders only for
kinds already in `BUILT_BLOCK_KINDS`, so no builder spends work on a kind no reader can see yet;
`BuilderTools {sessions, live, plan_model, compose_model}` (both models spend only from the
answer's headroom: `compose_model` since decision 0046, `plan_model` since decision 0050); `BuildAsk {answer_id, section,
request (the answer's `PlanRequest`: question, craft, depth, seats, language), blocks (the
section's checked English prose and ladder), cited (their claims and sources)}`; `Built {blocks,
sources}` (the source refs of every source the blocks cite beyond `cited`). An entry adds a
later-phase kind to the fields it names and waits `BUILDER_WAIT_SECONDS` (8 s) unless it raises
it, at most `BUILDER_WAIT_MAX_SECONDS` (60 s) for a model call. Entries are listed in
`PIECE_BLOCK_ORDER`, so a fresh section shows its added blocks in the order a reused one reads
them; `rebuilt_on_reuse` marks the kinds that are never pieces (`map_layer`, `molecule_3d`).

The sectioned flow makes one call: once a section's final attempt is checked, its builders start
together (`SectionBuilds.start`; none when the section has no checked prose or ladder, so it stays
`EMPTY` with what it searched, decision 0050) while the prose and ladder are translated and sent; then the
added blocks are numbered after them (`<section>.b<n>`), term-marked, translated and sent, before
the `images` block (renumbered after them), the open questions and `section_done`. Added blocks
join the stored explainer and, in English, the section's pieces. A builder that fails, overruns
its wait, makes another kind, makes a kind not yet built, carries a reuse mark or cites a source
it did not return adds nothing and is logged; the section is never failed by a builder. A builder
never holds a database connection while it waits on a model, the router or HTTP (decision 0040).
A reused section runs the `rebuilt_on_reuse` builders over its placed pieces and the reused
claims (`BlockBuilders.for_reuse`, `reused_sections.ReuseBuilds`), sending what they add after the
placed blocks and before the pictures, so a reused climate section keeps its map (decision 0050).

### Matter builders as built (decision 0045)

Registered in `BLOCK_BUILDERS` from `services/matter_builders.py`; each reads the craft's matter
in one short session first (`services/craft_matter.craft_matter`: the Process tab's rows, the
glossary terms of each material's concept, the compounds of its materials and reaction species,
their PubChem record sources), and an answer for any craft gets none.

- **`reaction_player`** (`CHEMISTRY`, 8 s): the craft's shown reactions in process order, each
  step the Process tab's reaction view (`science/reaction_player`), at most `REACTION_STEPS_MAX`
  (8; past it the reactions the section's claims cite are kept first). No model is asked.
  `reaction_player_problems` refuses a reaction that is not a stored row of the craft, a step
  whose stage, kind, label, species, equation or balance differ from the row, and a citation not
  linked to the reaction, when built and when its piece is reused.
- **`material_card`** (`CHEMISTRY`, `MATERIALS`, 20 s): materials a section sentence marks by a
  glossary term or names, at most 3, each offered with its own stored claims and the section's
  claims naming it (facts, at most 10); one plan-model call (`composer/material_cards`) sorts
  them into facts and handling by ref; an unknown ref is dropped and a card without a fact is not
  shown. `role` only when every stage use agrees; `termKey`, `localNames` and `wikidataId` from
  the linked term whose label the material's name contains; `formula` and `pubchemCid` only from
  a compound the compound lookup linked to its PubChem record.
- **`molecule_3d`** (`CHEMISTRY`, `MATERIALS`, 8 s): the first compound, in order of first
  mention, with a CID, a stored record source and a 3D conformer (at most 3 tried); one per
  section.

`GET /api/molecules/{pubchemCid}/conformer` (signed in; it checks the stored compound on the
request's one session and releases the connection before the bucket and PubChem, decision 0050)
answers the compound's 3D SDF
(`chemical/x-mdl-sdfile`, `Cache-Control: private, max-age=604800`) for a CID a stored `Compound`
holds; 404 `{detail}` for any other CID or a compound PubChem has no 3D conformer for, 503 when
the media bucket or PubChem fails, 422 for a CID below 1. The SDF comes from
`PubChemAdapter.conformer` (PUG REST `compound/cid/<cid>/record/SDF?record_type=3d`, paced at
one call per 0.25 s, refused unless it is that CID's terminated 3D molfile of at most 256 KiB)
and is kept with a miss in the private bucket at `media/molecules/<cid>/conformer.json`
(`ConformerRecord {schemaVersion 1, pubchemCid, sdf | null, checkedAt}`); a kept record answers
without calling PubChem.

### Place builders as built (decision 0044)

Registered in `BLOCK_BUILDERS` from `services/place_builders.py`; an answer for any craft, or a
craft with no cited district that has a polygon (`place_offers.mapped_districts`, the region
route's district places), gets neither.

- **`region_story`** (`GEOGRAPHY`, 20 s). Nothing until the river lines are loaded
  (`river_store.rivers_loaded`; logged once per answer). One short session reads the offer
  (`place_offers.region_offer`): the craft's districts; at most 3 rivers crossing them
  (`rivers_crossing`, by the crossing reach's Strahler order, then mean discharge, then upstream
  area), each traced with the 0043 tracer; district names from the register; the registry layers
  of the water, climate, soil, geology and terrain facets with a value in a craft district; their
  dataset rows. Then one plan-model call (`composer/region_story`, every river, district, layer
  and statement in its own untrusted block) answers refs: a river or `none`, at most 8 steps
  `{claim, district | none}` and at most 4 layers. The statements are the fact-level stored claims
  the section's blocks cite, in order of first citation, at most 12, each a step as stored with
  its visible citations; an unknown claim ref drops its step, a district the story does not list
  or the step's sentence and quotes do not name leaves the step unplaced (shown as "Step n" with no
  map focus, decision 0050), an unoffered layer or one whose dataset row is missing is left out.
  `datasets` is `DR_DISTRICT_SHAPES` (no row, no story), `HYDRORIVERS_1_0` with a river (no row,
  no river) and each listed layer's row. `river.name` is always null: HydroRIVERS names no river
  (decision 0044). No chosen step is no story.
- **`map_layer`** (`GEOLOGY`, `CLIMATE`, 8 s, no model): the facet's registry layers
  (`geo/section_layers`: soil, geology and terrain for `GEOLOGY`, climate for `CLIMATE`) in
  registry order, those whose subject words (`LAYER_SUBJECTS`, whole words) a section sentence
  names first; the first with a value in a craft district becomes the block, built from
  `map_layer(layer_values(...))` exactly as the layer route answers it, highlighting the craft's
  districts with a value.
- **Pieces.** A story is stored in `piece_slot`'s cross-craft slot (`region_topic`; a key past
  `TOPIC_KEY_MAX_CHARS` is not stored). A reused facet section also gets the current story keyed
  by a basin crossing the craft's districts or by those districts
  (`services/region_pieces.region_story_pieces`, looked up only when a geography section is asked,
  `REGION_STORY_FACETS`) when it passes the reuse rule as a craft-less
  piece and its river still follows the stored reaches (`river_store.stored_trace_problems`);
  the story kept with that section wins, else the newest (`piece_reuse.with_region_story`).

### Seasons and supply as built (decision 0047)

Registered in `BLOCK_BUILDERS` from `services/season_supply_builders.py`; an answer for any craft
gets neither.

- **`seasons`** (`CLIMATE`, 8 s, no model). One short session reads the craft's Process rows, the
  rainfall and the concept names of the section's claims. Rows (`services/season_rows`), in order:
  each stage in process order whose stored fact claims name a month or a season (its first such
  claim), else whose claim the section cites (listed with no months and no season); then the
  section's fact claims that are no stage's and name a month or a season, labelled by their
  concept's name. Timing is read from the claim's own text: `calendar.year_months` (a month beside
  a day or a year is a date, not a month of the year) and `only_season` (a text naming two seasons
  gives none); a month, range or season whose clause holds a negating or excluding word within
  five words before it (`EXCLUDING_WORDS`: not, never, except, until, ...) times nothing, and Jan,
  Mar or Dec before a capitalised word is a name (decision 0050). At most `SEASON_ROWS_MAX` (12) rows, timed first; no timed row is no block. A row
  with a season and no month takes the months of the one mapping every offered quote agrees on
  (`calendar.season_months`: a season word joined to one month range in a source's quote, with no
  sentence break, clause word or other month or season between; `season_mappings`), and its
  sentence cites that quote after its own, at the weaker level. `rainfall` is the first of the
  craft's mapped districts with twelve CHIRPS normals, with its dataset row; none leaves it null.
- **`supply_map`** (`MATERIALS`, 30 s). The craft's matter (`craft_matter`) gives the materials a
  section sentence names (at most 8) and their own claims; the statements are the section's fact
  claims (at most 12) then those claims (at most 16 in all). One plan-model call
  (`composer/supply_map`, every material and statement in its own untrusted block) answers
  `{links[{statement, material | none, materialWords, origin}]}`; a link whose refs were not
  offered, whose origin or unstored material its sentence and quotes do not state, whose stored
  material's own use claims do not include the statement and whose sentence and quotes name none
  of the material's surfaces (decision 0050), or whose material is its own origin is dropped, each pair once, at most 12. A stored material is shown by
  its glossary term's label, else its name. Origins are placed through the Wikidata adapter:
  `place_candidates` (`wbsearchentities`, the hits whose matched label or alias is the origin) and
  one `place_points` SPARQL query for P625 (Earth points, preferred over normal rank, none when one
  rank holds two points). One matching item is used; of several, only the one whose description
  names a capitalised word of the link's sentence or quotes. Otherwise, or when Wikidata fails, the
  origin is listed without a place.

### Expert panel as built (decision 0046)

Registered in `BLOCK_BUILDERS` from `services/expert_views.py` (`expert_view`, every field in
`PANEL_FIELDS`, 45 s). It hears nothing for a section without a checked block or a speaking seat.

- **Evidence.** The fact-level stored claims the section's checked sentences rest on
  (`BuildAsk.cited`), those the blocks cite first, each offered as its claim text and its
  citations' quotes inside an untrusted block (`panel_candidates`).
- **One call.** `composer/expert_takes.compose_takes`: one `COMPOSE` call (Claude Sonnet first)
  with the section line, an `Expert <SEAT>: <label>. <brief>` line per speaking seat, the
  statements and the question in untrusted blocks, and the compose source rules. Reply
  `{views[{seat, take[{text, quotes[{source, quote}]}]}], differences[{seat, statement,
  otherSeat, otherStatement}]}`, seats and statements as enums of what was offered; at most 3
  take sentences and 3 differences are read; a reply off the schema is a model failure.
- **Takes.** Every take sentence passes the prose checks (the composer's sentence validator, then
  `section_blocks.prose_problems`) or that seat's view is not shown; a view for a seat not
  offered is ignored.
- **Experts differ.** A proposed pair is kept when its seats differ and both gave a view, both
  statements are fact-level stored claims of the section, they are two claims, no source is
  cited by both and both claims are stored on one concept (`ClaimView.concept_id`); each pair of
  seats differs once. Both views carry it mirrored, each side the claim's own text, level and
  citations (`difference_refusal` names why a pair is refused).
- **Agreement.** Two views whose takes cite one stored claim and that do not differ agree, both
  ways.
- **Spend.** Builders call their compose model as `AnswerSpend.headroom()` (decision 0046): a
  call is refused unless the answer keeps half its depth's cap after it; Master Admins are never
  refused. A refused, failed or late call shows no view and never fails the section.
- Block ids are `<section>.<seat>` until the registry numbers them; sentence ids number the take,
  then each difference's two sides.

### Block renderers (`frontend/components/answer/blockRenderers.ts`)

`BLOCK_RENDERERS` maps a kind to its one renderer (`{block}` props); frontend lanes add entries
and their component modules. `ExplainerBlockView` draws a block only through `renderBlock`; a
block whose kind has no renderer is not drawn at all. `BLOCK_SHAPES` in `explainerContract.ts`
types every phase A and B kind; `explainerBlockShape` admits the built ones only.

The place kinds (decision 0048) enter through `components/answer/place/placeRenderers.tsx`:
`region_story` and `map_layer` load their map code on demand (`lazyBlock`), `seasons` and
`supply_map` are drawn at once and load a pin map only for a placed origin. A region story draws
the river from `GET /api/rivers/{mainRiv}` (`lib/riverTopology.ts`) and the districts from the
district shapes, lights each district as the water reaches it in `river.districtLgds` order, and
outlines a step's district and draws its stretch when the step is chosen; under either
reduced-motion switch the full course, every district and every step show at once. Every map
carries the block's `boundaryCaption` (the supply pin map the client's identical caption); the
river cites its `HYDRORIVERS_1_0` row and a layer its route's dataset row. A map layer the layer
route answers 404 for is not drawn. `explainerView.blockSentences` and `blockCitations` read the
steps', rows' and links' sentences, so their citations join the answer's one numbering.

The matter kinds (decision 0049) enter through `components/answer/matter/matterRenderers.tsx` and
the expert view through `components/answer/experts/expertRenderers.tsx`. A reaction player shows a
cast of its species with the open step's reactants and products lit by role, and its steps in
order: the open step's badges, its equation through `ChemEquation` (or the species row without
every formula) and its citations; Play advances a step every 4 s and stops on the last, and under
either reduced-motion switch every step is open and there is no playback. A material card shows
its stored name, local names, role, formula (a PubChem link only with a CID) and cited facts and
handling. A molecule loads 3Dmol.js (`lib/moleculeViewer.ts`, the one adapter, imported only when
the block nears the viewport) and the SDF of `GET /api/molecules/{pubchemCid}/conformer`, checked
as the PubChem adapter checks it (`lib/conformer.ts`); without WebGL, on a 404 or an SDF off the
contract it draws nothing, and it cites its record source with a numbered chip
(`explainerView.blockSourceIds`). A section's expert views are one panel where the first one
stands (`lib/expertPanel.sectionRuns`): seat cards, then one "Experts differ" card per pair both
seats state, the two sentences side by side with their citations.

### Declared for later phases

Fields are fixed now so the phases fill them without changing the envelope. `ExplainerSentence`
is written "sentence" below; every sentence is cited.

| Kind | Fields | Rules |
|---|---|---|
| `simulation` | `concept`, `title`, `model`, `createdAt`, `html`, `htmlSha256`, `values[{key, value, unit?, citations}]`, `hidden` | at most 200 KiB; each value once and cited (plan 2.6 adds the static check) |
| `what_if` | `changed`, `options[{label, outcome: sentence or null}]` (at least two) | an option without evidence has no outcome and is shown as unknown |
| `timeline_map` | `points[{label, yearFrom, yearTo, wikidataId, latitude, longitude, sentence}]`, `routes[{start, end, sentence}]` | coordinates from Wikidata; routes join two different listed points |
| `zoom_story` | `levels[{level, media?, districtLgd?, pubchemCid?, sentence}]` (at least two) | levels `DISTRICT`, `WORKSHOP`, `CLOTH`, `FIBRE`, `MOLECULE` in order, each once; a level is shown only with its district, licensed image or compound |
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
  researched section that cites claims and sources (`prose`, `process_ladder` and the blocks its
  builders added; an `images` block rests on illustrated claims and is not a piece), id `uuid5("knowledge-piece:<answer>:<block>")`,
  sentence ids renumbered `p<first 12 hex of the piece id>.<n>` in reading order, then embedded
  (a failure is logged; `embed_knowledge` fills it). It supersedes every earlier current piece of
  the same craft, facet, topic and kind at the same or a lower depth. Storing writes no process
  rows: stage concepts a `PROCESS` section's prose cites stay concepts (decision 0038).
- **Reusing** (`reusable`): for a craft (any-craft answers reuse nothing), unless `fresh`, the
  pieces of that craft with the asked facets and topics; a set is the pieces one answer stored for
  one facet, placed by kind (`piece_reuse.PIECE_BLOCK_ORDER`: `process_ladder`, `prose`, the phase B kinds, `images`), then in the order first shown, and it is reused only when every piece
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

`explainer.phase-b.golden.json` (decision 0042) holds every phase B kind for Kutch Ajrakh in six
sections: a region story for Kachchh (four cited steps on the Dhamadka stream, the Saran, the move
to Ajrakhpur and iron in groundwater; the `river-density` layer; the boundary and HydroRIVERS
dataset rows), a map layer (`soil-ph-0-5cm` from `region.layer.golden.json`, Kachchh highlighted),
seasons (two monsoon rows, no rainfall), a reaction player (the four seeded Ajrakh reactions from
the science seed plan), a material card (the seeded Alum with potassium alum and the `alum`
glossary term), a molecule (the seeded Alizarin compound, PubChem CID 6293 as the recorded
adapter response gives it, its record source `record_source_id(6293)`), two expert views
(Historian and Anthropologist, who differ on when the Khatris came to Kutch: the GI journal's
400 years against Khamir's seventh century) and a supply map (indigo from Shikarpur and Dhamadka,
blocks from Pethapur, unplaced). It also lists how each block is stored (`pieces`; map layer and
molecule are none) and its sources in order of first citation. The river's `reachIds` and
`mainRiv` are placeholders, named under `placeholders`, until lane 0043 loads HydroRIVERS; every
other id resolves to a seed row, a seeded science row, the LGD register, a golden or the recorded
PubChem response (`tests/contracts/test_explainer_phase_b.py`). The client parses each block with
its kind's shape and refuses it in the built-only parser and the stream
(`e2e/explainer-phase-b-unit.spec.ts`), and draws the place, matter and expert blocks from it
(`e2e/place-renderers-unit.spec.ts`, `matter-renderers-unit.spec.ts`,
`expert-panel-unit.spec.ts`).

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
kinds of later phases stay declared until their phase builds them. Phase B's contract (0042): the
kinds' final fields and validators, the builder and renderer registries (empty and wired), the
expert panel, the river data contract and the fixture; lanes 0043 to 0049 build the rest. Every
phase B kind has its renderer (0048, 0049), and the matter kinds have their builders (0045).
`expert_view` is built (0046): the panel builder, its renderer and both built lists.
`region_story` and `map_layer` are built (0044): their builders, the cross-craft region pieces and
both built lists.

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
