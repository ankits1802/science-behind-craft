# Field voices: contract

What the documentation portal (Field Repository, `documentation-portal`) must serve so KalaVigyan
can publish consented artisan interview quotes and process photographs, and how KalaVigyan reads,
stores, cites and withdraws them. Design choices: decision 0072. Owner decisions: O4 of
2026-11-17 (consent covers every existing transcription; artisans are quoted by name) and the
decision of 2026-11-18 (consented quotes and process photographs may be published, credited to
the artisan and the workshop, never with contact or identity details).

Last reviewed: 2026-11-18.

Status: the KalaVigyan reader is built behind `FIELD_VOICES_ENABLED` (default off) and has no
storage yet. **The portal routes and the publication consent do not exist yet**; the work is
listed at the end of this file for the portal's own session.

## Why a new route

| Existing route | Why it is not enough |
|---|---|
| `GET /api/data/transcripts/recordings.ndjson`, `turns.ndjson` (plan feature 9's first design) | Needs a signed-in account, so KalaVigyan would hold a portal master password. Returns every speaker (researchers too), uploader names, file names and summaries. Withholds only on the `EXTERNAL_PROCESSING` verdict, which answers `ALLOW` when no consent was ever recorded (`transcription/ledger.decide`). Filtering in KalaVigyan would mean the personal data had already left the portal. |
| `POST /api/cross-portal/peer/search`, `/search/record` | Search snippets for a signed-in person, gated by sharing consent, not by consent to publish. |

So the portal decides what may be published and sends only that. Nothing that must never leave
the portal is sent and then dropped.

## Consent the portal must hold

The portal's one consent store is the `Consent` ledger (`ConsentSubjectType`, `ConsentPurpose`,
`ConsentState`, `ConsentBasis`; the same model on both portals, `shared/enums.json`).

- **A new purpose `PUBLICATION`**: shown to the public on KalaVigyan, credited. It is not
  `EXTERNAL_PROCESSING` (sending audio to a transcription service) and not
  `CROSS_PORTAL_SHARING` (the designer portal looking up identity fields).
- **Publication needs a grant, never an absence.** Unlike `ledger.decide`, "nothing recorded" is
  a no. With `G_item` the current `PUBLICATION` state of subject `RECORDING` keyed by the
  `MediaFile.id` (any media type) and `G_a` that of subject `ARTISAN` for artisan `a`:

  | Item | Sent when |
  |---|---|
  | a quote spoken by artisan `a` | `G_item` is not `REFUSED`; `G_a` is not a `REFUSED` recorded after `G_item`'s grant (or at all, when `G_item` is not `GRANTED`); `G_item` or `G_a` is `GRANTED`; the recording's `EXTERNAL_PROCESSING` verdict (`consent_gate.verdict`) is not `REFUSED`; and, when the grant relied on is an `OWNER_ATTESTATION` `G_item`, `a` never refused sharing beyond the portal (no `ArtisanSharingConsent` with `granted` false and no current `CROSS_PORTAL_SHARING` state `REFUSED` for `a`) |
  | a photograph | `G_item` is `GRANTED` with a basis other than `OWNER_ATTESTATION`, recorded by a person who looked at the picture and affirmed that everyone shown agreed and no one under 18 is shown; no linked artisan has a `REFUSED` `G_a` recorded after that grant |

  The consent sent with a credit is the grant the rule relied on: `G_a` when it is `GRANTED`
  (`scope` `ARTISAN`), else `G_item` (`scope` `RECORDING`).
- **The owner's attestation (O4, 2026-11-17).** A dry-run-first, idempotent script writes one
  `PUBLICATION` `GRANTED` row per recording that had a transcript on 2026-11-17 (a
  `TranscriptVersion` created, or a completed `transcriptText`, by 2026-11-17 23:59:59 India
  time): basis `OWNER_ATTESTATION`, source `owner attestation`, `recordedAt` 2026-11-17 00:00
  India time, actor the owner's account. It skips a recording whose `EXTERNAL_PROCESSING` verdict
  is `REFUSED`. It never covers a photograph or a later recording. An artisan who refused sharing
  beyond the portal (the quote rule above) is not quoted on the attestation: their quotes wait for
  their own `PUBLICATION` grant, and the dry run lists them by artisan id with their recording
  count. **Owner to confirm** whether that refusal should also hold back publication under O4;
  until the owner decides, it does.
- **Withdrawal** is a `REFUSED` row; the next answer leaves the item out.
- **How an artisan is credited.** A new `ArtisanPublicationCredit {artisanId (id), named,
  creditName?, recordedById, recordedAt, updatedAt}` row records the artisan's choice. No row:
  named, by `Artisan.name` (O4). `named` false: credited without a name.

## The routes

Three peer routes on the existing `APIRouter(prefix="/cross-portal/peer")` (or a new
`api/routes/cross_portal_voices.py` included beside it):

```
GET /api/cross-portal/peer/field-voices
GET /api/cross-portal/peer/field-voices/{craftSlug}/quotes?cursor=<opaque>
GET /api/cross-portal/peer/field-voices/{craftSlug}/photographs?cursor=<opaque>
```

### Who may call them

- **Gate:** a new setting `CROSS_PORTAL_FIELD_VOICES_ENABLED` (default `false`) and
  `CROSS_PORTAL_TOKEN` of at least `MIN_SECRET_LENGTH` (32) characters. It does not need
  `CROSS_PORTAL_IDENTITY_ENABLED` or `AADHAAR_FINGERPRINT_KEY`. Gate off: 404 `{"detail": "Not
  Found"}`, as the other peer routes do.
- **Request:** `Authorization: Bearer <CROSS_PORTAL_TOKEN>`, `X-Cross-Portal-Nonce` (16-128
  characters), `X-Cross-Portal-Requested-By: kalavigyan-field-voices`. Reuse
  `cross_portal_peer._admit` with a new readiness function; a wrong bearer or nonce is 401.
- **Answer:** `cross_portal_peer.signed(settings, request, payload)`: `X-Cross-Portal-Signature`
  is HMAC-SHA256 with the token over `"GET\n" + peer_path + "\n" + nonce + "\n" + body`. The
  signed path is the path without the query string, so every page **echoes** the `craftSlug` and
  `cursor` it answers, and KalaVigyan refuses a page that names another. Every answer carries
  `Cache-Control: no-store`.
- **Errors (signed):** unknown craft slug 404 `{"detail": "Unknown craft."}`; a cursor the
  portal did not issue 400 `{"detail": "Unknown cursor."}`; more than 600 calls in 10 minutes from
  one requester 429 `{"detail": "Too many requests."}` with a `Retry-After` header in seconds.
- **Access log:** one `CrossPortalAccessLog` row per call: `action` `FIELD_VOICES_INDEX`,
  `FIELD_VOICES_QUOTES` or `FIELD_VOICES_PHOTOGRAPHS`; `outcome` `ok`, `unknown_craft`,
  `bad_cursor` or `rate_limited`; `remoteUserId` the requested-by value; `entityType` `CRAFT` and
  `entityId` the slug on the craft routes; `resultCount` the items sent.

### Which craft an item belongs to

By `Craft.slug` (the cross-portal identity; the master list's slugs are the same in KalaVigyan).
A recording belongs to the craft of each quoted speaker (`Artisan.craftId`), else to
`MediaFile.craftId`, else to its workshop's craft when the workshop has exactly one
(`WorkshopCraft`). A photograph belongs to `MediaFile.craftId`, else to the craft of its linked
record (`processstep` and `process` through the product, `product`, `tool` through `ToolCraft`,
`artisan`), else to its workshop's only craft. A `MERGED` craft's items are listed under the
craft it was merged into. An item may belong to more than one craft and is then listed under each.

### Index (`schemaVersion` 1)

One answer, no paging. A craft is listed only when it has at least one item to send.

```json
{
  "schemaVersion": 1,
  "portal": "FIELD_REPOSITORY",
  "generatedAt": "2026-11-18T02:00:00Z",
  "crafts": [
    {"craftSlug": "Kutch-Ajrakh", "craftCode": "ajrakh", "recordings": 2, "quotes": 3,
     "photographs": 1, "digest": "1dafe00e…52ed4", "updatedAt": "2026-11-17T12:00:00Z"}
  ]
}
```

| Field | Rule |
|---|---|
| `recordings`, `quotes`, `photographs` | exactly what the craft's pages will hold |
| `digest` | lower-case hex SHA-256 of the UTF-8 text made of one line per item, `"R <recording id> <revision>\n"` and `"P <photograph id> <revision>\n"`, sorted by code point and joined with nothing between |
| `updatedAt` | the latest change to any item of the craft, consent included |

### Quotes page

Recordings ordered by `recordedAt` as an instant, then `id` by code point (`COLLATE "C"`), across
all pages, 25 per page; `nextCursor` null on the last page.

```json
{
  "schemaVersion": 1, "portal": "FIELD_REPOSITORY", "generatedAt": "2026-11-18T02:00:01Z",
  "craftSlug": "Kutch-Ajrakh", "cursor": null, "nextCursor": "c2",
  "recordings": [{
    "id": "rec-1", "mediaId": "media-1", "revision": "91bdd4e889f5d9736c6c2fbd944dfd73",
    "recordedAt": "2026-03-14T10:22:00+05:30", "durationMs": 1832000,
    "workshop": {"id": "ws-1", "title": "Ajrakh documentation visit, Kachchh",
                 "startsOn": "2026-03-12", "endsOn": "2026-03-16", "district": "Kachchh", "state": "Gujarat"},
    "topics": [{"sectionCode": "C", "sectionTitle": "Process", "question": "How do you prepare the mordant paste?"}],
    "artisans": [{"id": "art-1", "named": true, "name": "…", "localName": "…", "yearsInCraft": 31,
                  "district": "Kachchh", "state": "Gujarat",
                  "consent": {"basis": "VERBAL_RECORDED", "scope": "ARTISAN", "recordedAt": "2026-03-14T10:05:00+05:30"}}],
    "quotes": [{"id": "turn-11", "artisanId": "art-1", "position": 11, "startMs": 724000, "endMs": 751000,
                "language": "gu", "text": "…", "textSource": "EDITED",
                "english": "We grind the alum with tamarind seed, and the paste must rest overnight.",
                "englishSource": "MACHINE"}]
  }]
}
```

| Field | Rule |
|---|---|
| recording `id`, `mediaId` | `QuestionnaireRecording.id` when there is one, else the `MediaFile.id`; `mediaId` is the `MediaFile.id` |
| which recordings | `MediaFile` of type `AUDIO` or `VIDEO`, `removedAt` null, status not `DRAFT` or `REJECTED`, its interview not deleted, with a current `TranscriptVersion` (`supersededAt` null) holding at least one quote that may be sent |
| `revision` | at most 64 characters, no whitespace (as for every id), that change whenever anything sent about the recording changes; for example the first 32 hex characters of SHA-256 over the item's JSON (`sort_keys`, compact separators, `revision` left out) |
| `recordedAt` | `QuestionnaireRecording.capturedAt`, else `MediaFile.recordedAt`, with its offset |
| `durationMs` | the recording's, or null; no quote ends after it |
| `workshop` | the interview's or the file's workshop, or null: `title` (`Workshop.title`, or null when the free-text screen below matches it), `startsOn` and `endsOn` (`startDate` or `date`, `endDate`, as dates), `district` and `state` from the workshop `Location`'s stated columns only |
| `topics` | the recording's `QuestionnaireRecordingTarget` rows: the section's `code` and `title`, and the exact wording asked (`askedQuestionId`'s `prompt`) or null; a `question` the free-text screen matches is sent null, and a topic whose section title it matches is left out |
| `artisans` | one credit for each quoted speaker and nobody else (below) |
| `quotes` | one per turn that may be sent, in `position` order |
| quote `id` | `TranscriptTurn.id`; a turn over 4,000 characters is cut at sentence ends into pieces `"<turn id>.<n>"` from 1, each timed from the turn's `words` |
| quote speaker | the turn's `TranscriptSpeaker` has `role` `ARTISAN` and a `personId` that is a subject of the recording (`QuestionnaireRecordingSubject`), an artisan of its interview, or `MediaFile.artisanId`. Researchers, `OTHER` speakers and unnamed "Speaker 2" turns are never sent |
| `text`, `textSource` | `editedText` (`EDITED`), else `machineText` (`MACHINE`); at least 40 characters after trimming, at most 4,000 |
| `english`, `englishSource` | `editedEnglish` (`EDITED`); else the text itself when `translationStatus` is `ALREADY_ENGLISH` (`ORIGINAL`); else `machineEnglish` when `TRANSLATED` (`MACHINE`); else both null (`STALE`, `PENDING`, `FAILED`) |
| `language` | the turn's code, a BCP 47 tag or `und` |
| `startMs`, `endMs` | the turn's (or piece's) times; `endMs` after `startMs` |

A turn is withheld when its text or English matches the portal's personal-data patterns (a
phone or Aadhaar-like number, an email address, a Pehchan card number) or a held-back term of the
free-text screen below, or when its speaker is under 18 on `recordedAt` by `Artisan.dateOfBirth`.

### Artisan credit

| Field | Rule |
|---|---|
| `id` | `Artisan.id` (a database id, never an identity number) |
| `named`, `name`, `localName` | from `ArtisanPublicationCredit`: `named` true sends `creditName`, else `Artisan.name`, and `Artisan.localName` only when no `creditName` was chosen; `named` false sends neither |
| `yearsInCraft` | `derive_experience_years` on the recording or photograph date (from `craftStartDate`, else `experienceYears`), 0-90, or absent |
| `district`, `state` | the artisan's `Location` stated `district` and `state`, or absent; never `Artisan.place` free text |
| `consent` | `{basis, scope, recordedAt}` of the grant the rule relied on |

### Photographs page

Photographs ordered by `takenAt` as an instant (photographs without one last), then `id` by code
point (`COLLATE "C"`), across all pages, 50 per page.

```json
{
  "schemaVersion": 1, "portal": "FIELD_REPOSITORY", "generatedAt": "2026-11-18T02:00:03Z",
  "craftSlug": "Kutch-Ajrakh", "cursor": null, "nextCursor": null,
  "photographs": [{
    "id": "photo-1", "revision": "7b44d54b1fb4b16a9fd145c5fc893613",
    "takenAt": "2026-03-13T09:40:00+05:30", "caption": "Printing the first resist with a wooden block",
    "stage": {"process": "Ajrakh printing", "step": "First resist printing", "stepOrder": 3},
    "workshop": {"id": "ws-1", "title": "Ajrakh documentation visit, Kachchh", "startsOn": "2026-03-12",
                 "endsOn": "2026-03-16", "district": "Kachchh", "state": "Gujarat"},
    "artisans": [{"id": "art-1", "named": true, "name": "…", "yearsInCraft": 31,
                  "consent": {"basis": "VERBAL_RECORDED", "scope": "ARTISAN", "recordedAt": "2026-03-14T10:05:00+05:30"}}],
    "consent": {"basis": "SIGNED_FORM", "scope": "RECORDING", "recordedAt": "2026-03-13T09:45:00+05:30"},
    "permission": {"statement": "Shown on KalaVigyan with the consent of the people pictured. Not openly licensed: ask the rights holder before any other use.",
                   "rightsHolder": "…", "licence": null},
    "image": {"url": "https://<bucket host>/field-voices/ac43…ad91.jpg?response-content-disposition=inline…&X-Amz-Expires=900&…",
              "expiresAt": "2026-11-18T02:15:03Z", "mimeType": "image/jpeg",
              "width": 2400, "height": 1600, "bytes": 812345, "sha256": "ac43…ad91"}
  }]
}
```

| Field | Rule |
|---|---|
| which photographs | `MediaFile` of type `IMAGE`, `removedAt` null, status not `DRAFT` or `REJECTED`, consented as above, none of its linked artisans under 18 on `takenAt` |
| `revision` | as for recordings, with `image.url` and `image.expiresAt` left out |
| `takenAt` | `MediaFile.recordedAt` with its offset, or null |
| `caption` | `MediaFile.caption` trimmed, or null; a caption with personal data withholds the photograph, and one the free-text screen matches is sent null |
| `stage` | for a `processstep` link: `Process.name`, `ProcessStep.name`, `ProcessStep.sortOrder`; else null, and null when the free-text screen matches either name |
| `artisans` | the linked artisans (`MediaFile.artisanId`, an `artisan` link, the product's artisan), credited as above; each `consent` is their own grant, else the photograph's |
| `consent` | the photograph's own grant: `scope` `RECORDING`, never `OWNER_ATTESTATION` |
| `permission` | `statement` (at most 600 characters) and `rightsHolder` from a new portal setting `FIELD_VOICES_RIGHTS_HOLDER`; `licence` a licence name or null (not openly licensed) |
| `image` | a derived copy, never the original object: orientation applied, long edge at most 2,400 px, re-encoded as JPEG (or PNG or WebP) with **no EXIF, XMP, IPTC or GPS data**; `width`, `height`, `bytes` (at most 8 MiB) and `sha256` of that copy. Stored once in the media bucket under the opaque key `field-voices/<sha256>.<ext>` (`jpg`, `png` or `webp`): no user id, uuid, file name or naming-convention field. This is a deliberate exception to the portals' naming convention, whose `media/<userId>/<uuid>/<FileName>` keys carry the uploader, the place and the subject. `url` is a presigned https GET of that key, signed for 900 seconds with a neutral name: `s3.presign_get_url_aged(key, filename="<sha256>.<ext>", mime_type=…, expires_in=900, disposition="inline")`. Its path is exactly `/field-voices/<sha256>.<ext>` and any file name in its query is that same leaf. Its host is the bucket's own: in production `fieldrepo-media-626159998512.s3.dualstack.ap-south-1.amazonaws.com`, what `s3._client()` signs for when `AWS_S3_ENDPOINT` is unset. `expiresAt` is when the URL stops working: now plus the window `presign_get_url_aged` returns plus 450 seconds (its cache reuses a URL for the first half of its 900 seconds) |

### Free text

Free text can undo a credit with `named` false, and can carry the village that every credit
leaves out (decision 0072): a caption or workshop title can name the artisan, and a workshop
title built by `workshop_inference.workshop_title` comes from the free-text `Workshop.place`.
KalaVigyan never receives the withheld name or the village, so only the portal can screen for
them. It screens every free-text field it sends: quote `text` and `english`, `workshop.title`,
`caption`, `stage.process` and `stage.step`, and `topics[].sectionTitle` and `question`.

- **Held-back terms of an item:** the `name`, `localName` and any `creditName` of every artisan
  linked to the item or to its workshop who is not credited by name on this item (`named` false,
  or no `PUBLICATION` grant); and the `village`, `placeName`, `address` and `pincode` of the
  workshop's `Location` and of each linked artisan's `Location`, with `Workshop.place` and
  `Artisan.place`, each split at commas, semicolons, slashes and line breaks, leaving out a part
  that is the stated `district` or `state`, or `India`.
- **Match:** after Unicode NFKC normalisation and case folding, a held-back term, or any word of
  at least 3 letters of a held-back name, matches where it stands with no letter or digit on
  either side, in the script it is held in.
- **A match:** withholds a quote; sends `workshop.title`, `caption` or `stage` as null; sends a
  `question` as null and leaves out a topic whose section title matches. Free text is never
  rewritten.
- **What it cannot catch:** a spelling the portal does not hold (another script, a nickname, a
  misspelt village). So the person who grants a photograph also affirms that its caption names
  nobody who has not agreed to be named and no village, and KalaVigyan never shows a workshop
  title beside an unnamed credit.

### Never sent

Never sent, and refused by KalaVigyan as a whole answer when any key names it
(`field_voices_never_sent`; a key is lower-cased and stripped to letters and digits, then
`FORBIDDEN_KEYS` match it whole: age, agegroup, ageyears, dob, gender, mobile, whatsapp, lat,
lng, lon, long, gps, coordinates, geo, geolocation, altitude, accuracy, village, placename,
place, locality; and `FORBIDDEN_KEY_PARTS` anywhere in it: phone, email, aadhaar, pehchan,
fingerprint, birth, address, pincode, postcode, latitude, longitude): phone numbers and their
country code, email addresses, Aadhaar numbers, last four digits or fingerprints, Pehchan card
numbers or availability, dates of birth, ages, gender, addresses (`Artisan.address`,
`Location.address`, `pincode`), coordinates of any kind (device fix, subject pin, altitude and
accuracy included), the village and any other free-text place (`village`, `placeName`,
`Workshop.place`, `Artisan.place`).

Also never sent: a photograph of anyone under 18, the original photograph, anything without a
recorded `PUBLICATION` grant, artisan cards and codes, notes, dos and don'ts, review notes, the
names of researchers, uploaders and the accounts that mapped speakers, file names and object keys
(an image URL names only its opaque copy), full transcripts, summaries and glossaries.

Version 1 may gain fields the reader ignores, except those keys. Removing or renaming a field or
changing a meaning is version 2 and needs a KalaVigyan change first.

## How KalaVigyan reads it (built)

Code: `backend/app/services/portal_peer.py` (`PortalPeer.signed_json`, the one signed GET of both
peer feeds), `field_voices_feed.py` (the typed answers, `snapshot_digest`),
`field_voices_never_sent.py` (the never-sent key scan), `field_voices_reader.py`
(`field_voices_reader(settings)`, `FieldVoicesReader.index()`, `.craft(entry)`). Tests:
`backend/tests/field_voices/` against recorded answers in `backend/tests/field_voices/recorded/`.

- **Settings:** `FIELD_VOICES_ENABLED` (default `false`; off, the reader refuses to start with
  `NotConfigured`), `FIELD_VOICES_IMAGE_HOSTS` (comma-separated bare host names the photographs
  may be served from; required when on, else `NotConfigured`; production
  `fieldrepo-media-626159998512.s3.dualstack.ap-south-1.amazonaws.com`), `CROSS_PORTAL_TOKEN`,
  `FIELD_REPOSITORY_API_URL`.
- **Every answer:** the signature over the path and nonce (an unsigned answer, one signed with
  another token, or one signed for another route is `Refused("unsigned_answer")`);
  `schemaVersion` 1; the portal; no never-sent key; the contract's types and limits (aware
  datetimes, BCP 47 languages, credits that match the quotes, a photograph's own consent, a signed
  URL that is https, expires within 15 minutes of `generatedAt`, is served from a listed host
  with no port, has the path `/field-voices/<sha256>.<ext>` for its own `sha256` and `mimeType`,
  and names no other file); the echoed slug and cursor. A 429 is an `ExternalFailure` of kind
  `rate_limit` carrying the portal's `Retry-After` in `retry_after`.
- **A craft:** a list the index counts as empty is not asked for; every other page is read (at
  most 200 per list; a cursor that repeats is refused); ids are unique across pages; the counts
  and the recomputed digest must equal the index entry, else `Refused("snapshot_changed")` and
  nothing of that craft is applied in that run; items that go backwards in the contract's order
  across pages are refused.
- **Its own screen:** any quote whose text or English, and any recording or photograph whose
  credits, workshop, topics, caption or stage, match `research/evidence.personal_data_in` is
  dropped and reported in `CraftVoices.dropped`; a credit left with no quote goes with it. A
  recording or photograph that credits an unnamed artisan has its `workshop.title` cleared, so a
  title is never shown beside an unnamed credit.

## How KalaVigyan stores, cites and shows it (to build)

Storage needs one migration (not in this run; listed for the lead):

| Table | Columns |
|---|---|
| `FieldVoiceCraft` | `portal`, `craftId` (FK `Craft`), `digest`, `recordings`, `quotes`, `photographs`, `lastCompleteAt`, `hiddenAt`; primary key (`portal`, `craftId`) |
| `FieldVoiceRecording` | `id`, `portal`, `portalRecordingId`, `mediaId`, `revision`, `recordedAt`, `durationMs`, `workshop` (JSONB), `artisans` (JSONB credits with consent), `sourceId` (FK `Source`), `lastConfirmedAt`, `hiddenAt`; unique (`portal`, `portalRecordingId`) |
| `FieldVoiceRecordingCraft` | `recordingId`, `craftId`; the crafts a recording is listed under |
| `FieldVoiceQuote` | `id`, `recordingId` (FK, cascade), `portalQuoteId`, `artisanId` (portal id), `position`, `startMs`, `endMs`, `language`, `text`, `textSource`, `english`, `englishSource`, `chunkId` and `englishChunkId` (FK `Chunk`, set null); unique (`recordingId`, `portalQuoteId`) |
| `FieldVoicePhotograph` | `id`, `portal`, `portalMediaId`, `revision`, `takenAt`, `caption`, `stage` (JSONB), `workshop` (JSONB), `artisans` (JSONB), `consentBasis`, `consentRecordedAt`, `statement`, `rightsHolder`, `licence`, `objectKey`, `mimeType`, `width`, `height`, `bytes`, `sha256`, `mediaRefId` (FK `MediaRef`, set null), `lastConfirmedAt`, `hiddenAt`; unique (`portal`, `portalMediaId`) |
| `FieldVoicePhotographCraft` | `photographId`, `craftId` |

No enum change: `SourceKind` already has `FIELD_TESTIMONY`.

- **A recording is a primary source:** one `Source` per recording, `kind` `FIELD_TESTIMONY`,
  title "Field interview, <workshop>, <recording date>" (or "Field interview, <recording
  date>" without a workshop), `authors` the named credits, `year` of `recordedAt`, `publisher` "Field Repository",
  no `url`, `storage` `EXCERPT`, `sensitivity` `ATTRIBUTE_REQUIRED`, `origin` `IMPORT`,
  `externalIds.fieldRepository` `{recordingId, mediaId, revision}`, `retrievedAt` the sync time.
- **A quote is a chunk:** the original text with `lang` its language, and the English as a second
  chunk, both with the locator `m:ss–m:ss` (`h:mm:ss` past an hour) from `startMs` and `endMs`,
  `acl` `PUBLIC` (published by consent; this replaces PLAN section 13 item 7's researcher-only
  excerpts). A claim drawn from a quote stays provisional "field testimony" until a reviewer
  raises it.
- **A citation** reads "<credit>, interview recorded <date>, <workshop>, <locator>"; a credit with
  `named` false reads "An artisan of <craft>, <district>, <state>". <workshop> is the workshop's
  `title` when the answer kept one, else "a workshop in <district>, <state>, <month and year of
  `startsOn`>" from the stated fields only. A machine English is labelled as a machine
  translation; the original language text is always shown beside it.
- **A photograph** is downloaded once per revision within the URL's 15 minutes (a plain GET to a
  `FIELD_VOICES_IMAGE_HOSTS` host; the cross-portal token is never sent to the image host),
  checked against `mimeType`, `bytes`, `sha256`, `width` and `height`, re-encoded without
  metadata, and stored in KalaVigyan's media bucket under a key from `services/naming.py` that
  carries the copy's `sha256` and no name or place (a new `field_voice_key`, added with the
  storage); a `MediaRef` row (`display` `INLINE`, provider `field_repository`, `credit` the credit
  line, `licence` null, the statement and rights holder shown) points at it. It is not openly
  licensed, so it is never offered for reuse or export.
- **Runs:** nightly and after each deploy, like the craft sync: read the index; for each craft
  whose digest differs from `FieldVoiceCraft.digest`, read its pages and apply them in one
  transaction; for an unchanged craft, stamp `lastConfirmedAt`. The portal allows 600 calls in 10
  minutes, so the sync spaces its calls at least one second apart, and on a 429 waits the
  `retry_after` it carries (at most 60 seconds) and asks again, up to 3 times, before it leaves
  that craft as unread for this run.

## How KalaVigyan withdraws

- An item absent from a craft's complete snapshot loses that craft's link
  (`FieldVoiceRecordingCraft`, `FieldVoicePhotographCraft`), and a craft absent from a complete
  index loses all of its links. An item listed under another craft keeps that link and its
  stored voices. An item left with no craft link is withdrawn in the same run: its quotes,
  chunks, claims that cite only it, its `Source`, the photograph copy and its `MediaRef` are
  deleted; knowledge pieces and stored explainers that hold it are rebuilt without it, and a
  saved explainer that quoted it shows that a quote was withdrawn by its speaker. Revoked consent
  takes an item out of every craft's snapshot at once, so every craft that listed it has a new
  digest and is read.
- A craft whose listed digest changed but whose pages could not be read completely has its stored
  voices **hidden** (not deleted) until a complete read.
- Nothing is served that a complete sync has not confirmed within the last 7 days: on a longer
  outage the voices are hidden until the next complete sync.
- A failed index (unreachable, 404 with the gate off, unsigned, broken) changes nothing beyond
  the 7-day rule.

## Portal-side work (for the documentation portal's own session)

1. `ConsentPurpose` gains `PUBLICATION` in `shared/enums.json` and a migration (`ALTER TYPE
   "ConsentPurpose" ADD VALUE 'PUBLICATION'`), in both portals, since the ledger is one model.
2. A publication verdict beside `consent_gate`: the rules above (a grant required, per speaker,
   per photograph; on an `OWNER_ATTESTATION` grant, no speaker who refused sharing beyond the
   portal), with tests.
3. `ArtisanPublicationCredit` (model, migration, API) and, on the artisan form, "Publish on
   KalaVigyan" with the credit choice; on a recording, the same per recording; on a photograph,
   the grant with the affirmation that everyone shown agreed, no one under 18 is shown and the
   caption names nobody who has not agreed to be named and no village; each writes the ledger and
   a `REFUSED` row withdraws.
4. The owner-attestation script for transcriptions that existed on 2026-11-17, dry run first; the
   dry run lists, by artisan id and recording count, the artisans it leaves out for a sharing
   refusal.
5. The free-text screen (held-back terms per item, the match and what a match does), one function
   used by both page builders.
6. The derived, metadata-free photograph copy (Pillow is already a dependency), stored once per
   revision under `field-voices/<sha256>.<ext>`, and its presigned URL with the neutral file name
   and `disposition="inline"`; the portal's naming convention records this key as its one
   exception.
7. The three routes, `CROSS_PORTAL_FIELD_VOICES_ENABLED` and `FIELD_VOICES_RIGHTS_HOLDER` (both in
   the GitHub secrets and the box `.env`), the access log rows, the rate limit with `Retry-After`,
   and tests that pin every never-sent field, the consent rules (a sharing refusal under the
   attestation included), the free-text screen (a caption and a workshop title naming an unnamed
   artisan, a village in a caption, a quote naming its speaker's village, a title built from
   `Workshop.place`), the image key, URL path and file name, the digest, the order (instants, then
   ids by code point, untimed photographs last), the paging and a signature computed with
   `cross_portal.sign`.
