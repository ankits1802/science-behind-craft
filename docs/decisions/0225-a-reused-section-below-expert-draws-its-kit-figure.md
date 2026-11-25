# 0225. A reused section below Expert draws its kit figure

A section an answer reuses from stored pieces draws its kit figure at every depth. Below Expert it
still asks the model for no generated explainer, as decision 0090 chose; it runs only the part of
the explainer's builder that composes a figure from the kit, which calls no model.

Date: 2026-11-25. Status: accepted (the lead, on the measured answer run of release f0f965b7). It
amends [decision 0090](0090-reused-and-curated-sections-enriched.md) (a reused section enriched like
a researched one) and [decision 0224](0224-a-section-draws-its-kit-figure-first-and-it-takes-none-of-the-answer-s-explainers.md)
(the kit figure first). The contract is `docs/contracts/explainer.md` (Builders on reuse; Kit
figures, Composed, no model).

| For | Read |
|---|---|
| The reuse depths it amends | [decision 0090](0090-reused-and-curated-sections-enriched.md) |
| The kit figure's order | [decision 0224](0224-a-section-draws-its-kit-figure-first-and-it-takes-none-of-the-answer-s-explainers.md) |
| The kit figure itself | [decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- On release f0f965b7 the four-question answer run (45666058092) scored rubric 0.978 and judge
  0.83, but its indigo answer (9b6cbe82, "Why does Ajrakh cloth turn blue only after it leaves the
  indigo vat?") drew no kit figure, although it cites "At first bright green, the cloth rapidly
  becomes blue as oxygen meets the dye particles on the fibres."
- The answer's builder record (`Answer.plan.builds`) shows why: no section ran the `simulation`
  builder, nor `expert_view`, and the supply map, region story and a material card came from storage.
  The evaluation asks the same questions every run, so their sections are reused, and decision 0090
  runs the `simulation` builder on reuse only at Expert (`BuilderEntry.reused_from`), to keep the
  longest model call out of a reused Detailed or Basic answer. The kit figure is drawn by that
  builder (decision 0201), so a reused section below Expert never drew one. The indigo answer of
  release 8ac83675 (b5222670) shows the same record; decision 0224's reading of it, that the answer
  was written differently, missed this.
- A kit figure is never stored as a piece (`UNSTORED_BLOCK_KINDS`), so a reused section can never
  show one from storage either.

## Decision

1. **Below its reuse depth, a builder that draws still draws.** `BlockBuilders.for_reuse` keeps an
   entry that `draws` a kind below its `reused_from` depth when its builder offers a drawing
   (`builder_interface.DrawingBuilder.drawing`), and runs that drawing in the builder's place. At or
   above the depth the whole builder runs, as before; an entry whose kind the section already shows
   runs neither.
2. **The explainer's drawing is the kit figure alone.** `SimulationBuilder.drawing()` returns
   `KitDrawing`, whose build composes the section's first concept that the kit can draw, by the
   same order and the same answer-wide record as the whole builder (`AnswerConcepts.draw`), and
   returns it with no pictures and no model call. A concept drawn once is not drawn again in that
   answer.
3. **No model call is added.** A reused answer below Expert asks the model for exactly what it asked
   before.

## Consequences

- A reused Detailed or Basic answer whose sections cite a quoted change of colour shows the kit
  figure that a freshly researched one shows. The answer's cost does not change.
- Tested in `backend/tests/answering/test_reuse_enrichment.py` (below Expert a reused section runs
  the explainer builder's drawing, at Expert the whole builder, and neither when it shows the kind)
  and `backend/tests/simulations/test_answer_kit_figure.py` (the drawing draws the vat figure with no
  model call, draws nothing where no concept composes, and never draws one concept twice).

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
