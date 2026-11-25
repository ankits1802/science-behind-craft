# 0208. A reader downloads every craft, family and category page from the page itself, with the pictures it shows and its fixed words in the reader's language

Every craft monograph, Kutch Ajrakh included, and every family and category page offers one
Download menu with a PDF and a Word document. A page export embeds each open-licence picture its
plates show, read at the standard Commons width that fits the paper, caption first and credit after;
a picture that was not read, or whose licence forbids a copy, is given by its description and credit
and the figure says so. The export's own words are reviewed interface words keyed `export.*`. A
family or a category page exports through its own route and the same export services.

Date: 2026-11-25. Status: accepted (the lead's lane `exports-2` of the page-quality round; the owner,
2026-11-25, to build what decision 0206 left). It amends
[decision 0206](0206-every-new-kind-exported-as-its-still-and-read-in-a-page-s-languages.md) (the
four things its Consequences left: no button, pictures by their alt text, English fixed words, craft
pages only) and [decision 0157](0157-translations-read-back-and-reviewed-interface-words.md) (the
keys an interface words file holds gain `export.*`). The contracts are
`docs/contracts/monograph-document.md` (Exports), `docs/contracts/page-layout.md` (Routes),
`docs/contracts/research.md` (Interface words), `docs/contracts/learning.md` and
`docs/contracts/frontend.md`.

| For | Read |
|---|---|
| The export, its builders and its still renderer | [decision 0206](0206-every-new-kind-exported-as-its-still-and-read-in-a-page-s-languages.md) |
| Interface words, their sources and their review | [decision 0157](0157-translations-read-back-and-reviewed-interface-words.md) |
| The picture reads, the bucket and a file made while a picture was unread | [decision 0067](0067-lessons-and-exports.md), [decision 0143](0143-lessons-exports-and-follow-ups-kept-true.md) |
| The open licences | [decision 0192](0192-open-licence-pictures-placed-by-their-page.md) |
| The phone budget the page's JavaScript is held to | [decision 0205](0205-a-page-measured-on-a-slowed-phone-held-to-its-budget-and-heavy-kinds-loaded-near.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **No reader could reach the export.** Decision 0206 built `GET /api/crafts/{slug}/monograph/{fmt}`
  and left the button out: placing one on the approved Kutch Ajrakh page changes what the owner
  approved. The owner asked on 2026-11-25 for the rest to be built and the button placed, for the
  owner to move if they wish.
- **Paper held no picture.** A picture plate was given by `Picture: <alt>` and its credit line. The
  site already reads open pictures for lessons and answer reports (`export_pictures` through
  `picture_files`, Commons and Openverse only, no time limit), and the backend had the Commons
  widths in `source_lookup_pictures` but not the web's `standardWidth` rule. Kutch Ajrakh's ten
  pictures are the site's own crops of Commons files (`/monographs/kutch-ajrakh/img/`, credited
  "…, cropped"), so the Commons original is not the picture the page shows.
- **The fixed words were English in every language.** "Sources", the paper notes, the kind labels,
  "Drawn:", "Given by:", "Key:" and the phrases around a home place, a resting step and a route
  were literals in the builders, and decision 0206's Consequences said they would stay English
  until interface words were sourced for them. No source in the repository gives any of them in
  any language: the Kutch Ajrakh answer panels and the boards hold only the essay's words.
- **Families and categories had no export of their own.** A family page is drawn at `/crafts/{slug}`
  from `/api/crafts/{slug}/monograph`, which falls back to the family's generated document, and a
  category page draws its science from `/api/categories/{slug}/monograph`; `/api/families/{slug}/monograph`
  serves the family's document directly. The lane brief named `/api/families/{slug}/page/{fmt}` and
  asked to follow the routes those pages use now.

## Decision

1. **One Download per page, beside Cite.** `components/monograph/PageDownload` draws the button
   (`learn/DownloadTrigger`, the same button `DownloadMenu` draws) and, the first time it is
   pressed, loads `PageDownloadList`, which hands the page's two items (`lib/pageExport.pageDownloads`:
   PDF and Word document, at the path of the page's kind, slug and language) to `learn/DownloadList`,
   the list `DownloadMenu` now draws too, so there is one menu. On a craft monograph with a cite
   block it is the second action of the block's `ActionGroup`, beside Copy citation. A family or a
   category page has no cite block (`documentCitation` cites crafts only), so `PageDownloadRow` draws
   it alone where the block would be, at the page's end. On Kutch Ajrakh the cite block is a
   fragment of the approved page, so the row is drawn by the shell page after `#kv-main` and before
   the footer, the nearest place the shell draws itself; `#kv-main` is drawn exactly as before.
   The menu's list, its popover and the API client load only when pressed; what every page ships is
   the button and the loader.
2. **Pictures on paper.** Before a file is built, `page_export_pictures.wanted_pictures` takes each
   `picture_plate` and `specimen_plate` the page holds, keeps those whose credit names an open
   licence (`research/licences.open_licence` on the credit's words, so NC, ND, all rights reserved
   and "Contributed to KalaVigyan", which names none, are never copied), and asks for each once:
   a Commons file at the standard width that fits the column (`commons_urls.commons_fitting_width`:
   the PDF's 178 mm column at 150 dpi is 1051 px, so 1280, never wider than the file and the file
   itself when it is under 330 px; `COMMONS_WIDTHS` moved there from `source_lookup_pictures`, with
   `standard_width`, the web's `standardWidth`), and a picture the site serves itself from the
   page's own site. They are read through `picture_files`, whose hosts gain the https host of
   `PUBLIC_WEB_URL`, within 30 s for the page (`export_pictures(..., within=)`, a time limit any
   caller may now give). A figure holds the picture read (JPEG, at most 1600 px a side) under its
   title, its captions first and its credit after as the figure's credit; a picture not read, or
   whose licence forbids a copy, is given by `Picture: <alt>` and its credit, and the figure's note
   says which. A file built while a picture was unread is filed apart and never reused, as lesson
   files are, and the export's edition (`PAGE_EXPORT_EDITION` 2) joins what a file is made from, so
   no file built before this change is served again.
3. **Fixed words through the reviewed interface words.** `page_export_words` is the one home of the
   export's own words, each an `ExportWord(key, english)` with the English the code held
   (`EXPORT_WORDS`): `export.heading` (Sources), `export.note` (the reading note), `export.paperNote`
   (the paper notes), `export.kind` (each kind's label), `export.label` (Drawn, Given by, Swatches,
   Key, Picture), `export.phrase` (this craft's place, as the page opens, drawn in the figure
   `{title}`, `{before}` becomes `{after}`, `{before}` or `{after}`, `{start}` to `{end}`, `{years}`)
   and `export.pictureNote` (the two picture notes). `export_words(language)` draws a word from that
   language's reviewed entry whose English is the code's, and English otherwise, marked
   `w:lang="en"` in Word; each word stands alone, so it is drawn as soon as it is reviewed. No file
   gains an entry: no source gives these words, a translation written here would be invented, and
   only a reader of the language marks one reviewed (decision 0157). The reviewed export words of
   the language join what a file is made from, so a newly reviewed word makes a new file.
4. **Family and category exports beside their pages' routes.** `GET /api/families/{slug}/monograph/{fmt}`
   and `GET /api/categories/{slug}/monograph/{fmt}`, with `lang`, read the document
   `page_documents.subject_document` serves the family and category routes and hand it to
   `page_export_link`, the craft route's own; the file is named `KalaVigyan_Family-Page_…` or
   `KalaVigyan_Category-Page_…`. They sit under the routes that serve those documents, as the craft
   export sits under `/crafts/{slug}/monograph`, rather than at the brief's `/page/{fmt}`, which no
   page reads. The web asks for a page's file by the page's kind, so a family page drawn at
   `/crafts/{slug}` downloads through `/families/{slug}`; the craft route still exports it too.

## Consequences

- Every reader can download every page that has a document; a craft without a monograph has no
  document and no Download.
- Kutch Ajrakh's export holds its ten photographs, read from the site's own host, so production's
  `PUBLIC_WEB_URL` must be the https site the pictures are served from; with any other value they
  are given by their description and credit. Its PDF grows by about the ten JPEGs.
- The web's `exportLinkShape` accepts `docx` (`EXPORT_FORMATS`), which only a page export answers.
- The answer report's kit figure keeps its English "Drawn:" (`kit_diagram_lines` defaults to the
  English words); the answer's own fixed words are not export words.
- Each page's JavaScript grows by the button and its loader only; the phone budget's run on this
  change measured it (Frontend checks, below the recorded limits of `e2e/phone-budget.json`, which
  was not re-recorded).
- A reader of each language can now add and review `export.*` entries; until then every export
  word is English. The register's entry "Interface words in other languages wait for their
  readers" is the lead's to widen to them.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by `backend/tests/exports/test_page_pictures.py`,
`backend/tests/exports/test_export_words.py`, `backend/tests/db/test_page_exports_db.py`,
`backend/tests/sources/test_commons_urls.py`, `backend/tests/learning/test_export_store.py`,
`backend/tests/test_interface_words_data.py`, `backend/tests/public/test_route_inventory.py`,
`frontend/e2e/page-download-unit.spec.ts` and `frontend/e2e/lesson-exports-unit.spec.ts`.
