# Sanganeri Hand Block Printing: content changes for Monograph parity

What Sanganeri Hand Block Printing's published content would need for Monograph parity to pass,
read from production on 2026-11-25 (`GET /api/crafts/Sanganeri-Hand-Block-Printing/monograph`,
version 88), for an Admin's AI client to stage through the KalaVigyan MCP server's review tools
(`kalavigyan://admin/published-content.md`, decision 0194) and a person to confirm on the Review
page. Decision 0210 has the causes and the code that fixed them.

| For | Read |
|---|---|
| Why the run failed and what the code now does | [decision 0210](../decisions/0210-a-page-drawn-a-version-behind-reads-its-rest-and-a-where-icon-drawn-at-its-own-size.md) |
| How an Admin stages a removal or an edit | `backend/app/data/admin/published-content.md` |
| How a contributor composes a craft's player from the kit | `.claude/skills/kalavigyan-interactives`, decisions 0198 to 0200 |

## What parity needs: no content change

| Failure line | Item | Cause | Content change |
|---|---|---|---|
| `two-mordants-one-bath: an icon of 24 units draws 239px wide` (658 and 651 px at the wider widths) | `sanganeri-hand-block-printing/chemistry/two-mordants-one-bath` (`reaction_player`, chemistry chapter) | each of its five steps carries a where icon of `viewBox="0 0 24 24"`, and the view drew it at its column's width | none: the view now draws a 24-unit icon 24 px wide (decision 0210, item 4) |
| `shared/chemistry/alizarin-purpurin-3d ... not found` | `shared/chemistry/alizarin-purpurin-3d` (`molecule_3d`, borrowed from Kutch Ajrakh) | placed in the chemistry chapter as it should be; the rest of the page could not be read at the version its HTML named | none: a replaced version is now kept and read (decision 0210, items 1 and 2) |
| `shared/chemistry/indigo-vat-dip ... not found` | `shared/chemistry/indigo-vat-dip` (`dip_player`, borrowed from Kutch Ajrakh) | the same | none |

Nothing is staged for parity. Staging any change to these three would not change what the run
reads.

## If the owner wants the player rebuilt to the kit's bar

The player's five scenes are drawn by hand: rectangles and circles painted in the dye tokens,
each beside a line icon of where the step happens. A scene drawn from the figure kit draws where it
happens itself and needs no where icon (decisions 0199 and 0200). This is a quality change, not a
parity one.

**The contributor's way (preferred).** A contributor's AI client, signed in for Sanganeri
Hand Block Printing:

1. `compose_component` with `craft` `Sanganeri-Hand-Block-Printing` and `kind`
   `reaction_player` (with no `about`, or `about` `{"reaction": "<key>"}` for one of the page's
   reactions as `get_facts` lists them), which returns the player finished from the craft's own
   facts, each step's scene from the kit; when it composes nothing, propose each item its `missing`
   names and call it again.
2. Add what it returns to a draft as it is, with `replaces`
   `sanganeri-hand-block-printing/chemistry/two-mordants-one-bath`, call `preview_page`, look at the
   pictures at 390 and 1440 px, fix every rule the report fails, then `propose_page`.
3. An Admin approves it in the review queue, which registers it in place of the hand-drawn player.

**The Admin's way, only to take the hand-drawn player off the page until a rebuild is approved.**
An edit that drops the where icons is refused at staging, because a step drawn by hand must show
its where icon; the one change an Admin can stage is the removal:

```json
{"decisions": [
  {"kind": "COMPONENTS", "id": "sanganeri-hand-block-printing/chemistry/two-mordants-one-bath",
   "action": "remove", "craft_slug": "Sanganeri-Hand-Block-Printing",
   "reason": "Hand-drawn scenes below the kit's bar; a player composed from the kit replaces it."}
]}
```

`list_components` names the component by its label; use the id it gives if it differs. The two
borrowed components stay.

## How this document is kept true

It records what production held on 2026-11-25 and is not a living list: once the owner chooses,
the change is staged or proposed as above and this file is deleted in the change that records the
choice. Read it again only if Monograph parity fails on Sanganeri Hand Block Printing after the
release that carries decision 0210.
