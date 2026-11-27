from __future__ import annotations

__all__ = [
    "ADD",
    "BRIEF_NEXT",
    "CONFIRM",
    "CREATED",
    "DESIGN_MORE",
    "DESIGN_NOTES",
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
    "Fix each failed rule from the checklist page guide hands you. Then read your own pictures chapter by "
    "chapter as a designer, against the designer's rubric (design-critique/1): write a note for each thing you "
    "would fix (chapter, where, problem, fix) and a verdict, fix what you found, designing the figure a "
    "chapter's story still needs (playbook/1, step 9; cookbook/1), and preview again with your notes as "
    "critique; a client that cannot see the pictures adds read_pictures for the server's read. When no rule "
    "fails and every field is dense with its figures, propose_page with the same draft_id or bundle: your "
    "latest critique goes to the reviewer with the layout."
)
READ_NEXT = (
    "Next, building this page (playbook/1): read its brief (get_page, parts brief), its story and every fact "
    "in one line, and find its story, reading a fact whole with get_facts and ids; decide what a reader must "
    "see by the design principles, read how Kutch Ajrakh answered the same questions (bar/1 lists its worked "
    "chapters), then open its draft with edit_draft, subject and lists."
)
BRIEF_NEXT = (
    "Find the craft's story in these lines; get_facts with ids gives any fact's full text, quotes and sources, "
    "and get_page with the cursor gives the fact lines still to come. Next (playbook/1, step 2): decide what a "
    "reader must see by the design principles (kalavigyan-design/1), then read how Kutch Ajrakh answered the "
    "same questions (bar/1) before opening the draft with edit_draft."
)
FOLLOW = "Follow each part with get_proposal or my_work."
CONFIRM = (
    "Give the person the confirm_url: nothing is proposed or shown until they, signed in to this account, press "
    "Confirm on it once. Then follow each part with get_proposal or my_work."
)
FIX_FIRST = "Fix each refused part (its message says how) and propose the page again; nothing was held."
EDIT_DESCRIPTION = (
    "Builds one craft, family or category page in a private draft over many calls, kept for this account for "
    "14 days after its last change (one open draft a page, ten at once, 4 MB each). With the page as subject, "
    "an edit opens the page's draft when it has none, and an edit with nothing to change returns it whole; a "
    "draft_id reads one, a submitted one with its outcome too. add takes facts, structure items, finished "
    "components and dataset figures ({proposal, cites}, cites naming the draft's facts as fact:0 and on), the "
    "layout, pictures, supplied sources, withdrawals ({label, reason}: this account's registered "
    "components to take off every page) and sections ({field, sentences}: a field's written section, its "
    "sentences in order, each {text, claim_ids} citing stored facts the page shows in that field; a later "
    "section for a field replaces the draft's earlier one); a "
    "component borrowed from another page whose units cite facts this page does not hold is refused, naming "
    "them; remove takes parts by kind and index (removing a fact renumbers the later ones wherever "
    "they are named; a fact still named is kept); lists sets the page's mechanisms, ambiguous terms and "
    "signature fact, which the preview checks. Each part is checked for its shape and the draft for its limits, "
    "room for a whole page (200 facts, 100 structure items, 100 components, 40 pictures, 40 supplied sources, "
    "100 withdrawals, a section for each of the 16 fields), an add taking up to 20 facts, 20 structure items, 10 components and 10 pictures a call, "
    "as does a bundle sent whole; nothing in a draft is proposed until the draft itself is. Components added "
    "to a draft that holds none are held back, nothing changed, until the call carries the read_token "
    "returned with KalaVigyan's design pages."
)
PREVIEW_DESCRIPTION = (
    "Assembles the page a draft (draft_id) or a bundle would make, the stored page with its facts, structure, "
    "components, layout and pictures, without proposing anything: a private link for this account for 24 hours, "
    "drawn exactly as the site draws its pages. Each part says whether it is shown, listed or would be refused "
    "by the checks that run without fetching sources; the gates read the sources when the page is proposed. A "
    "section is drawn in place of its field's published one when every sentence cites facts the page shows in "
    "that field and states no number, name, date or place they do not, in at least three sentences or as many "
    "as the field's facts allow; its judge reads each sentence against its facts when it is proposed. A "
    "sandboxed browser then draws the link at 390 and 1440 px in light and returns pictures of the first screen "
    "at both widths and of each chapter. It runs the release's own drawing checks on every component at both "
    "widths (an icon or text drawn too large, a component of no size or drawing empty, anything past the column "
    "or the phone's width, a map, chart or interactive not whole at rest, the masthead picture and the page's "
    "name in the first screen); a failure fails rule 28 with the component's label and the problem, and when "
    "the pictures cannot be made the rule says so and is left to judgement. With it comes the page checklist "
    "report: each of the 29 rules that can be checked mechanically passed or failed with its evidence, the rest "
    "listed to be judged on the link, coverage by field, figures, sources by grade, pictures by licence and the "
    "page's pictures, figures, interactives and maps beside Kutch Ajrakh's, chapter by chapter, for comparison "
    "only; drawn by ui://kalavigyan/page-preview.html in clients that show MCP Apps. A translation draws the "
    "page in its language, authored pages too. A critique of the previous preview's pictures is recorded with "
    "this preview and shown in the report, on the card and to the layout's reviewer, never as a gate; "
    "read_pictures has the server read the pictures, within a fixed cost. A bundle with components needs the "
    "read_token returned with KalaVigyan's design pages, as a draft's opening components do."
)
DESIGN_NOTES = (
    " The server's read of the pictures left {count} notes, yours to judge as your own and never a failure; "
    "work through each before propose_page: {notes}."
)
DESIGN_MORE = "; and {count} more in report.designRead"
PROPOSE_DESCRIPTION = (
    "Proposes a draft once (draft_id), or a bundle, which may hold one part alone: a finished component or a "
    "figure, the page's layout built on its current layout version, or any mix of facts, structure, "
    "components, layout, pictures and sections for one page. Every part is checked on its own as it would be "
    "alone: facts through the gates, structure through its checks, a component against its kind's spec model "
    "(kalavigyan://components/<kind>.schema.json), its units' facts and the library, where a close match refuses "
    "it with the matches and two ways on, the layout against the page's version, a new picture starting its "
    "upload, a translation's passages against their current English (a TRANSLATE task's), a section "
    "through the preview's checks and a judge, the cheapest model the nightly evaluation holds reliable for "
    "it, that names anything a sentence says its cited facts do not; one refused sentence refuses the whole "
    "section, and a section that passes waits for a reviewer beside the field's published one, approval "
    "putting it in that one's place and keeping the replaced one in the record. "
    "A refused part leaves the others standing; the report gives each part's outcome, id and reason. "
    "A withdrawal takes this account's registered component off every page, kept in the record; a component "
    "naming the one it replaces takes its place in every layout once registered. A component borrowed from "
    "another page (a SUBJECT_LINK, or a library label in the layout) whose units cite facts this page does not "
    "hold is refused. From an account whose proposals publish at once, a draft or a bundle of several parts is "
    "held, nothing proposed, until the person signed in to it presses Confirm once on the reply's confirm_url. "
    "Each part counts against its kind's hour, sized for one whole page (a withdrawal as a component, a "
    "section as a structure item), and a "
    "draft or a bundle of several parts also against the page bundles. While the page's latest preview fails "
    "its drawing checks (rule 28), the page is refused, naming them, until a preview no longer does. A draft "
    "holds 10 components, so a full page is proposed in rounds."
)
