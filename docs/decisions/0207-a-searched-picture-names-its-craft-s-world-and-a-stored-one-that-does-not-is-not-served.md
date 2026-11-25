# 0207. A searched picture must name its craft's world in its title, and a stored one that does not is no longer served

Besides sharing two content stems with a claim, a picture an image search found must name the
craft's world in its title: the craft's names, its places or its family's picture words. A stored
`TEXT` link of a searched picture that fails that bar is not served, and nothing stored is
deleted. A curator's pick, a field photo and a `VISION` verdict are never held to it.

Date: 2026-11-25. Status: accepted (the lead's page-quality brief of 2026-11-24, lane
picture-relevance). It amends [decision 0034](0034-images-and-terms.md) (choosing pictures by
their relevance to the claim text) and [decision 0166](0166-pictures-terms-and-stored-pieces-kept-true.md)
(a section shows its claims' stored pictures before it searches). The contract is
`docs/contracts/explainer.md` (Pictures and terms as served, Choosing).

| For | Read |
|---|---|
| The relevance rule it amends | [decision 0034](0034-images-and-terms.md) |
| The stored pictures' reuse it amends | [decision 0166](0166-pictures-terms-and-stored-pieces-kept-true.md) |
| Why no model call is added | [decision 0165](0165-answers-counted-as-settled-asked-as-asked.md) |
| The family records the picture words join | [decision 0081](0081-craft-page-contract-v2.md) |
| What is left | `docs/TECH_DEBT.md`: Relevance is by text only |
| Every decision, by group | [README.md](README.md) |

## Context

- **Two shared words were enough.** A picture illustrated the claims whose content stems it
  shared at least two of, the craft's name left out (`research/image_relevance`). The measured
  answer run of 2026-11-25 (Kutch Ajrakh, four questions) showed "Clay Farm, Aura, Lime Avenue -
  geograph.org.uk - 6678543", a Commons photograph of a farm in England, beside the mud resist and
  the lime ("clay" and "lime"); "Lemons and Limes, Fresh Fruit Color" from Flickr beside lime; and
  "Brick House iPhone Background" from Flickr beside the lime of the indigo vat, whose Openverse
  tags hold "block", "lime" and "grout" against the claim's "blocks", "lime" and "ground". The
  judge's note on the first answer named the farm.
- **A wrong picture stayed.** Decision 0166 stores a chosen picture against its claims
  (`MediaRef`, `MediaRefClaim`) and serves it from then on without searching
  (`section_images.stored_items`), so each wrong picture returned in every later answer citing
  those claims.
- **No model may look.** The vision call that would settle it waits on the owner: decision 0165
  keeps each answer's model calls and input tokens at or below their measured level.

## Decision

1. **The craft's world.** `PictureContext` (`research/image_relevance`) is a set of words; a title
   names it when one of the title's content words begins with one of them (`named_in`), so
   "printing" holds "print" and "Kutchi" holds "kutch", while "cottage" does not hold "cotton" nor
   "prince" "print". `picture_context(names, places, family_words, *, ordinary)` makes it from the
   content words (four letters or more, not stop words, `research/quotes.content_words`) of the
   craft's names and places that are not ordinary English words (`data/english_words`, so
   "Dhamadka River (Suran)" gives "dhamadka" and "suran", and "Ajrakh block printing" gives
   "ajrakh"), and from every one of its family's picture words.
2. **Read from the craft's records.** `services/craft_picture_context.craft_picture_context`
   reads, for the slug the ask names: the craft's name, local name and active aliases
   (`craft_resolver.alias_names`); its states of origin and practice, "All India" left out, and
   its locations' labels, district and state names (`craft_resolver.craft_places`, the craft
   index's own reading of a craft's places); and its family (`craft_page_family.family_names`, now
   the one query the craft page and the generated monograph also read). With no craft, or a slug
   that names none, it is every family's picture words, so an answer for any craft still shows
   only pictures of some craft's world.
3. **The family's words are in the family records.** Each of the nine families in
   `data/craft_families.json` (version 3) lists `pictureWords`: the words a picture's title uses
   for that family's world, its materials, tools, products and makers (for textiles: cloth,
   fabric, textile, dyes, dyed, dyeing, dyer, print, block, weave, weaving, woven, loom, thread,
   yarn and the like). Nothing is listed per craft. A word is lower-case, listed once and a content
   word, and none begins another of its family's words (which would add nothing). Colour names
   are left out, "indigo" among them, since a title naming a colour can show anything, and so is a
   word whose likeliest other sense would admit common pictures ("bell", "fired", "straw").
4. **The title alone names the world.** The description is still read for the two shared stems,
   never for the context: an Openverse description is its uploader's tag list, and the brick wall's
   tags hold "block".
5. **Searched pictures.** `choose_images` takes the context and refuses a candidate whose title
   names nothing of it before the stems test, so it is never kept as a `MediaRef`. Both places that
   build a `SectionImagesAsk` pass the craft's slug: the answer's enrichment
   (`section_enrichment`) and the simulation builder's concept pictures (`simulation_builder`).
   `SectionImages` reads the context once per block through its `context` reader. Picture search
   texts still start with the craft's name (`image_search_text`).
6. **Stored pictures, filtered at read.** `stored_items(pictures, context)` drops a `TEXT` link
   of a searched picture whose title names nothing of the craft's world; the row and its links
   stay, so a person can still see what was kept, and a section left with no stored picture
   searches again under the new bar. A link is never dropped when it is `VISION`, or when the
   picture is a curator's pick (`provider` `curation`, `CHOSEN_PICTURE_PROVIDERS`) or a field
   photo from either portal (`designer_portal`, `field_repository`): a person chose or took those
   for the craft. Pictures given through `give_pictures` and approved open pictures are image
   contributions, not `MediaRef` rows, and never reach this bar.
7. **Measured on the run.** `backend/tests/images/test_measured_pictures.py` holds the run's
   pictures in the shapes the answers stored them, against Kutch Ajrakh's world read from its
   register row, aliases, dossier places and family words:

   | Picture | Provider | Now | Why |
   |---|---|---|---|
   | Clay Farm, Aura, Lime Avenue - geograph.org.uk - 6678543 | Commons | refused | clay, farm, aura, lime, avenue, geograph: none is a word of the craft's world |
   | Lemons and Limes, Fresh Fruit Color | Openverse | refused | lemons, limes, fresh, fruit, color |
   | Brick House iPhone Background | Openverse | refused | its title holds none; its tags are not read for the world |
   | Lemon and lime | Commons | refused | a stored pick the answers' recorded payloads show beside the vat's lime |
   | Natural dye and printing materials, among them alum and lime, laid out on an ajrakh cloth | curation | kept | a curator's pick; its title also names ajrakh, printing and cloth |
   | stretch of art, dhamadka kutch | Openverse | kept | Dhamadka, a village of the craft's record, and Kutch, its name |
   | feel the heat, dhamadka kutch | Openverse | kept | the same |
   | Ajrakh Block Printing \| Crafts of Kutch | SearXNG | kept | ajrakh and kutch, and the family's print and block |
   | Cotton textile structure | a search | kept | cotton and textile are the textile family's words |
   | Workers beating the vats at an indigo factory in Allahabad in 1877 | curation | kept | a curator's pick, whatever its words |

   "Cotton textile structure", the micrograph, is kept because the bar asks a picture to be of the
   craft's world, its family included, not of the craft itself: it shows cotton cloth, magnified,
   beside a cotton claim, and only a look at the picture could say it shows no ajrakh. "Workers beating the vats at an indigo factory in Allahabad in 1877" names nothing of
   Kutch Ajrakh's world by its words (indigo is left out as a colour name, Allahabad is not one of
   the craft's places, and none of workers, beating, vats or factory begins a textile word), so a
   search would refuse it; it is kept because a curator chose it, with the stand-in note "An
   indigo factory at Allahabad in 1877, not Kachchh", and the bar never overrides a person's
   choice. The two pictures not in the recorded payloads (the farm and the lemons) are fixtured by
   the titles the run reported.

## Consequences

- An answer adds no model call and no input token (decision 0165). The context costs one small
  read of the craft's records per `images` block. No migration: links are filtered at read.
- A section whose only stored pictures now fail searches the image services again, once per
  answer, until a picture of the craft's world is stored for its claims.
- A picture whose title names the craft's world and shares two words with a claim is still shown
  without being seen, even if it shows another step or another craft of the family; the register
  entry "Relevance is by text only" now says so, and the vision call still waits on the owner.
- A new family, or a family's new kind of work, needs its picture words in `craft_families.json`;
  a family without them fails to load.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/research/test_picture_context.py`, `backend/tests/images/test_picture_world.py`,
`backend/tests/images/test_measured_pictures.py`, `backend/tests/test_craft_families.py` and
`backend/tests/db/test_craft_picture_context_db.py`.
