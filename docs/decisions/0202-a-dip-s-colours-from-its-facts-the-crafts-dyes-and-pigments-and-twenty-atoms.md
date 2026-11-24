# 0202. A dip player takes its colours from the substances its stages name, the crafts' dyes and pigments are recorded from their facts, and a molecule draws twenty elements

A craft's composed dip player no longer waits for the team to record a colour with each fact: each
bath stage's colour after is drawn as the depicted material of the dye, mordant or resist that gives
it, through the colour key's one substance-to-token mapping, and a colour no token depicts is
outlined and named in words. The dyes and pigments the crafts' facts describe gain their specimen
records, each with the fact that quotes its colour, and the molecule kit colours the twenty elements
the crafts' held compounds contain, in all four themes, so any held compound's conformer turns.

Date: 2026-11-24. Status: accepted (the lead's page-quality brief of 2026-11-24, lane `colours`; the
owner judged the Sanganeri Hand Block Printing page far below Kutch Ajrakh's). It amends
[decision 0198](0198-a-craft-s-own-interactives-composed-and-played-on-every-page.md), items 2 (the
dip player and the molecule) and 3 (what `missing` names), and
[decision 0197](0197-a-colour-key-from-cited-colours-and-a-masthead-that-names-the-craft-once.md),
item 3 (the tokens the key maps). The contracts are `docs/contracts/component-specs-science.md`
(`molecule_3d`, Composed from a craft's own facts) and `docs/contracts/open-work.md` (MCP); the
design is `.claude/skills/kalavigyan-design/references/SYSTEM.md` 2.5 and 2.5a.

| For | Read |
|---|---|
| The composer, its kinds and what it names when a craft holds too little | [decision 0198](0198-a-craft-s-own-interactives-composed-and-played-on-every-page.md) |
| The colour key and its substance-to-token mapping | [decision 0197](0197-a-colour-key-from-cited-colours-and-a-masthead-that-names-the-craft-once.md) |
| The specimen tokens, their records and their frame | [decision 0092](0092-design-system.md), and SYSTEM.md 2.5 |
| The figure kit, whose parts take the same depicted materials | [decision 0199](0199-a-kit-of-figure-parts-and-hand-drawn-art-held-to-the-bar.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **A dip waited for a record nobody makes.** `compose_dip` drew a stage only in the token the team
  recorded with the fact stating its colour after (`stated_specimens`); every craft but Kutch
  Ajrakh, Bidriware, Jaipur's blue pottery and Bastar Dhokra has no such record, so their stages
  named red and yellow and composed nothing. The colour key (decision 0197) already maps a colour a
  fact names to the token of the substance that gives it, from the same stage materials.
- **The crafts' facts describe colours no token depicts.** Read from the dossiers on 2026-11-24, the
  dyes, mordants, resists and pigments with no `--dye-*` token are, among others: turmeric and
  pomegranate rind (Bagru, Sanganeri, Bagh, Kutch Ajrakh, Madhubani), the al or aal root and chay
  root reds, kali mitti (Dabu, Bagru), syahi and kasim iron blacks (Bagru, Dabu, Sanganeri,
  Machilipatnam), alum and begar, beeswax and paraffin wax, Pattachitra's cinnabar, red ochre,
  orpiment, lamp black and conch white, Madhubani's flower and leaf colours, lac dye, lithopone and
  the oxides of Jaipur's glazes; the flagships add the clays, the stones, wax and cast metal. Only
  some have a fact whose quote states the material's colour.
- **The molecule kit coloured four elements.** The kit's `.bx-chem` rule gives carbon, hydrogen,
  nitrogen and oxygen; the crafts' held compounds (the dossiers' PubChem materials) also hold iron,
  sulphur, copper, zinc, silver, gold, lead, chlorine, potassium, sodium, calcium, titanium and
  mercury, and their facts name alum's aluminium, chrome tanning's chromium and Sankheda's tin. No
  generator check covered an atom colour.

## Decision

1. **A dip's colour from its facts.** `compose_dip` takes each bath stage's colour after as the
   recorded token when one exists, else the first colour its after names that a token depicts from
   the names of the stage's dyes, mordants and resists (name, botanical name and local names),
   through `research/colour_key.first_depicted`, `agent_materials` and `agent_names`, which the
   colour key's stage colours use too (one home). A colour no token depicts is drawn as the outlined
   piece (the reaction scene's undepicted swatch, `compose_scene.piece_drawing(None)`) and named in
   words in the phase's text when its after does not say it, and `leftOut` asks for its specimen
   record. A stage whose after names no colour is left out with its reason; with fewer than two
   stages left, that reason is in `missing`. A dip none of whose colours a token depicts composes
   nothing. `HeldMaterial` carries the role, local names and botanical name the curated page holds.
2. **The mapping grows with the records.** `DEPICTED_COLOURS` maps syahi and kasim to `kut` (iron
   pastes black on tannin, as the facts say), and the new records below to their colour words.
3. **Eight specimens recorded from the crafts' facts** (`tools/design/materials.json`), each with
   its craft's material and the fact whose quote states its colour: `--dye-turmeric` (Bagru M16,
   C088, "Yellow ... Haldi"), `--dye-pomegranate` (Bagru M17, C088, "Light yellow ... Naspal"),
   `--dye-kali-mitti` (Dabu M01, C007 and C077, "black clay"), `--dye-cinnabar` (Pattachitra M05,
   C083, "vermillion red"), `--dye-red-ochre` (M06, C083, "brick red"), `--dye-orpiment` (M07, C085
   and C095, "light, vivid yellow ... inclined towards orange"), `--dye-lamp-black` (M08, C055) and
   `--dye-conch-white` (M04, C081). The rest of the list above waits: their facts name a use, not a
   colour (aal, chay, beeswax, alum), or name a colour of a mixture or a glaze, not of the material.
4. **The molecule kit is generated.** `tools/design/system.json` gains `molecule`: the stage ground
   (`sunk`), `--mol-bond`, `--mol-letter` and `--mol-edge`, and twenty atoms, each with its symbol,
   name, radius, letter and a colour in each of four themes. Carbon, hydrogen, nitrogen and oxygen
   keep the approved kit's values (high contrast keeps each theme's, as the kit does); the others
   are drawn at half their covalent radius (Cordero and others 2008), at most 0.55. The generator
   writes `--atom-*` and the kit tokens into every theme block, the table into `tokens.json`, and
   `backend/app/research/molecule_atoms.py` for the server, and refuses an atom whose edge reads
   below 3:1 on the stage, a lettered atom below 4.5:1 under its letter, two atoms within 5 delta E,
   an atom within 3 of a reserved colour, or an interactive blue.
5. **The renderer's element table.** `science/molecule_elements` reads the generated table; the
   server's drawing takes its radii and letters from it (every atom but C and H lettered), the
   conformer reader its drawn elements and a margin of the largest atom's radius and 0.04 when that
   passes 0.42, the composer its words and key labels ("Iron, Fe"), the kit defs a gradient
   `ag-<Symbol>` for every atom (`document_kit_defs.atom_defs`, drawn as Ajrakh's are), and the kit's
   `RAD` the same radii. Delivery accepts a key's `--atom-*` swatch only for an atom the table holds.

## Consequences

- A craft whose stages' afters name colours and whose dyes are named by their substance composes
  its dip player on its next `compose_component` call; the Skill text teaches agents to propose
  the after with its colours and the stage's materials by substance.
- The colour key draws turmeric, pomegranate rind and the Pattachitra pigments as swatches where it
  named them in words; its tests now name marigold as the dye no token depicts.
- A compound of other elements (silicon, arsenic, cobalt, boron) still waits for its atom colour,
  named in `missing`; PubChem computes no 3D conformer for most metal salts, so a model of one turns
  only where PubChem holds it.
- The flagships' Missing lines (`flagships.md`, `research/open_work_flagship_backlog.py`) still ask
  for the mineral pigments' tokens, which now exist for Pattachitra; the lead updates the backlog
  and its reference together.
- The kit's `.bx-chem` rule keeps its own copy of the four approved atoms and the bond, letter and
  edge, which a test holds equal to the generator's.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-24; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by `backend/tests/compose/`,
`backend/tests/research/test_colour_key.py`, `backend/tests/research/test_kit_defs.py`,
`backend/tests/science/test_molecule_elements.py`, `backend/tests/layouts/test_generated_colour_key.py`,
`tools/tests/test_design_atoms.py`, `tools/tests/test_design_materials.py` and
`frontend/e2e/molecule-atoms-unit.spec.ts`.
