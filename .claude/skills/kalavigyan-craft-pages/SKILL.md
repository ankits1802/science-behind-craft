---
name: kalavigyan-craft-pages
description: How to make or deepen a KalaVigyan craft, family or category page's content (the curated dossier in backend/app/data/curation) to the Kutch Ajrakh bar - pictures placed in chapters, the masthead, each stage's colour after and its why, native names, reactions, botanical names, GI record - cheaply, one dossier per agent, with the verifier and checker as the judges. Load it before creating, deepening, fixing or reviewing any dossier or check file, before any work on a craft page's or category page's content, and before briefing an agent to do so.
---

# KalaVigyan craft and category pages

A craft page is drawn from one dossier: `backend/app/data/curation/<CraftSlug>.json` (a category:
`categories/<CategorySlug>.json`) and its `.check.json`. The page code is done; content is what
makes a page magnificent. `docs/contracts/curation.md` is the contract, field by field; this skill
is the method and the bar. Read the contract section for a field before writing it, not the whole
file.

## The bar (Kutch Ajrakh, version 2)

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

## See the gaps first

`python -I .claude/skills/kalavigyan-craft-pages/scripts/gaps.py [<dossier> ...]` prints each
dossier's counts and what is missing against the bar (`--json` for machine output). Run it before
and after; the after run goes in the report. A gap stays a gap only when you searched and found no
source: add what you searched to `searched`.

## Method, cheapest first

1. **Use what the dossier already holds.** Place every existing picture (`placement`, `focal`,
   `width`/`height` from `fetch.py --picture`). Set `after` and `whyClaimId` from claims already
   in the dossier where their quotes support them (the rules in the contract, "Process stages").
   Native names and botanical names often already sit in a quote. No new source is needed for
   any of this.
2. **Then fill the remaining gaps from new sources**, open sources only (the rubric in the
   contract): pictures from Wikimedia Commons with an open licence (search Commons for the craft,
   its centre, its materials and stages; `fetch.py --picture` gives url, size, author, licence);
   native names from a source that says the craft is called that; reactions only as a source
   states them.
3. **Verify and check** (commands below). Fix every problem they report. Never edit `index.json`.
4. **Report** in under 150 words: gaps before and after, sources added, what was searched and not
   found. No prose summaries of the craft.

Every new claim follows the curator checklist in the contract (a claim says no more than its
quotes, hedges stay, one voice stays one voice, dates quoted, conflicts recorded, places to
district). The verifier rejects a quote that is not verbatim in its source.

## Commands

From the repository root with the backend's Python (`backend\.venv\Scripts\python.exe`):

| Step | Command |
|---|---|
| gaps | `python -I .claude/skills/kalavigyan-craft-pages/scripts/gaps.py backend/app/data/curation/<Slug>.json` |
| read a source as the verifier will | `python tools/curation/fetch.py <https url>` |
| a Commons picture's url, size, author, licence | `python tools/curation/fetch.py --picture https://commons.wikimedia.org/wiki/File:<name>` |
| verify quotes (network) | `python tools/curation/verify.py backend/app/data/curation/<Slug>.json` |
| offline checks | `python tools/curation/check.py backend/app/data/curation/<Slug>.json` |
| index (the lead only, once per batch) | `python tools/curation/check.py --write-index` |

## Cost rules (owner, 2026-11-18: a whole plan was spent on agents that ran too long)

- **One dossier per agent.** Never two dossiers in one agent, never two agents on one dossier.
- **Sonnet, not Opus**, for deepening; the verifier and checker are the judges, so no critic or
  judge agents.
- **Stop at about 60 turns.** Write what is done, run verify and check, report the rest as open.
- **Read narrowly**: one field of the exemplar, one contract section, one source page at a time.
  Never read the whole dossier into context when a field will do; never open application code.
- **Run nothing else**: no backend or frontend test suites, no builds, no git. The lead commits.
- **Never edit code, schemas or other dossiers.** A tooling problem is reported, not fixed.

## Briefing an agent (the lead)

Give the agent: this skill's name, the dossier path, and the gaps output for it. Nothing else;
the skill carries the method. Run the dossiers of one family together so their pictures and
reactions do not repeat, the lead runs `check.py --write-index` once, and the import on deploy
does the rest (decision 0053).

## Order

Minister-facing first: the GI crafts with the most visual stages (Bidriware, Blue Pottery of
Jaipur, Kutch Bandhani, Machilipatnam Kalamkari, Madhubani, Orissa Pattachitra, Bastar Dhokra,
Channapatna), then the rest of the crafts, then the nine categories. The three with no pictures
(Bareilly Cane Bamboo, Sanganeri, Varanasi Soft Stone Jali) need step 2 first.
