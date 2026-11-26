from __future__ import annotations

__all__ = [
    "ADD",
    "CONFIRM",
    "CREATED",
    "EDIT_DESCRIPTION",
    "FIX_FIRST",
    "FOLLOW",
    "HELD",
    "PREVIEW",
    "PREVIEW_DESCRIPTION",
    "PROPOSE_DESCRIPTION",
    "READ_NEXT",
    "REVIEWED",
    "SUBMITTED",
]

CREATED = "The draft for {kind} {slug} is open: build the page in it over as many calls as you need."
HELD = "The draft holds {facts} facts, {structure} structure items, {components} components and {pictures} pictures."
ADD = (
    "Add facts, structure, components, a layout, pictures and supplied sources with edit_draft's add, each "
    "figure designed for the page's story (the page playbook, playbook/1), then preview_page with the draft_id."
)
PREVIEW = (
    "Call preview_page with the draft_id to see the page and its checklist report; fix each failure, add the "
    "figure a chapter's story still needs and preview again."
)
SUBMITTED = (
    "Follow each part with get_proposal or my_work; the draft stays readable until it expires. Then open the "
    "next draft for the same page with edit_draft and go on until the page tells its story whole "
    "(playbook/1, step 10)."
)
REVIEWED = (
    "Fix each failed rule from the checklist page guide hands you; look at every picture as a reader and ask "
    "of each chapter whether its story has the figure it needs beside the words, designing what is missing "
    "(playbook/1, step 9; cookbook/1); preview again. When no rule fails and every field is dense with its "
    "figures, propose_page with the same draft_id or bundle."
)
READ_NEXT = (
    "Next, building this page (playbook/1): get_facts for its facts and find its story, decide what a reader "
    "must see by the design principles, read how Kutch Ajrakh answered the same questions (bar/1 lists its "
    "worked chapters), then open its draft with edit_draft, subject and lists."
)
FOLLOW = "Follow each part with get_proposal or my_work."
CONFIRM = (
    "Give the person the confirm_url: nothing is proposed or shown until they, signed in to this account, press "
    "Confirm on it once. Then follow each part with get_proposal or my_work."
)
FIX_FIRST = "Fix each refused part (its message says how) and propose the page again; nothing was held."
EDIT_DESCRIPTION = (
    "Build one craft, family or category page in a private draft over many calls, kept for this account for 14 "
    "days after its last change (one open draft a page, ten at once, 600 kB each). Name the page as subject: the "
    "first edit opens its draft, and an edit with nothing to change returns it whole; a draft_id reads one, a "
    "submitted one with its outcome too. add takes facts, structure items, finished components and dataset "
    "figures ({proposal, cites}, cites naming the draft's facts as fact:0 and on), the layout, pictures, "
    "supplied sources and withdrawals ({label, reason}: your registered components to take off every page); a "
    "component borrowed from another page whose units cite facts this page does not hold is refused, naming "
    "them; remove takes parts by kind and index (removing a fact renumbers the later ones wherever "
    "they are named; a fact still named is kept); lists sets the page's mechanisms, ambiguous terms and "
    "signature fact, which the preview checks. Each part is checked for its shape and the draft for its limits "
    "(20 facts, 20 structure items, 10 components, 10 pictures, 40 supplied sources); nothing is proposed "
    "until propose_page. An add of components hands back guide, each kind's design rules; the page's first "
    "components are answered instead with the design pages, nothing changed, and go in once the call is sent "
    "again with the read_token those pages carry. Its place in the page playbook (playbook/1): open it at "
    "step 4 and add the figures you designed for the page's story, then its pictures and layout; next_step "
    "names what follows."
)
PREVIEW_DESCRIPTION = (
    "Assemble the page a draft (draft_id) or a bundle would make, the stored page with its facts, structure, "
    "components, layout and pictures, without proposing anything: a private link for this account for 24 hours, "
    "drawn exactly as the site draws its pages. Each part says whether it is shown, listed or would be refused "
    "by the checks that run without fetching sources; the gates read the sources on propose_page. A sandboxed "
    "browser then draws the link at 390 and 1440 px in light and returns pictures of the first screen at both "
    "widths and of each chapter: look at them as a reader would. It runs the release's own drawing checks on "
    "every component at both widths (an icon or text drawn too large, a component of no size or drawing empty, "
    "anything past the column or the phone's width, a map, chart or interactive not whole at rest, the masthead "
    "picture and the page's name in the first screen); a failure fails rule 28 with the component's label and "
    "the problem, and when the pictures cannot be made the rule says so and is yours to judge. With it comes the "
    "page checklist report: each of the 29 rules that can be checked mechanically passed or failed with its "
    "evidence, the rest listed for you to judge on the link, coverage by field, figures, sources by grade, "
    "pictures by licence and the page's pictures, figures, interactives and maps beside Kutch Ajrakh's, chapter "
    "by chapter, as guidance only; drawn by ui://kalavigyan/page-preview.html in clients that show MCP Apps. A "
    "translation draws the page in its language, authored pages too. guide hands over the checklist page of "
    "each failed rule. A bundle with components waits, like a draft's first, for the read_token that comes "
    "with the design pages. next_step says what to fix and add before propose_page (playbook/1, step 9)."
)
PROPOSE_DESCRIPTION = (
    "Propose a draft once (draft_id), or a bundle, which may hold one part alone: a finished component or a "
    "figure after searching list_components, the page's layout built on get_page's version, or any mix of facts, "
    "structure, components, layout and pictures for one page. Every part is checked on its own as it would be "
    "alone: facts through the gates, structure through its checks, a component against its kind's spec model "
    "(kalavigyan://components/<kind>.schema.json), its units' facts and the library, where a close match refuses "
    "it with the matches and two ways on, the layout against the page's version, a new picture starting its "
    "upload, a translation's passages against their current English (a TRANSLATE task's). "
    "A refused part leaves the others standing; the report gives each part's outcome, id and reason. "
    "A withdrawal takes your registered component off every page, kept in the record; a component naming the "
    "one it replaces takes its place in every layout once registered. A component borrowed from another page "
    "(a SUBJECT_LINK, or a library label in the layout) whose units cite facts this page does not hold is "
    "refused: build the page's own on its facts. From an account whose proposals publish at once, a draft or a "
    "bundle of several parts is held, nothing proposed, until the person signed in to it presses Confirm once "
    "on the reply's confirm_url. Each part counts against its own hour's allowance (a withdrawal as a component), "
    "and a draft or a bundle of several parts also against the page bundles. Preview it first with preview_page: "
    "while the latest preview of the page fails its drawing checks (rule 28), propose_page refuses it, naming "
    "them, until a preview no longer does. A draft holds 10 components, so a full page is proposed in "
    "rounds, and next_step says when to open the next draft (playbook/1, step 10)."
)
