# 0226. A section draws a kit figure only of a change its own prose states

A section draws a kit figure only when one of its prose sentences cites a claim the figure cites,
so the figure illustrates what the section says. A concept that only another block of the section
names (a reaction player, a zoom story, a ladder, a material card) no longer brings its figure.

Date: 2026-11-26. Status: accepted (the lead, on the measured answer run of release 2ad6b820). It
amends [decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md)
(an answer draws its own kit figure) and [decision 0225](0225-a-reused-section-below-expert-draws-its-kit-figure.md)
(a reused section below Expert draws its kit figure). The contract is `docs/contracts/explainer.md`
(Kit figures, Composed, no model).

| For | Read |
|---|---|
| The kit figure | [decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md) |
| The kit figure first | [decision 0224](0224-a-section-draws-its-kit-figure-first-and-it-takes-none-of-the-answer-s-explainers.md) |
| The reused section's drawing | [decision 0225](0225-a-reused-section-below-expert-draws-its-kit-figure.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- After decision 0225 the four-question answer run on release 2ad6b820 (45681947685: rubric 0.978,
  judge 0.82, $0.29) drew the indigo answer's vat figure, "Green to blue", in its section
  "Colourless in the vat, blue in the air". It also drew the same figure in three sections that are
  not about the vat: "From the Suran's dam to a new village" (Geography), "How madder root dye grips
  the alum mordant" (Chemistry) and "Soaked in castor oil and dung, then myrobalan" (Process), one
  in each of the other three answers.
- A section's concepts (`science/mechanisms.section_concepts`) are read from every cited sentence of
  the blocks it is given. A researched section gives the builder its prose and ladder; a reused one
  gives every placed block, and its stored reaction players, zoom stories and material cards name the
  vat in sections whose prose never states its change of colour.

## Decision

1. **The figure illustrates the section's own words.** `simulation_builder._kit_figure` draws a
   concept's figure only when a claim the figure cites is cited by a sentence of the section's prose
   blocks (`kind == "prose"`). Otherwise the concept is skipped and stays free for a later section.
2. **One rule for both paths.** It holds for the whole builder of a researched section and for the
   drawing a reused section runs below Expert (`KitDrawing`).

## Consequences

- A kit figure appears only beside prose that states the change it draws; an answer may show fewer
  figures, never one beside a section about something else. No model call changes.
- Tested in `backend/tests/simulations/test_answer_kit_figure.py`: a section whose only mention of
  the vat is in another block draws no figure, and the concept is then drawn by the section whose
  prose states it.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
