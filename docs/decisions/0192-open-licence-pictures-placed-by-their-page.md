# 0192. An agent places open-licence pictures by their page, and the server reads their licence and credit

A contributor's agent gives `give_pictures` the page of an open-licence picture on Wikimedia
Commons, Openverse or Flickr, with the facts it illustrates, a caption written from them and its
place on the page. The server, never the agent, reads the picture's licence, author, title and
file from the source's own record, takes only public domain, CC0, CC BY and CC BY-SA, screens the
file as it screens every contributed picture, files it for review by trust tier with its licence
evidence, credits it in the design's form linked to its page wherever it is shown, and returns a
thumbnail so the agent sees what it placed.

Date: 2026-11-24. Status: accepted (the owner, after the Sanganeri Hand Block Printing page was
built over MCP with an empty top because its agent could not add the open-licence photos it had
found: "add open-sourced pictures on its own, with credits"). It amends
[decision 0104](0104-image-contributions-intake.md) (every contribution was declared by a person)
and [decision 0109](0109-image-formats-and-screens.md) (pictures from the chat). The contracts are
`docs/contracts/image-contributions.md` (Open-licence pictures), `docs/contracts/mcp-ask-and-upload.md`
(`give_pictures`), `docs/contracts/craft-page.md` (Contributed pictures) and
`docs/contracts/knowledge-api.md` (Pictures); the rules an agent follows are in the sources
reference and the page checklist (rules 2, 7 and 14).

| For | Read |
|---|---|
| Contributed pictures: declared, private until approved | [decision 0104](0104-image-contributions-intake.md) |
| The formats, the screens and pictures from the chat | [decision 0109](0109-image-formats-and-screens.md) |
| Room for the page-quality tools | [decision 0191](0191-room-for-the-page-quality-tools.md) |
| Open licences and how they are read | [decision 0013](0013-review-fixes-quotes-licences-scope.md), [decision 0139](0139-sources-and-providers-reach-outside-services-once.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **The agent could not place what it found.** The Sanganeri agent found good open pictures ("Fabric
  drying" and "Workshop wide shot" by CTC Sanganer Official, CC BY 4.0; Ketayun Katz's "Printing
  with Hand Carved Block", CC BY-SA 4.0; nevil zaveri's "on the drying rack, sanganer", CC BY 2.0
  on Flickr) through `search_sources`, but `give_pictures` took only a person's own pictures under
  their declaration, the prompts said a curator places Commons pictures through the dossier
  import, and it could not open the images, only read their titles. The page's top stayed empty.
- **The pieces existed.** Answers already read Commons `extmetadata` and Openverse records, keep
  only open licences with a named author and credit them; the picture fetcher, the intake, the
  repeat and vision screens, the review queue and the trust tiers already guard contributed
  pictures; the generated page already draws a contributed picture as a plate.
- **Flickr has no key here.** Openverse indexes Flickr's CC pictures but cannot be asked for one
  by its Flickr id, and no Flickr API key is in the settings. Flickr's own oEmbed answers without a
  key with the photo's licence by name, address and number, its author's name, its page and file
  (seen on 2026-11-24 for photo 339988080: "CC BY 2.0", licence 4, `.../licenses/by/2.0/`).

## Decision

1. **`give_pictures` takes a page, not a new tool.** A picture may come as `page_url` with its
   `claim_ids` (at least one), `caption`, `alt_text` and target (`slot`, `stage_id`, `material_id`,
   `task_key`, or none) and no declaration or prompt. A new tool would have had to be taught by the
   contributor skill in the same change, which this lane does not edit; the tool's input grew, not
   the list (decision 0191's budget holds it).
2. **The source's own record decides.** `research/open_pictures.open_link` reads a Commons file
   page (also the mobile host, `index.php?title=` and the upload address), an Openverse image or
   API record, and a Flickr photo page or `flic.kr` short link (base 58). `sources/images/open_picture_pages`
   asks Commons for `imageinfo` with `extmetadata` and its 1920 px rendering (the widest the site
   draws, so a large TIFF or an SVG is screened as the raster readers see), Openverse for the
   image's record, and Flickr's oEmbed. An Openverse record of a Commons or Flickr picture is read
   from that site, so the credit names where the picture lives and the licence is the current one.
3. **Only four licence families, refused by name.** Public domain (with the mark and PDDL), CC0,
   CC BY and CC BY-SA of any version, by name or deed address (`open_licence`, unchanged); NC, ND
   or all rights reserved in either the name or the address refuses the picture saying which
   (`licences.licence_restriction`), anything else names its licence, and a missing licence says
   so. A picture whose author is missing, empty once hidden direction and control marks are
   removed, or a placeholder is refused. The licence is judged before the author, and both before
   any file is read.
4. **The same screens, and no repeats on the page.** A picture whose page or file the craft's
   curated pictures or its live open-licence pictures already hold is refused; then the file goes
   through the picture fetcher and every screen of a contributed picture, under origin
   `OPEN_LICENCE` (so a file marked AI-made is refused), and the same picture twice in a call is
   refused (`image_screens.same_picture`, moved there from the chat path).
5. **Filed as an open-licence contribution.** A new origin `OPEN_LICENCE`, which no person may
   declare, and an `OpenPicture` row per contribution with the evidence (site, page, original file,
   the record read, title, author, licence and its address, credit, original size, when read);
   migration `0102_open_pictures`. No `PictureDeclaration`; `termsVersion`
   `open-licence-2026-11-24` and `rightsConfirmedAt` the moment the licence was read. It waits for
   an Admin, or is approved at once for a Professor or above whose screen is `CLEAR`, as every
   contributed picture.
6. **One credit line, linked.** `photo_credit` is the one home of "Photo: author, licence, via
   site" (the pictures search, the curated plates and the open plates use it); Openverse pictures
   from elsewhere say "via Openverse from <site>". A plate's credit unit is "Photo: " and a link to
   the picture's page, for curated plates too, as the approved Kutch Ajrakh page draws them. A
   Commons picture is drawn from its Commons original at the standard widths (`commonsThumb`), any
   other from its kept copy at its own size; the craft page JSON carries `sourceUrl`.
7. **The agent sees what it placed.** Each accepted raster comes back as image content, a JPEG of
   at most 320 px a side after the line "Picture <n>: <credit>", with its `openSource` and its
   plate's label for a draft's layout; each refused one says why.
8. **The prompts and references teach it.** The `curate_page` and `give_picture` prompts send open
   pictures to `give_pictures` by page; the sources reference and checklist rules 2, 7 and 14 say
   how; the review queue and the contributor's own list show the evidence and the credit.

## Consequences

- An agent can fill a page's masthead, stages and chapters with open pictures in one call and see
  them before proposing; an Admin decides each with its licence evidence in front of them.
- The site now copies an open picture's file into the media bucket (Commons' 1920 px rendering or
  the original elsewhere) for review and, outside Commons, for serving; a Commons picture is still
  drawn from Commons, so a later new version of the file there is drawn unscreened, as a curated
  Commons picture is today.
- Flickr is reached from the API for the first time (`www.flickr.com/services/oembed/`, anonymous).
  A Flickr API key is not needed; if Flickr stops answering, Flickr pictures are refused saying
  Flickr could not be read, and Openverse's Flickr records can no longer be resolved either.
- Open pictures stay out of the dossier export, like every contributed picture; a curated picture's
  focal box and stand-in note still enter by the dossier route.
- The release before this one reads and writes every table (its models map `origin` as text), but
  its picture views refuse an `OPEN_LICENCE` row's origin; such rows exist only once this release
  has run, a rollback's downgrade deletes them, and the web accepts the new origin and `openSource`
  in the same change.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-24; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by `backend/tests/research/test_open_pictures.py`,
`backend/tests/sources/test_open_picture_pages.py`, `backend/tests/mcp/test_give_open_pictures.py`,
`backend/tests/db/test_open_pictures_db.py`, `backend/tests/curation/test_contributed_plates.py`,
`backend/tests/test_open_pictures_migration.py` and `frontend/e2e/image-contributions-unit.spec.ts`.
