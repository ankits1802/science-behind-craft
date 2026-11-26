# Removing and editing published content

For an Admin's or Master Admin's AI client signed in with the review scope. Anything already published
can be removed or edited over MCP, and nothing changes until a person confirms it: `stage_reviews`
stores the decision in a batch, the Review page shows it with its reason and the client that proposed
it, and an Admin presses Confirm selected once for the batch. A client that shows forms asks the
person whose AI staged the batch at once, in the client, to confirm all, some or none of it, saying
what each item will do; only that person's answer confirms, never the AI, and what is left waits on
the Review page. A batch expires three days after it was staged, and an Admin stages at most 100
items in an India day. Every removal keeps the record, names
who confirmed it and why in the audit log, and refreshes the pages it touched. A removal or an edit
also drops every earlier edition of those pages (`/crafts/<slug>/v<N>`), so none still shows what was
removed or the text an edit replaced; the page's next version is kept again.

## Find the item

`review_queue` with `published` reads published content instead of the queue:

- `{"published": {"kind": "IMAGES", "subject": {"kind": "craft", "slug": "Sanganeri-Hand-Block-Printing"}}}`
  lists the page's items of that kind, 25 at a time; pass the reply's `next_cursor` as `cursor` for
  the next 25.
- `{"published": {"kind": "IMAGES", "id": "<id>"}}` opens one item with the fields an edit changes and
  what each holds now; a component opens by its `label` as well.

| Kind | Where its id comes from | Remove | Edit |
|---|---|---|---|
| `FACTS` | `get_facts` | `retract`, as before | `text` |
| `COMPONENTS` | `list_components` (name it by `label`) | off every page, or off the one page `craft_slug` or `family_slug` names | `title`, `description`, `spec`, `units` |
| `IMAGES` | `published` on a craft's page | off its craft's pages and no longer served; its record, credit and file are kept | `caption`, `alt_text`, `focal`, `place` |
| `LAYOUTS` | `published` on the page: its current layout | the page goes back to the latest earlier layout that is neither this one nor one a removal took off, or to its default arrangement | |
| `STRUCTURE` | `published` on the page: each entry with its fact's id and `entry` kind | off the page | the entry's own fields, below |
| `READINGS` | `published` on a craft's page | off the process view and the craft's pages | |
| `LAYERS` | `published` with no page: the approved map layers | no longer fit to ship; a layer already drawn from `tools/maplayers` leaves the maps when an engineer takes it out | |
| `STAGES` | `published` on a craft's page: the stages answers found that were placed | off its process, the stages after it moving up one | |
| `SOURCES` | `get_facts`, each fact's sources | unlinked from every fact that cites it | `correct`, as before |

Some removals are refused while other content depends on the item, and the refusal names it: a source
that is the only source of a fact (retract the fact or give it another source with `propose_source`
first), a source whose quotes readings are read from, a source that is a component's last, a stage
that still holds conditions, reactions or pictures, and a layout that is no longer the page's current
one.

## Stage it

Each decision is `{kind, id, action, reason}` with a reason of at least 12 characters, plus:

- for a removal of a component from one page, `craft_slug` or `family_slug`;
- for a structure entry whose fact holds up more than one entry, `entry` (its kind);
- for an edit, `edit`: only the fields that change and their new values.

```json
{"decisions": [
  {"kind": "IMAGES", "id": "<picture id>", "action": "remove", "reason": "<why, in at least 12 characters>"},
  {"kind": "FACTS", "id": "<fact id>", "action": "edit", "reason": "<why>",
   "edit": {"text": "<the text as its quotes state it>"}},
  {"kind": "STRUCTURE", "id": "<fact id>", "entry": "NATIVE_NAME", "action": "edit", "reason": "<why>",
   "edit": {"text": "<the name as its source gives it>"}}
]}
```

The server reads what each named field holds now and keeps it with the edit, so the person confirming
sees every field's before and after. An edit is refused at staging when it names a field the kind does
not edit, changes nothing, or fails a gate below, in the gate's own words; it is refused when it is
confirmed if any field it changes was changed by someone else meanwhile. A person may change a staged
decision's reason, but an edit is confirmed with the values it was staged with and a removal stays a
removal; stage a different one anew.

## The gates an edit passes

The same checks the item passed when it was first proposed.

- **A fact's text**: 20 to 1000 characters and no personal data; every figure in it appears in one of
  its quotes; at least half of its words are in its quotes; and each quote is still found in the
  passage stored for its source. A fact with no quote is retracted and proposed anew with its quotes.
- **A component**: its spec and units pass every check a delivered component passes (its kind's
  schema, dataset cells, and units whose facts are shown and state what the units say). Its units cite
  only the facts it already rests on; to cite others, propose a replacement that names `replaces`.
- **A picture**: `caption` and `alt_text` of 3 to 300 characters; `focal` a box `{x, y, width,
  height}` inside the picture, or null for none; `place` a stage or material of the picture's craft
  (`{"stage_id": ...}`, `{"material_id": ...}`), a slot (`{"slot": "MASTHEAD"}` or `RECORD`), or `{}`
  for loose.
- **A structure entry**, through its own proposal's rules (the page must still hold its stage or
  material, and a name, term or question is never given twice), and a GI record too: every name,
  colour and number the edit brings must be in a quote of the facts the entry rests on, or it is
  refused as `Not edited: the STATED check refused it.` with the value no quote states:

| Entry | Its fields |
|---|---|
| `STAGE_AFTER` | `text`, `colours` |
| `NATIVE_NAME` | `text`, `language`, `script` |
| `BOTANICAL_NAME` | `botanical_name` |
| `GLOSSARY_TERM` | `meaning`, `language`, `script`; a renamed term is removed and proposed anew |
| `CONFLICT` | `about` |
| `OPEN_QUESTION` | `question`, `settled_by` |
| `GI_RECORD` | `application_number`, `certificate_number`, `filed_on`, `registered_on`, `journal_issue`, `proprietors`, `authorised_user_count` |

A stage's why (`STAGE_WHY`) is the fact it rests on, so that fact is edited instead, and a reaction
(`REACTION`) is removed and proposed anew, since its equation is balanced when it is proposed.

## What stays on the site

Testimony and pictures waiting for review are decided on the site only. A batch proposed by a
craft's steward, asking that a component it did not propose leave its pages, is confirmed or
discarded on the Review page like any other. A picture a curated dossier
holds changes with that dossier's import.
