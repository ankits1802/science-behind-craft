# Curation contract: dossiers, check files and the index (decision 0051)

What a curated craft dossier holds, how its quotes are verified, and what the offline checker
refuses. The plan is `docs/plans/dataset-curation.md` (sections 3, 5, 6 and 10; its section 0 and
the decisions in its section 14 are the owner's). The code is the Pydantic model and the rules in
`backend/app/curation/`, shared by the tools and the later importer, and the tools in
`tools/curation/`. The JSON Schema generated from the model is
`shared/curation.dossier.schema.json` (`python tools/curation/schema.py` writes it; a backend test
fails when it is stale). Change the model, the schema file, this page and the tests
(`backend/tests/curation/`, `tools/tests/test_curation_*.py`) together.

Last reviewed: 2026-11-17.

## Files

| Path | What | Written by |
|---|---|---|
| `backend/app/data/curation/<CraftSlug>.json` | one dossier per craft, named by its `craftSlug` | the curator |
| `backend/app/data/curation/<CraftSlug>.check.json` | the quote verification of that dossier | `tools/curation/verify.py` |
| `backend/app/data/curation/index.json` | per craft: version, coverage, counts, check status | `tools/curation/check.py` |

Nothing else lives in that folder: the checker reports any other file, and a check file whose
dossier is missing. Files are UTF-8 without a byte-order mark, LF line endings.

## Shape conventions

- Models derive from `research.base.ContractModel` (`docs/contracts/research.md`): JSON in
  camelCase, unknown fields refused, strings stripped, URLs `https://` only, instants with a
  time zone. Lists of ids or names list each entry once.
- Stored vocabularies are read from `backend/app/models/enums.py` through
  `research/vocabulary.py`; the curation-only ones live in `backend/app/curation/vocabulary.py`;
  numeric limits in `backend/app/curation/limits.py`. The schema file carries every enumeration.
- Ids are stable inside the file and become `uuid5(namespace, "curation:<slug>:<id>")` at import,
  so a re-curation updates rows instead of duplicating them.

| Part | Id | Pattern |
|---|---|---|
| sources | `S01` | `^S\d{2,3}$` |
| claims | `C001` | `^C\d{3,4}$` |
| places | `L01` | `^L\d{2,3}$` |
| communities and people | `G01` | `^G\d{2,3}$` |
| process stages | `P01` | `^P\d{2,3}$` |
| materials | `M01` | `^M\d{2,3}$` |
| tools | `T01` | `^T\d{2,3}$` |
| reactions | `R01` | `^R\d{2,3}$` |
| glossary terms | `W01` | `^W\d{2,3}$` |
| pictures | `I01` | `^I\d{2,3}$` |
| open questions | `O01` | `^O\d{2,3}$` |

## The dossier, field by field (`curation/dossier.py`)

### Header

| Field | Rule |
|---|---|
| `schemaVersion` | `1` |
| `craftSlug` | a slug of `backend/app/data/craft_master_list.json`, case as stored (`Kutch-Ajrakh`); the file is `<craftSlug>.json` |
| `version` | 1 or more; raised on each re-curation |
| `curatedAt` | instant with a zone |
| `curator` | `claude-code` |
| `coverage` | `FULL` or `THIN` (below) |
| `searched` | at least one `{query, site}`: every query and site tried, kept so a thin dossier shows what was looked for |

### Sources (`sources`, `S..`; `curation/parts.Source`)

| Field | Rule |
|---|---|
| `kind` | a stored `SOURCE_KINDS` value other than `FIELD_TESTIMONY` |
| `subKind` | only with `kind` `OTHER`: `THESIS`, `MUSEUM_RECORD`, `NGO_REPORT` or `NEWS` |
| `title`, `authors[]`, `publisher`, `year` | as the source states them, never guessed; `year` 1000 to 2100 or absent |
| `url` | https, the canonical page: no tracking parameters (`utm_*`, `fbclid`, `gclid`, ...), not a search result or redirect page |
| `doi` | when there is one (`research/evidence.DOI_PATTERN`) |
| `archivedUrl` | a Wayback Machine snapshot (`https://web.archive.org/web/<timestamp>[id_]/<url>`) when the live page blocks automated reading; `fetch.py` prints it |
| `language` | ISO 639 code (`en`, `gu`, `hi`, ...); Indian-language sources are allowed (decision D4) |
| `licence` | as the source states it |
| `access` | `OPEN`, `ABSTRACT_ONLY` or `RESTRICTED`; restricted sources are cited from their open abstract only |
| `reliability` | `A` to `D` by the rubric below |
| `retrievedAt` | the day the curator read it (`YYYY-MM-DD`) |

Every source is quoted by at least one claim; a source that yielded nothing is dropped and its
search stays under `searched`.

### Claims (`claims`, `C..`; `curation/parts.Claim`)

| Field | Rule |
|---|---|
| `discipline` | one of the answer engine's 14 disciplines (`models/enums.DISCIPLINES`, titled by `research/sections.DISCIPLINE_TITLES`) |
| `subject` | `{type, ref}`: `CRAFT` (no `ref`), or `STAGE` (`P..`), `MATERIAL` (`M..`), `PLACE` (`L..`), `TOOL` (`T..`), `COMMUNITY` (`G..`), `TERM` (`W..`) with that part's id |
| `text` | plain English, one sentence ending in `.`, `!` or `?`, 8 to 40 words |
| `quotes` | at least one `{sourceId, locator, quote}`: `quote` verbatim from the text `fetch.py` shows, in the source's language, 25 to 300 characters once normalised; `locator` a page, section, paragraph, line or timestamp |
| `hypothesis` | true only when the source states it as uncertain, a theory or a legend |
| `sensitivity` | a stored `SENSITIVITIES` value; `OPEN` unless the claim names a living private person beyond what a published source states |

`corroborated` is computed, never written: two or more quotes from different publishers
(`curation/index.corroborated`; the publisher is the source's `publisher`, else its URL's host).

### Places (`places`, `L..`; `curation/entities.Place`)

`name`; `kind` `VILLAGE`, `TOWN`, `DISTRICT`, `STATE`, `COUNTRY`, `REGION` or `RIVER`;
`district` and `state`; `country`; `wikidata` (`Q...`) when one exists; `role` (one of
`PRACTISED`, `ORIGIN`, `HISTORIC_CENTRE`, `MATERIAL_SOURCE`, `MARKET`, `MIGRATED_FROM`,
`MIGRATED_TO`); `claimIds` (one or more) that state the role. A place with two roles (Dhamadka,
practised and a historic centre) is listed once per role, each with its own claims. For
`country` `India`, a village, town or district names its district and state, and both are
written exactly as the LGD register names them (`backend/app/data/lgd_register.json`, its pending districts included; read through
`data/district_register.py`). `district-shapes.json` holds geometry by LGD code only, so names
are matched against the register and the import joins shapes by code. Places outside India are
not checked against a register.

### Communities and people (`communities`, `G..`; `curation/entities.Community`)

`kind` `COMMUNITY`, `PERSON` or `ORGANISATION`; `name`; `localNames[]`; `honours[]` (a `PERSON`
only); `placeId`; `claimIds`. A named person appears only when a published source names them in
connection with the craft, with name, honours and place only (decision D6): a `PERSON` carries a
`placeId`. Never phone numbers, email addresses, identity numbers or home addresses.

### Process stages (`stages`, `P..`; `curation/entities.Stage`)

`name`, `localName`; `stageType` (stored `STAGE_TYPES`); `order` with `orderClaimId` together, or
neither: order is set only when a source states the sequence, and no two stages share one;
`duration` and `season` as `{text, claimId}`, where `text` is stated by that claim or its quotes;
`materials[{materialId, claimId}]` and `tools[{toolId, claimId}]`, each use backed by a claim;
`claimIds` (what happens in the stage and why).

### Materials, tools and reactions (`curation/entities`)

- `materials` (`M..`): `name`; `kind` (stored `MATERIAL_KINDS`); `role` (stored `MATERIAL_ROLES`
  other than `TOOL`); `localNames[]`; `botanicalName` for plants; `pubchemCid` only for a
  well-defined substance, checked against PubChem's own record; `claimIds`.
- `tools` (`T..`): `name`, `localNames[]`, `claimIds`.
- `reactions` (`R..`), only when a source states them: `kind` (stored `REACTION_KINDS`);
  `stageId`; `reactants[]` and `products[]` (`{name, formula?}`, one or more each); `claimIds`.
  Every formula occurs in a quote of those claims. The science engine balances on import; an
  unbalanceable reaction is kept as text with its citation.

### Environment links (`environment`; `curation/records.EnvironmentLink`)

`{factor, placeId?, claimIds}`, `factor` one of `WATER`, `SOIL`, `CLIMATE`, `LANDFORM`,
`VEGETATION`, `OTHER`: claims that tie the craft to its land, water and climate. Dataset values
(rainfall, soil, temperature) are not curated; the geo ETL supplies them per district.

### Market and GI (`market`; `curation/records.Market`)

- `gi`: `applicationNumber`, `certificateNumber`, `filedOn`, `registeredOn` (partial dates),
  `journalIssue`, `proprietors[]`, `authorisedUserCount`, `claimIds`. It cites at least one
  `GI_JOURNAL` or `GOVERNMENT_REPORT` source (the registry's own pages are government records),
  and every number in it (the year of each date) appears in a quote of its claims.
- `prices[{claimId, date, placeId}]`: a price only with its date, place and source.
- `workforce[{claimId, year}]`: numbers of artisans or households only with the year the
  source states, which appears in that claim's quotes.

### Glossary (`glossary`, `W..`; `curation/records.Term`)

`term`, `meaning` (as a source gives it), `language` (ISO 639), `script` (ISO 15924, `Gujr`),
`claimIds`. These feed the `Term` glossary that answers underline.

### Conflicts and open questions (`curation/parts`)

- `conflicts[{claimIds (two or more), about}]`: facts sources state differently, shown as
  "Sources differ" with every citation and never resolved by the curator.
- `openQuestions[{id O.., question, claimIds, settledBy?}]`: what the sources say is unknown or
  disputed, and every hypothesis claim, with what would settle it when a source says so.

### Pictures (`pictures`, `I..`, at most 6; `curation/records.Picture`)

`url`, `pageUrl`, `author`, `licence`, `licenceUrl`, `caption`, and the `claimIds` or `stageId`
it shows (at least one). The licence or licence URL is on the open-licence allow-list
(`research/licences.open_licence`). No screenshots of other sites.

### The overview (`overview`; `curation/overview.py`)

- `lede`: 2 to 4 `{text, claimIds}` sentences: what the craft is, where, by whom, what is
  distinctive.
- `keyFacts`: 1 to 8 `{label, value, claimIds}`.
- `sections`: `{discipline, sentences (3 to 8)}`, one per discipline, each discipline with at
  least 3 non-hypothesis claims.

Every sentence is one sentence, cites claims (never a hypothesis), carries no number, date,
unit or formula that no quote of its claims holds, and at least half of its content words
occur in its claims and their quotes (`research/quotes.quote_overlap`, the composer's rule).
The import runs the answer engine's prose validator and drops a failing sentence.

### Coverage (`curation/coverage.py`)

| Target | FULL | THIN |
|---|---|---|
| Sources | 8 or more, 3 or more rated A or B | whatever exists |
| Claims | 40 to 150 | 5 to 150 |
| Disciplines with 3 or more claims (hypotheses not counted) | `OVERVIEW`, `HISTORY`, `PROCESS`, `MATERIALS` and 2 more | no minimum |
| Places | at least one centre (`PRACTISED` or `HISTORIC_CENTRE`), each Indian centre with its district | as found |
| Process | at least one stage | as found |
| Overview | lede, key facts, 3 or more sections | lede and key facts |

A `FULL` dossier must meet every FULL target. A `THIN` dossier must meet the THIN targets and
must not meet every FULL target (then it is marked `FULL`). A thin dossier is never padded.

## Reliability rubric (the checker's table)

- **A** primary or authoritative: GI journal and registry, peer-reviewed papers, museum
  collection records, government reports (Textiles Committee, Development Commissioner
  (Handicrafts), state handicraft boards), academic books.
- **B** theses, conference papers, edited encyclopedias, established craft institutions with
  named authors.
- **C** reputable press features and artisan organisations' own pages with a named author.
- **D** other web pages and retailers. A claim whose quotes all come from D sources is refused,
  except an `ECONOMICS` claim stating a price in a currency (a dated retailer page as a price on
  that date).

Never used: shadow libraries, AI-generated content farms, social media posts, unattributed blog
spam, anything behind a login.

## Reading and matching (`tools/curation/reading.py`, `curation/matching.py`)

`fetch.py` and `verify.py` read a source with the same function (`reading.source_text`):

- Plain HTTP (`httpx`) with a browser-like user agent, redirects followed (at most 10), the
  final URL reported; one request per host at a time with 1.5 s between requests to a host; a
  response over 40 MiB is refused, never truncated.
- HTML through the fetcher's own trafilatura extraction (`app.fetcher.extract`: scripts, styles
  and hidden elements dropped; capped at 200,000 characters and marked truncated), PDF through
  pypdf (`app.fetcher.pdf.pdf_text`, up to 2,000 pages), plain text as is. A server's wrong
  content type is corrected by sniffing (`%PDF-`, a leading `<`).
- When the live page refuses (an HTTP error, a failed connection, no extractable text), the
  source's `archivedUrl`, else the latest Wayback Machine capture with status 200 (the CDX
  index), is read in its raw form (`<timestamp>id_`).
- The text is normalised once (`research/quotes.normalise_quote_lines`): Unicode NFKC, soft
  hyphens removed, hyphenated line breaks joined, curly quotes and dashes folded to ASCII,
  whitespace collapsed inside each line, blank lines dropped. `fetch.py` prints these lines
  numbered, so the curator copies quotes from exactly what the verifier sees.
- A quote passes when, case-folded, it occurs in the case-folded text with whitespace and
  line breaks collapsed and hyphens between letters ignored (`research/quotes.quote_key`),
  starting and ending on a word boundary and never inside a number (`50` does not occur in
  `150`). Case is folded for matching only; the dossier keeps the quote as copied.

## The check file (`curation/check_file.py`)

```
CheckFile {schemaVersion 1, craftSlug, dossierVersion, dossierDigest, checkedAt, tool,
           sources[SourceCheck], quotes[QuoteCheckEntry]}
SourceCheck {sourceId, url, route LIVE|ARCHIVE|null, readUrl, finalUrl, fetchedAt, contentType,
             textSha256, characters, truncated, problem}
QuoteCheckEntry {claimId, sourceId, quote, result PASS|FAIL}
```

- `tool` is `VERIFY_TOOL` (`kalavigyan-curation-verify/1`); a check file from another version is
  stale, so a change to the matching rule bumps it and forces re-verification.
- `dossierDigest` is the SHA-256 of the craft slug, every source's id, URL and archived URL, and
  every quote's claim, source and text (`verified_digest`). Prose, overview and structure edits
  keep it; any change to a source or quote makes the check file stale.
- `textSha256` is the SHA-256 of the normalised text the quotes were matched against; a source
  that could not be read has no hash and a `problem` naming both the live and the archive
  failure, and every quote from it is `FAIL`.

A check file is current when its craft and tool match, its digest equals the dossier's, its
`checkedAt` is not before the dossier's `curatedAt` and it covers every source. File times are
not used: a checkout resets them. A claim keeps only quotes that passed; a claim left with none
is dropped, and a source that could not be read is dropped with its claims.

## The checks (`tools/curation/check.py`, `curation/checks.py`)

One line per problem, `<file>: <where>: <message>`, and a non-zero exit on any:

1. Schema and vocabulary (`Dossier.model_validate_json`); a file that does not validate gets
   only these lines.
2. Every id used once per part; every reference resolves (claims to sources and subjects;
   places, communities, stages, materials, tools, reactions, environment links, market records,
   glossary terms, pictures, conflicts, open questions and the overview to claims, places,
   stages, materials and tools). Unresolved references stop the remaining rules.
3. Craft slug on the master list; file named `<craftSlug>.json`; Indian districts and states as
   the LGD register names them (with the closest names suggested).
4. Claims: 8 to 40 words, one sentence; every number, date, unit and formula in the text
   appears in one of its quotes (`research/quotes.unsupported_figures` and the units of
   `research/translation.protected_tokens`; native digits count); no hedging word (may, might,
   probably, reportedly, ...) the quotes do not use; no relationship sentence (below).
5. Quotes 25 to 300 characters once normalised, none repeated within a claim.
6. No two claims with near-identical texts (rapidfuzz `ratio` or `token_sort_ratio` of the
   case-folded, punctuation-free texts at least 90) unless linked in one conflict.
7. Hypotheses: each cited by an open question; none cited as a fact anywhere else.
8. Reliability: no claim resting on D sources only, prices excepted.
9. Sources: each quoted by a claim; no tracking parameters; no search-result or redirect URL.
10. Stages, reactions, market records and pictures as described above.
11. The overview sentence rule; each section's discipline with 3 or more claims.
12. No personal contact details in any text field (`research/evidence.personal_data_in`:
    email addresses, spoken email addresses, phone-like and Aadhaar-like numbers); URL fields
    are not scanned.
13. Coverage class matches the targets above.
14. The check file is current and every kept quote passed (above).

A relationship sentence is graph structure written out as prose, which belongs in stages,
materials and tools: a demonstrative left without its subject at the end of the sentence
(`uses this material.`, `this tool (`), seed filler (`sequential order`, `(GI method of
production)`, `as documented`), a stored relation name in capitals (`PRECEDES`) or an arrow, or a
bare `X uses Y` / `X precedes Y` / `X is part of Y` sentence: one relation phrase
(`sentences.RELATION_PHRASES`) with at most 6 words on each side, no digit, comma, colon or
parenthesis, and none of the qualifying words (`because`, `when`, `with`, `instead`, `not`, ...)
that make it say something a reader learns.

With no file arguments `check.py` checks every dossier in the folder and reports stray files;
with file arguments it reports those files only. Either way it regenerates `index.json` from
every dossier in the folder. `--check-index` (CI) writes nothing and reports an index that
differs from what it would write; `--dir` points at another folder.

## The index (`curation/index.py`)

```
CurationIndex {schemaVersion 1, crafts[IndexEntry]}         crafts by slug
IndexEntry {craftSlug, file, version, coverage, curatedAt, counts{}, claimsByDiscipline{},
            sourcesByReliability{A, B, C, D}, check {status PASS|FAIL, problems, verifiedAt}}
```

`counts`: `sources`, `claims`, `hypotheses`, `corroborated`, `places`, `communities`, `stages`,
`orderedStages`, `materials`, `tools`, `reactions`, `environment`, `terms`, `conflicts`,
`openQuestions`, `pictures`, `overviewSections`. `claimsByDiscipline` lists the disciplines with
claims in `DISCIPLINES` order. A dossier that does not validate is listed by its file name with
null fields and `FAIL`. The index has no generation time, so it changes only when a dossier or
its check does.

## Commands

From the repository root, with the backend's environment (`backend\.venv\Scripts\python.exe` on
Windows, `backend/.venv/bin/python` on Linux):

| Step | Command |
|---|---|
| read a source as the verifier will | `python tools/curation/fetch.py <https url> [--out <file>]` |
| verify every quote of dossiers | `python tools/curation/verify.py backend/app/data/curation/<CraftSlug>.json ...` |
| run the offline checks and regenerate the index | `python tools/curation/check.py [backend/app/data/curation/<CraftSlug>.json ...]` |
| CI form (writes nothing) | `python tools/curation/check.py --check-index` |
| regenerate the JSON Schema after a model change | `python tools/curation/schema.py` |

`verify.py` and `fetch.py` use the network; `check.py` and the tests never do.

## Not built yet

The importer (`app.scripts.import_curation`, plan section 8), the critic's brief (plan section 7)
and the first dossiers (wave 0, plan section 10).
