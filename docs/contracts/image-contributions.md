# Image contributions (decision 0101, item 17; decision 0104)

Pictures that readers with the right to propose knowledge give to a craft: photographs, drawings
and AI-made illustrations. Each is declared, checked on our side, stored privately, and shared on
approval. Approval follows decision 0101, item 12: a Professor's, Admin's or Master Admin's picture
is approved at once; anyone else's waits for an Admin.

## Who may do what

| Action | Capability | Roles |
|---|---|---|
| Declare, upload, list own, withdraw | `PROPOSE_KNOWLEDGE` | Researcher and above |
| Review the queue, approve, reject | `REVIEW_CONTRIBUTIONS` | Admin, Master Admin |

A reviewer never decides their own picture.

## Routes (`/api/contributions/images`)

| Route | Body | Answer |
|---|---|---|
| `POST ""` | `ImageDeclaration` | 201 `ImageContributionView`, status `AWAITING_FILE` |
| `PUT /{id}/file` | the picture's bytes (PNG, JPEG or WebP, at most 10 MB) | `ImageContributionView`, `PENDING` or `APPROVED` |
| `GET /mine` | none | `ImageContributionView[]`, newest first, at most 100 |
| `POST /{id}/withdraw` | none | `ImageContributionView`, `WITHDRAWN`, only while the picture waits for its file or for review; an approved picture stays (409): consent cannot be revoked |
| `GET /review?state=PENDING` | none | `ImageQueue {status, items[]}`, oldest first, at most 100 |
| `POST /review/{id}/approve` | `{note?}` | `ImageContributionView`, `APPROVED`; the picture is shared |
| `POST /review/{id}/reject` | `{note}` (3 to 500 characters) | `ImageContributionView`, `REJECTED` |

Refusals: 404 for a contribution that is not the caller's (or does not exist), 409 for a state
that does not allow the step (a second file, a decided picture, a repeat of a live picture, one's
own picture), 413 over 10 MB, 422 for a declaration or file that fails its checks, 503 when the
media bucket is not configured.

## `ImageDeclaration`

- `craftSlug`; optional `stageId`, which must be one of the craft's stages; `claimIds`, at most
  20, each a fact a signed-out reader is shown.
- `origin`: `PHOTOGRAPH`, `DRAWING` or `AI_GENERATED`.
- An AI-made picture names its `generator` (tool and model, 2 to 120 characters), its `prompt`
  (up to 4,000 characters) and at least one fact it shows. Other origins carry neither.
- `caption` and `altText`, 3 to 300 characters each.
- `rightsConfirmed: true` and `termsVersion: "2026-11-19"`, the declaration's version (its text:
  `docs/legal/image-declaration.md`): the uploader holds the rights to give the picture under the
  contribution terms.

## What the file goes through (`research/image_intake.py`)

- **Type from the bytes:** PNG, JPEG or WebP; anything else is refused.
- **Size:** at most 10 MB; 320 to 8,192 pixels a side.
- **Metadata removed:** PNG text, EXIF and time chunks; JPEG EXIF (except a rebuilt orientation),
  XMP, IPTC, comments and Content Credentials (APP11); WebP EXIF, XMP and C2PA chunks, with the
  extended header's flags cleared. Pixels are never re-encoded.
- **AI mark:** a file whose own metadata carries the IPTC digital source type
  `trainedAlgorithmicMedia` (C2PA actions or XMP) is marked `aiMarked`. A picture declared a
  photograph or drawing that carries the mark is refused.
- **Repeats:** a picture whose cleaned bytes match a live contribution's (SHA-256) is refused.

## Storage

- The cleaned file goes to the media bucket at `media/<contributor id>/<token>/<name>`, named
  `KalaVigyan_Contribution_<date>_<time>_<craft>_<caption>_<Photo|Drawing|Illustration>.<ext>`.
- A `MediaAsset` holds it: mime, size, width, height, the caption as label, the generator as
  model, the alt text; `PRIVATE` until approved, `CRAFT_SHARED` after, with `approvedById`.
- `ImageContribution` holds the declaration, the status, the asset, the SHA-256, the AI mark and
  the review (`reviewedById`, `reviewedAt`, `reviewNote`). Row level security is on and the public
  roles have no grants.

## `ImageContributionView`

`{id, craftSlug, craftName, stageId, claimIds, origin, label, generator, prompt, caption, altText,
status, aiMarked, mime, width, height, fileUrl, createdAt, reviewedAt, reviewNote}`. `label` is how
a page names the picture: "Photograph", "Drawing" or "Illustration, made with <generator>".
`fileUrl` is a ten-minute presigned link to view the stored file.

## Not yet

- Showing approved pictures on craft pages, with their label (the craft page redesign).
- The contribute page and the admin review screen in the web app.
- The MCP tool that opens a declaration and hands back the upload page's link (slice 2).
