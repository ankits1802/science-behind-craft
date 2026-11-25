# 0224. A section draws its kit figure first, and a kit figure takes none of the answer's explainers

Each section of an answer tries every one of its concepts against the kit before it takes one for a
generated explainer, and draws the first that composes. A drawn figure costs no model call, so it no
longer counts against the answer's generated explainers (one at Basic depth, two at Detailed, three
at Expert); a section that draws one asks the model for nothing.

Date: 2026-11-25. Status: accepted (the lead, on the measured answer run of release 8ac83675). It
amends [decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md)
(an answer draws its own kit figure). The contract is `docs/contracts/explainer.md` (Kit figures,
Composed, no model).

| For | Read |
|---|---|
| The kit figure it amends | [decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md) |
| Why model calls may not rise | [decision 0165](0165-answers-counted-as-settled-asked-as-asked.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- On release 12607d72 the answer to "how does the indigo cloth turn blue" (run 45565723558) drew the
  vat's kit figure, "Cloth drawn green in the vat, then blue". On release 8ac83675 the same question
  (run 45632414175, answer b5222670) drew none, although it cited the same quote, "At first bright
  green, the cloth rapidly becomes blue as oxygen meets the dye particles on the fibres." Nothing in
  the kit figure's path changed between the two releases; the answer was written differently.
- `SimulationBuilder.build` took, for each section, only the first concept its sentences name, and
  asked the kit for a figure of that concept alone. A kit figure also took one of the answer's
  generated explainers (`AnswerConcepts.take`). So a vat concept named after another concept in its
  section, or in a section built after the answer's explainers were spent, drew nothing, and a figure
  drawn early spent an explainer a later section could have used.

## Decision

1. **The kit first.** Before a section takes a concept for a generated explainer, each of its
   concepts in order is tried against the kit (`science/kit_figures.concept_kit_figure`); the first
   that composes is drawn (`AnswerConcepts.draw`) and is the section's figure. The section's other
   concepts are pictured as before.
2. **A figure takes no explainer.** A drawn concept is kept apart from the answer's generated
   explainers, so the limit counts only figures the model writes. A concept drawn once is never built
   or pictured again in that answer.
3. **No model call is added.** A section that draws a figure asks the model for nothing, as before;
   a section that would have drawn nothing under the old order now may draw a figure instead of a
   generated explainer, which saves its call.

## Consequences

- An answer may show more kit figures than before (one per section whose concepts compose), never
  more generated explainers, and never more model calls than decision 0165 allows.
- Tested in `backend/tests/simulations/test_answer_kit_figure.py`: a section draws its figure after
  the answer's explainers are spent; a figure leaves the answer's explainer to another section; a
  concept is drawn once and never also built or pictured.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
