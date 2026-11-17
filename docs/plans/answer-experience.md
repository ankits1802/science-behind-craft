# Plan: the answer experience

Status: approved by the owner, 2026-11-17 (section 8); phase A built, not yet deployed (section 5).
Supersedes the chat-style answer and the live voice call. PLAN section 0 still binds: accuracy over speed, every claim cited, research not limited
to named sources, the knowledge base grows from every answer, no review gates.

Owner direction this plan answers (2026-11-17):

- A question is typed or dictated. Dictation uses the browser's Web Speech API, so no AI tokens are
  spent turning speech into text.
- The craft can be picked, but never has to be. The app works out the craft (or crafts) from the
  question and proceeds; a wrong guess is one tap to change.
- The answer is expert-grade across every field the question touches: chemistry, physics, materials,
  geography and water, geology and soil, climate, ecology, botany, history, economics, design, health.
  Master Admin and Admin get the fullest depth by default; students get the clear version; anyone
  can switch.
- The answer is immersive: a process ladder that fills step by step, a river that flows from its
  source across the districts it affects, soil and terrain maps when they explain something,
  reactions that play out, interactive explainers that Claude builds, pictures from the web,
  underlined terms that open a short sourced summary.
- Voice is for listening to finished research, in the reader's language. The live voice call is
  retired.
- Every source and citation stays.
- What one answer researches is stored in a structured form per craft and reused by later answers
  when it is relevant.
- Approved features 1 to 16 of the 2026-11-17 list, with a wider expert panel. Feature 17 (offline
  field copy) is not in scope.

## 1. What the reader sees

1. **Ask.** A large question box. A microphone starts dictation (live transcript, language shown,
   Stop). Optional controls under it: craft (detected, changeable, or "Any craft"), depth (Basic,
   Detailed, Expert), answer language, and Ask from a photo.
2. **Understand.** Within a second: "Answering for Kutch Ajrakh · Expert · in Hindi", each part
   changeable. Several crafts can be detected for comparison questions.
3. **Research trail.** Sources appear as they are found, read and quoted, grouped by kind (papers,
   encyclopaedia, datasets, web, stored knowledge). Reused stored pieces show as "From earlier
   research" with their date.
4. **Explainer.** Sections build one at a time, each with its own state (researching, writing,
   checking, ready). A section bar lets the reader jump. The order adapts to the question; a "how is
   it made" question leads with the process.
5. **Use it.** Listen (highlighted as it reads), Save, Export, Share, Film mode, follow-up questions
   that extend the same explainer.

The board is the visual reference: the "Answer experience" page of
https://claude.ai/artifact/Qrpuvcfq4X53uryZz2Kngs.

## 2. Architecture changes

### 2.1 The explainer document

An answer becomes an **explainer**: an ordered list of typed **blocks** inside **sections**.
Sentences keep today's contract (verbatim quote, citation, number and formula checks). New
`research/explainer.py` holds the models; `docs/contracts/explainer.md` the contract;
`shared/explainer.*.golden.json` the fixtures both sides test against.

Block kinds (each is one renderer on the web and one validator on the server):

| Block | Content | Data it may use |
|---|---|---|
| `prose` | cited sentences, term spans | claims, read documents |
| `process_ladder` | ordered stages, materials, conditions, links to science | process route, claims |
| `region_story` | river path, districts reached, narrative steps, layer list | HydroRIVERS lines, district register, geo values, claims |
| `map_layer` | a choropleth with legend and basis | geo values only |
| `reaction_player` | ordered steps, balanced equations, species | science engine, claims |
| `material_card` | formula, local names, role, origin, handling | PubChem, Wikidata, claims |
| `molecule_3d` | a PubChem compound to render in 3D | PubChem 3D conformer |
| `images` | open-licence images inline, other images as credited links | Commons, Openverse, web search |
| `simulation` | a generated interactive explainer (section 2.6) | claims passed in as data |
| `what_if` | inputs, outcomes per option | claims only |
| `timeline_map` | dated places and routes on a time slider | claims, Wikidata coordinates |
| `zoom_story` | district → workshop → cloth → fibre → molecule levels | geometry, licensed images, PubChem |
| `expert_view` | one expert's take, agreements and disagreements | claims |
| `seasons` | months against process steps | CHIRPS monthly, claims |
| `supply_map` | where each material comes from | claims, Wikidata |
| `compare` | two crafts side by side | both crafts' stored pieces |
| `in_practice` | advice per audience | claims |
| `quiz` | questions with keyed answers | claims |
| `open_questions` | unknowns and how to find out | composer hypotheses |
| `artisan_voice` | consented quotes from field interviews | documentation portal (section 4.9) |
| `designs` | prototypes made for the craft | designer portal (section 4.10) |

Rules every block validator enforces, failing closed:

- Every fact carries a citation to a source or a dataset row. A block with an uncited fact is
  dropped and the section says what it searched.
- Numbers, coordinates, districts and river paths come from claims or datasets, never from a model.
  A model chooses and orders; the server fills values.
- Geometry is the real geometry (HydroRIVERS, the district register); the boundary caption is shown
  on every map.
- Untrusted text stays inside untrusted blocks in every prompt.

### 2.2 Structured knowledge per craft (reuse)

Every finished block is stored as a **knowledge piece**, so the next relevant answer reuses it.

- New table `KnowledgePiece`: `craftId` (nullable for cross-craft pieces such as a district's water
  story), `kind` (the block kind), `facet` (process, region, chemistry, …), `topicKey` (normalised
  subject, for example `water:kachchh` or `reaction:alum-alizarin`), `language` (`en`; translations
  are cached separately as today), `depth`, `payload` (the validated block JSON), `claimIds` and
  `sourceIds` (what it rests on), `contentHash`, `embedding`, `createdFromAnswerId`, `createdAt`,
  `supersededById`.
- The structured parts also land in their natural homes so other screens use them: process stages
  and reactions in the science tables (the craft page Process tab), region stories against districts,
  terms in a `Term` glossary, images in a `MediaRef` table with licence and credit.
- **Reuse at answer time.** After the craft and facets are known, retrieval looks up pieces by
  craft, facet and topic key, then by embedding similarity to the question. A piece is reused when it
  matches the question's facet and topic, its depth is at least the requested depth, and every claim
  it rests on is still visible and not retracted. Reused pieces stream first and are marked "From
  earlier research · date". Research then runs only for facets with no reusable piece, or when the
  reader asks for fresh research.
- **Freshness.** When a claim is retracted or its level changes, every piece resting on it is
  marked stale; the next answer that would reuse it rebuilds that block instead. A nightly job
  rebuilds stale pieces for the most-asked crafts.
- **Growth.** The coverage job (decision 0011) and the full curation run (section 6) produce pieces
  too, so popular questions become instant over time.

### 2.3 Pipeline

1. **Understand** (one cheap call, Gemini Flash Lite): craft candidates (resolver plus model, never
   blocking: best match proceeds, others offered), facets and fields the question touches, the
   experts to seat (section 4.6), answer language, depth from the role default unless set.
2. **Reuse** stored pieces (section 2.2).
3. **Plan** per open facet (today's planner, extended with the expert seats).
4. **Research** per facet in parallel within the depth budget (today's tiered research; the trail
   streams per source).
5. **Compose** per section in parallel: Claude Sonnet writes each section's blocks against the block
   schema; Gemini is the fallback route. Expert views are composed from the same evidence by expert.
6. **Validate** each block (section 2.1), regenerate once, then drop with a note.
7. **Enrich** with images, term spans, 3D molecules and simulations (section 2.6) as they finish.
8. **Translate** checked English blocks (decision 0023), block by block.
9. **Store** pieces and claims (section 2.2), with citations.

Streaming: the stream contract gains `section_started`, `block`, `section_done`, `trail` events;
blocks render as they arrive. The 60-second heartbeat stays.

### 2.4 Depth by role

| Depth | Default for | Sections | Experts | Live research | Rough model cost |
|---|---|---|---|---|---|
| Basic | Student | 3 to 4 | 2 | stored first, light | low |
| Detailed | Researcher, Professor | 5 to 7 | 4 | hybrid | medium |
| Expert | Admin, Master Admin | all relevant | 6 to 10 | deep | high |

Per-answer cost caps per depth are settings in the AI budget for every role except Master Admin. **Master
Admins have no caps (owner, 2026-11-17):** no per-answer cap, no daily cap, and the monthly ceiling does not
refuse or degrade their answers; their spend still shows on Usage. For everyone else the monthly
ceiling applies and degrades Expert to Detailed at 80%.

### 2.5 Voice

- **Dictation:** Web Speech API `SpeechRecognition` in the browser, interim results shown live, the
  recogniser's language set from the reader's choice. Offered only where the browser has it (Chrome,
  Edge, Safari); hidden elsewhere. Languages are offered after a check on each target browser; Indian
  languages are expected on Chrome and must be verified one by one.
- **Listen:** ElevenLabs text to speech of the finished answer in the answer language, with word
  timings so the text highlights as it reads. Audio is cached per answer piece and language in the
  private media bucket, so a second listener costs nothing.
- **Switched off (owner, 2026-11-17):** the live voice call stays in the code but off: the voice
  session, custom-LLM endpoint and relay routes answer 404 and the voice button is not drawn. Nothing
  is deleted.

### 2.6 Generated explainers (sandboxed)

- Claude Sonnet writes one self-contained HTML file for a concept the block library cannot show (dye
  bonding, heat in a kiln, indigo oxidising, resist paste).
- **Data in, not numbers made up.** The server passes the cited values as a JSON object; a static
  check rejects numeric literals in the code that are not in that object (beyond layout constants
  such as sizes), any network API (`fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`,
  `navigator.sendBeacon`, `import()`, `eval`, `Function`), and external URLs.
- **Sandbox.** Rendered in an `iframe` with `sandbox="allow-scripts"` (no same-origin, no forms, no
  popups, no top navigation), `srcdoc`, and a CSP meta of `default-src 'none'; script-src
  'unsafe-inline'; style-src 'unsafe-inline'; img-src data:`. It cannot read the page, the account or
  the network. Size cap 200 KB.
- **Labelled.** "Generated explainer · model · date", what it was built from, View code.
- **Stored and reused** as a knowledge piece keyed by the claim set and concept; a professor can hide
  one.

### 2.7 Pictures from the web

- Inline: Wikimedia Commons and Openverse images with an open licence, shown with author, licence and
  link; relevance checked against the claim text and, for the top candidates, one cheap vision call.
- Other web images: shown as credited link cards from web search, opening the source page. Owner
  decision O2 below picks whether the card shows a thumbnail.

### 2.8 Tappable terms

The composer marks term spans against a `Term` glossary (local names included). Tapping opens a
30-second summary: Wikipedia summary first, then a quick web search with a Flash Lite summary, both
cited, cached per term and language; "Ask about it" starts a follow-up.

## 3. Data and engineering pieces this needs

| Piece | Work |
|---|---|
| River lines | HydroRIVERS lines for India simplified per basin, stored as static TopoJSON in the media bucket; a path tracer over `NEXT_DOWN` from source to mouth; districts crossed computed with PostGIS |
| Monthly rainfall | extend the geo ETL with CHIRPS monthly normals per district |
| Rainfall trends | CHIRPS annual series 1981 to 2025 per district, a trend per district |
| Glossary | `Term` table seeded from craft aliases, Wikidata labels and the master list |
| Images | Commons and Openverse adapters (one adapter per service), `MediaRef` table |
| 3D | 3Dmol.js (BSD) vendored, PubChem 3D conformers through the PubChem adapter |
| Units | Indian traditional units in Pint with cited regional values; a value is only shown with its region and source |
| PDF export | print stylesheet plus server render; citations through citeproc (APA, BibTeX) |
| Lesson builder | slides as HTML (vendored reveal.js) and PPTX (python-pptx), reading list, quiz |
| Alerts | in-app notifications and a weekly email digest through SES |

## 4. The sixteen approved features

1. **Powers-of-ten zoom.** A `zoom_story` block: district map (real geometry) → workshop photo →
   cloth → fibre (open-licence micrograph or open-access figure) → molecule in 3D. A level without a
   licensed image is skipped, never faked.
2. **3D molecules and tools.** 3Dmol.js with PubChem conformers; tools from CC0 3D collections
   (Smithsonian Open Access) when one exists for the tool, else a photo.
3. **Film mode.** Plays the explainer as a narrated sequence: each block's own animation as a scene,
   ElevenLabs narration with timings, captions in the answer language. No generated video.
4. **Trade routes through time.** `timeline_map`: dated places and routes from history claims,
   coordinates from Wikidata, a time slider; every point cited.
5. **What-if lab.** `what_if` blocks: one input changed at a time (natural or synthetic dye, river or
   well water, temperature), outcomes only from cited relationships; options without evidence are
   shown as unknown.
6. **Expert panel.** Seats chosen per question from: chemist, physicist, materials scientist,
   textile or ceramic technologist, geologist, hydrologist, soil scientist, climatologist, ecologist,
   botanist (dye and fibre plants), toxicologist and health, historian, anthropologist, economist,
   design and art historian, conservator, GI and policy expert, and the artisan's voice (feature 9).
   Each seat is a role brief with preferred source kinds; each speaks only from cited evidence;
   disagreements across seats are shown as "Experts differ", with both citations.
7. **Shared-science explorer.** A concept graph from claims (alum mordant, iron-rich water, reduction
   firing); "other crafts that share this" with links; a graph view for researchers.
8. **Local measures converter.** Recipes in local units converted to metric with the region and the
   source of each conversion.
9. **Artisan voices.** Quotes from field interviews about the craft. The owner confirmed on
   2026-11-17 that consent covers all existing transcriptions. Source: the portals' existing
   transcript API, the same one the Research app uses (`tools/field_repository/fieldrepo.py`):
   `GET /api/data/transcripts/recordings.ndjson` and `turns.ndjson` on both portals. A nightly
   KalaVigyan job pulls them, stores each transcript as a private `FIELD_INTERVIEW` source linked to
   its craft, and indexes it for retrieval and for the artisan seat of the expert panel. It signs in
   with each portal's master account (owner decision, section 8), keeps the credentials only in
   Parameter Store and makes read-only calls. No portal change is needed.
10. **Designs from the workshops.** Prototypes and designs from designer-portal workshops for the
    craft, as their sharing settings allow. Needs a peer route in the portals (section 7).
11. **Lesson builder.** Professors turn an explainer into a lesson pack: slides, reading list, quiz;
    export PPTX and PDF.
12. **Climate and risk.** Rainfall and temperature trends per district, groundwater notes where open
    data exists, and what they mean for the craft; actionable notes for policy and NGOs; every value
    with dataset, period and resolution.
13. **Market and GI insight.** GI status from the registry, signs of imitation from GI journal text,
    price ranges from cited sources with date and place.
14. **Ask the map.** Tap a district: crafts practised there, and an explainer of why the land suits
    them, built from region pieces.
15. **Follow-ups that build.** A follow-up adds or deepens sections of the same explainer; the
    explainer keeps a version history.
16. **"This answer got better" alerts.** Saved explainers are re-checked when new claims arrive for
    their craft and facets; the reader gets an in-app note and an optional weekly email.

Already designed and in scope with the explainer: research trail, local names spoken, quiz, compare
two crafts, seasons and supply, export, ask from a photo (Gemini vision names the craft and
technique; the photo is private and deleted after 30 days).

## 5. Phases

Each phase ends with every check green on GitHub, one or two known-answer questions asked in
production, the E2E run at three widths, and one deploy.

| Phase | Scope | Proves |
|---|---|---|
| A. Foundation | explainer contract and stream events; block renderer shell; never-blocking craft detection; depth by role; dictation; Listen with highlighting; research trail; prose, process ladder, images and terms; knowledge pieces and reuse; retire the live voice call | an Expert answer for Kutch Ajrakh streams as sections, reuses its pieces on a second ask, and every sentence is cited |
| B. Place and matter | river lines and tracer; region story; map layers; reaction player; material cards; 3D molecules; expert panel; seasons and supply (CHIRPS monthly) | the water story for Kachchh plays from real geometry; experts differ is shown where sources disagree |
| C. Play | sandboxed generated explainers; what-if lab; film mode; powers-of-ten zoom; trade routes | a generated explainer passes the static check and runs with no network |
| D. Learn and act | quiz, compare, shared-science explorer, local measures, market and GI, climate and risk, ask the map, follow-ups that build, alerts, lesson builder, PDF and citation export | a professor builds a lesson pack from one explainer |
| E. Field voices | artisan voices from the portals' transcripts | named, credited artisan quotes appear for a craft, each cited to its recording |

**Phase A status (2026-11-17).** Built and checked offline, not yet deployed: the explainer
contract (decision 0030), understanding and depth (0031), sectioned composition (0032), knowledge
pieces and reuse (0033), pictures and terms (0034), Listen with the live call switched off (0035),
the asking screen (0036), the explainer view (0037), the review fixes (0038) and step 7 of section
2.3, pictures and term spans in the stream with https pictures allowed on every page (0039). Open:
process stages found by answers do not reach the Process tab until a source states their order
(0038), finding 8a.3, pictures after a move to `/ask` inside the app (0039, the owner's choice),
and the phase's proof: checks green on GitHub, the Kutch Ajrakh known-answer questions in
production, the E2E run at three widths and one deploy. `docs/PROGRESS.md` and
`docs/TECH_DEBT.md` hold the details.

Then the **curation run** (owner offer of 2026-11-17): every craft through Expert depth once, with a
one-time budget, producing the stored pieces of section 2.2 so most first questions are fast.

Rough effort: A two days, B two days, C two to three days, D two to three days, E one day once the
portal routes exist; the curation run one to two days of background running.

## 6. Cost

- Expert answers cost several times a Basic one: more sections, more experts, deep research, a
  generated explainer. The first Expert answers in phase A measure the real figure; until then the
  per-answer caps in section 2.4 hold the spend.
- Reuse (section 2.2) is the main saving: a second question on a covered craft and facet costs a
  fraction of the first.
- The curation run is a one-time budget outside the monthly ceiling (PLAN 17.2 estimated $700 to
  $1,000); it stops when the budget is spent.

## 7. Dependencies

- **Portal credentials** for feature 9: each portal's master account email and password in
  KalaVigyan's Parameter Store.
- **Feature 10** (designs): deferred until the workshops hold designs.
- **Keys:** Brave (web search fallback and image results) and Semantic Scholar improve research;
  neither blocks.

## 8. Owner decisions (all taken 2026-11-17)

- **O1. Live voice call:** switched off and kept; nothing deleted.
- **O2. Web images that are not openly licensed:** credited link cards with a thumbnail loaded from
  the source site, opening the source page.
- **O3. Cost:** Master Admins have no caps at all. Admin Expert answers start with a modest per-answer
  cap, raised once phase A measures real costs. The $800 monthly ceiling stays for everyone except
  Master Admins.
- **O4. Artisan quotes:** consent covers all existing transcriptions. Artisans are quoted by name,
  with their credentials (titles, awards, GI holder, years in the craft) and their place (village,
  district, state) where it matters to the answer. Phone numbers, email addresses and identity
  numbers are never shown.
- **O5. Local units:** only conversions a source states for that region are shown.
- **Sync account:** the nightly transcript sync signs in with each portal's master account, the same
  as the Research app. Its credentials live only in KalaVigyan's Parameter Store, and the sync makes
  read-only calls.
- **Feature 10 (designs from the workshops):** deferred; the workshops hold no designs yet.

## 8a. Production findings phase A must fix (E2E run 43959098727, 2026-11-17)

Status: 1 fixed (decisions 0032 and 0038), 2 fixed (0032), 4 fixed (0038); 3 open, not reproduced
offline (`docs/TECH_DEBT.md`, Craft Process tab on phones hangs).

1. **Composition with Claude Sonnet produces nothing.** Both known-answer questions (English and
   Hindi, Kutch Ajrakh, Hybrid) ended "not enough cited evidence" although 20 stored claims were
   retrieved. Server log: the first two `POST https://api.anthropic.com/v1/messages` calls answer
   400 Bad Request, `providers/anthropic_p.py` then drops `output_config.format` (the
   `rejects(model, "format")` path) and sends again, the reply is free text, and every sentence is
   dropped (`compose dropped 5 sentence(s): {'MALFORMED': 5}`; the regenerate reply has no
   `sentences` list). Fix in the sectioned-composition lane: make the compose and block schemas
   valid for Anthropic structured outputs (only supported keywords, `additionalProperties: false`
   on every object, required lists complete), test the exact schema against Anthropic's rules, and
   never fall back to free text: a rejected format is a provider failure that moves to the next
   route (Gemini), logged as such.
2. **No live research when stored composition fails.** The planner skips live research when stored
   coverage looks sufficient; when composition from stored claims then yields no block, the answer
   must run live research for that facet instead of ending with not enough evidence.
3. **Craft Process tab on phones hangs.** The phone run reached Craft Overview and timed out on
   Process (10 minutes). Find and fix in the explainer-UI or craft-page code.
4. **E2E overflow false positives.** The overflow check flags KaTeX's visually hidden MathML copy
   (`.katex-mathml`); the check in `frontend/e2e/production/` must ignore elements inside it, and
   only it.

## 9. Practice and checks

- One contract per phase written first (`docs/contracts/explainer.md` and fixtures), decisions
  recorded from 0030 on, debt in `docs/TECH_DEBT.md`.
- Every block kind has a validator test with hand-derived expected values and a fixture the web
  renderer parses; every adapter is tested on recorded responses.
- The sandbox static check has its own test set of escape attempts.
- Accuracy: one or two known-answer questions per phase in production, not a large suite.
- Reduced motion: every animation has a static end state; the river, ladder and reactions are
  readable without motion.
