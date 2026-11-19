---
name: kalavigyan-craft-pages
description: How to make or deepen a KalaVigyan craft, family or category page's content to the Kutch Ajrakh bar - pictures placed in chapters, the masthead, each stage's colour after and its why, native names, reactions, botanical names, GI record - cheaply, one dossier per agent, with the verifier and checker as the judges. The database is the source of truth - new facts are proposed through the Knowledge API (tools/curation/propose.py) or the MCP propose_fact tool and pass the gates; the dossiers in backend/app/data/curation are the database's versioned export, edited by hand only for a bulk import. Also the general page checklist for every craft, family, category and answer page (each page's mechanisms, ambiguous terms and signature fact derived from its own dossier; first minute, true counts, no repetition, complete at rest, layout, science correctness). Load it before creating, deepening, fixing or reviewing any dossier, check file or proposed fact, before any work on a craft page's or category page's content, and before briefing an agent to do so.
---

# KalaVigyan craft and category pages

The database holds a page's knowledge (decision 0101, item 6). A craft's dossier,
`backend/app/data/curation/<CraftSlug>.json` (a category: `categories/<CategorySlug>.json`) with
its `.check.json`, is the database's versioned export: a backup, a diff, and the way to bulk import.
Curation is not written there any more. The method below is unchanged; only where the work goes
changed. `docs/contracts/curation.md` is the dossier contract, field by field,
`docs/contracts/knowledge-writes.md` the write path and its gates, `docs/contracts/dossier-export.md`
the export. Read the section for a field before writing it, not the whole file.

## Where each change goes

| Change | Path | Who |
|---|---|---|
| A new fact that stands alone (a claim with its quotes and sources) | proposed through the API: `tools/curation/propose.py`, or MCP `propose_fact` for an agent on the MCP server | the curator |
| Structure: picture placements and focal boxes, a stage's `after` or `whyClaimId`, native names, reactions, botanical names, the GI record, glossary, conflicts, open questions, and the facts that structure cites | a bulk import: a new dossier version in git, imported on deploy | the lead commits it |
| A new craft's first dossier | a bulk import | the lead commits it |
| Reading what the database holds | the export, `export_dossiers --diff` (needs the database); the public facts, MCP `get_facts` | the lead; anyone |

The API takes facts only, about a craft or a category; it has no write for structure yet. A fact
that structure cites travels with that structure in the bulk import, because a stage's why or a
picture's claims name dossier claim ids.

## The bar (Kutch Ajrakh, version 3)

`Kutch-Ajrakh.json` is the exemplar. Read it by field, never whole (it is large):
`python -I -c "import json;d=json.load(open('backend/app/data/curation/Kutch-Ajrakh.json',encoding='utf-8'));print(json.dumps(d['pictures'][:3],ensure_ascii=False,indent=1))"`

A finished craft page has:

| Part | Ajrakh | Bar for every craft |
|---|---|---|
| Pictures | 10, all placed | 8 or more where open-licence pictures exist, at most 16, every one placed |
| Masthead | 1, with focal box | exactly 1 `MASTHEAD`, with `focal` and `width`/`height` |
| Chapters with pictures | glance, made, chem, why, history, people | 4 or more; an `OPENER` per chapter where a fitting picture exists |
| Stage pictures | `STAGE` placements on key stages | the stages a reader would want to see |
| Material pictures | `MATERIAL` placements, `standIn` when not this craft | key dyes, ores, clays, fibres |
| Stage `after` | 8 of 14 | every stage whose result a source describes (text plus up to 3 colours) |
| Stage `whyClaimId` | 11 of 14 | two thirds of stages or more |
| Native names | Sindhi script and Latin | 1 or more, in the craft's own script where a source gives it |
| Reactions | 2, with reactants and products | every reaction a source states, formulas only as quoted |
| Botanical names | on plant materials | every plant material |
| GI record | full | every GI-registered craft (never a family or category) |
| Conflicts, open questions | recorded | every disagreement found; never settled |

A category page has no stages, native names or GI record; it has pictures placed the same way,
`subCategories` on sentences and questions, and the family's reactions.

## Start from the export, in a working copy

Copy the craft's dossier from `backend/app/data/curation` into your scratchpad as the working
dossier, under the same file name (a category's inside a `categories` folder there), and work only
on that copy. Never edit the dossier in git by hand: it is the export, and the lead refreshes it.
When the lead says the git copy is behind the database, ask for a fresh export instead.

## See the gaps first

`python -I .claude/skills/kalavigyan-craft-pages/scripts/gaps.py <working dossier>` prints the
dossier's counts and what is missing against the bar (`--json` for machine output). Run it before
and after; the after run goes in the report. A gap stays a gap only when you searched and found no
source: add what you searched to `searched`.

## Method, cheapest first

1. **Use what the dossier already holds.** Place every existing picture (`placement`, `focal`,
   `width`/`height` from `fetch.py --picture`). Set `after` and `whyClaimId` from claims already
   in the dossier where their quotes support them (the rules in the contract, "Process stages").
   Native names and botanical names often already sit in a quote. No new source is needed for
   any of this. It is structure: it goes in through a bulk import.
2. **Then fill the remaining gaps from new sources**, open sources only (the rubric in the
   contract): pictures from Wikimedia Commons with an open licence (search Commons for the craft,
   its centre, its materials and stages; `fetch.py --picture` gives url, size, author, licence);
   native names from a source that says the craft is called that; reactions only as a source
   states them; new facts as claims with verbatim quotes.
3. **Verify and check** the working dossier (commands below). Fix every problem they report.
   Never edit `index.json`.
4. **Propose the facts that stand alone**: `propose.py --dry-run` first, then the real run. Each
   fact comes back `PUBLISHED`, `WAITING` (for a Professor or Admin) or `REFUSED` at a gate with
   its reasons. A refused fact is fixed from its sources or dropped, never reworded past its
   quotes to slip a gate. The receipt beside the working dossier keeps a fact from being sent
   twice.
5. **Hand the structure to the lead** as the working dossier with its version raised by one, its
   `curatedAt` updated, verified and checked, holding only what the bulk import should store.
6. **Report** in under 150 words: gaps before and after, each fact's outcome, sources added, what
   was searched and not found. No prose summaries of the craft.

Every new claim follows the curator checklist in the contract (a claim says no more than its
quotes, hedges stay, one voice stays one voice, dates quoted, conflicts recorded, places to
district). The verifier rejects a quote that is not verbatim in its source; the API's quote gate
fetches the source again and rejects it the same way.

## Commands

From the repository root with the backend's Python (`backend\.venv\Scripts\python.exe`); `<work>`
is the working dossier in your scratchpad.

| Step | Command |
|---|---|
| gaps | `python -I .claude/skills/kalavigyan-craft-pages/scripts/gaps.py <work>` |
| read a source as the verifier will | `python tools/curation/fetch.py <https url>` |
| a Commons picture's url, size, author, licence | `python tools/curation/fetch.py --picture https://commons.wikimedia.org/wiki/File:<name>` |
| verify quotes (network) | `python tools/curation/verify.py <work>` |
| offline checks | `python tools/curation/check.py <work>` |
| what would be proposed | `python tools/curation/propose.py <work> --dry-run` |
| propose the new facts | `python tools/curation/propose.py <work>`, with `KALAVIGYAN_TOKEN` set; `--only <claim id>` to send some |
| what the database holds against git (the lead) | from `backend`: `python -m app.scripts.export_dossiers --diff --slug <Slug>` |
| refresh the export in git (the lead) | from `backend`: `python -m app.scripts.export_dossiers --out app/data/curation` |
| index (the lead only, once per batch) | `python tools/curation/check.py --write-index` |

`propose.py` sends only the facts the dossier in git (the export, or the file `--stored` names)
does not hold, by claim id or by the same wording. The token is a signed-in session token of a
Researcher or above, set in `KALAVIGYAN_TOKEN` by the person running the session; never print
it, write it to a file or put it on a command line. The address, `KALAVIGYAN_API` or `--api`, is
the API origin (`PUBLIC_API_URL` in `docs/RUNBOOK.md`), not the site: the site refuses a write
that does not come from its own pages.

## Agents on the MCP server

An agent that reaches KalaVigyan through its MCP server, not this repository, follows the same
method with the server's tools: `get_facts` to read what the craft holds before researching,
`propose_fact` (scope `contribute`) with the same proposal a claim makes (subject, field,
statement, up to 5 sources with up to 6 verbatim quotes each), and `list_open_work` and
`claim_task` to take a gap. Its facts pass the same gates.

## Cost rules (owner, 2026-11-18: a whole plan was spent on agents that ran too long)

- **One dossier per agent.** Never two dossiers in one agent, never two agents on one dossier.
- **Sonnet, not Opus**, for deepening; the verifier, the checker and the gates are the judges, so
  no critic or judge agents.
- **Stop at about 60 turns.** Write what is done, run verify and check, propose what stands alone,
  report the rest as open.
- **Read narrowly**: one field of the exemplar, one contract section, one source page at a time.
  Never read the whole dossier into context when a field will do; never open application code.
- **Run nothing else**: no backend or frontend test suites, no builds, no git, no export. The
  lead commits and exports.
- **Never edit code, schemas, other dossiers or the dossiers in git.** A tooling problem is
  reported, not fixed.

## Briefing an agent (the lead)

Give the agent: this skill's name, its working copy of the exported dossier, and the gaps output
for it. Nothing else; the skill carries the method. Run the dossiers of one family together so
their pictures and reactions do not repeat. When the agents are done, the lead commits the
structure versions to `backend/app/data/curation`, runs `check.py --write-index` once, the import
on deploy stores them (decision 0053), and `export_dossiers --diff` against the database then
reports no change for those dossiers.

## The exemplar page

The owner-approved Kutch Ajrakh page is served as built at `/crafts/Kutch-Ajrakh` from
`frontend/public/monographs/kutch-ajrakh/index.html` (decision 0100). Every other craft, family
and category page takes its form from it: the chapter order, the opening, the figures and their
players, the citation clusters and popovers, the media gallery, the coda and the sources. Read
it by section, never whole (it is about 3 MB). Its facts are Ajrakh's and never carry over:
every sentence on another page comes from that craft's own dossier and stored claims. The
scripts that built it are archived in `docs/design/monograph-build.zip` (`build.py` reads the
boards and writes the page; `ship_monograph.py` copies a rebuilt page into `frontend/public`).
Generalising them into one template for every craft is recorded in `docs/TECH_DEBT.md`.

## The page itself

The dossier is half the job; the page built from it is the other half.
`references/page-checklist.md` holds 22 general rules for every craft, family, category and
answer page: the first minute, true counts, no repetition, complete at rest, layout, and
science correctness. Before building a page, derive its three lists from its own dossier:
mechanisms, ambiguous terms and the signature fact. The rules apply through those lists, so they
carry to any craft. One critic scores each built page against the checklist; fix to 9 or above.
An owner-approved page is served as built (decision 0100).

## Order

Minister-facing first: the GI crafts with the most visual stages (Bidriware, Blue Pottery of
Jaipur, Kutch Bandhani, Machilipatnam Kalamkari, Madhubani, Orissa Pattachitra, Bastar Dhokra,
Channapatna), then the rest of the crafts, then the nine categories. The three with no pictures
(Bareilly Cane Bamboo, Sanganeri, Varanasi Soft Stone Jali) need step 2 first.
