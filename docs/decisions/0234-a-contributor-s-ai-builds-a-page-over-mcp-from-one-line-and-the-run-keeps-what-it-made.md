# 0234. A contributor's AI builds a page over MCP from one line, run by hand before a release, and the run keeps what it made

A workflow dispatched by hand, `agent-acceptance.yml`, signs a contributor's MCP client in as the
Professor E2E account and gives Claude one plain request through the Claude API's MCP connector,
with drafts and previews allowed and nothing that proposes, publishes or reviews. The loop runs
until the model stops or the cap is reached. The run keeps the transcript, the last preview with
its pictures, the private link and the cost, and writes a short summary. The run is the evidence;
a second opinion on the pictures is shown, and it never passes or fails the run.

Date: 2026-11-26. Status: accepted (the lead's lane brief `ux-acceptance`, on the owner's word of
2026-11-26 that "done" means what a contributor's AI builds unaided from a plain request, judged by
Kutch Ajrakh's design principles, not by green checks). It amends
[decision 0195](0195-a-preview-drawn-seen-and-checked-before-it-is-proposed.md), item 7 (the agent
sees the page): a client on the API's MCP connector receives only the text of a tool result. The
contract is `docs/contracts/mcp-oauth.md` (How this document is kept true); the operations are in
`docs/RUNBOOK.md`, Release gate.

| For | Read |
|---|---|
| The preview, its pictures and its drawing checks | [decision 0195](0195-a-preview-drawn-seen-and-checked-before-it-is-proposed.md) |
| The contribution round trip whose sign-in this run shares | [decision 0149](0149-a-fact-readers-can-see.md) |
| The tools and their groups | [decision 0111](0111-fewer-mcp-tools.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- The checks on the MCP path prove pieces: the MCP client check signs in with the read scope and
  calls one tool, and the contribution round trip proposes one test fact. None of them watches a
  model build a page, and the owner judged the Sanganeri Hand Block Printing page a contributor's AI
  rebuilt as far below Kutch Ajrakh.
- The Claude API's MCP connector (`mcp_servers` with an `mcp_toolset`) carries tools only, not
  prompts or resources. Its `mcp_tool_result` block holds text blocks only (the SDK's
  `BetaMCPToolResultBlock.content`), so the pictures `preview_page` returns since decision 0195
  never reach a model on this path.
- The `claude-api` skill names the connector beta `mcp-client-2025-11-20`. The live connector
  documentation names `mcp-client-2026-09-15` as its successor, which includes everything the older
  header does and records the server's tool list in an `mcp_tool_listing` block.

## Decision

1. **By hand only.** `.github/workflows/agent-acceptance.yml` has no schedule and no pull-request
   trigger, so it never spends money by itself. It takes `craft` (default
   `Sanganeri-Hand-Block-Printing`), `request` ("Deepen this craft's page to the KalaVigyan bar."),
   `cap` in US dollars (default 12, above 1 and at most 50) and `model` (default `claude-opus-5-5`).
   Inputs reach the scripts through the environment, never through the script text. Only one run
   goes at a time.
2. **Signed in like a contributor.** The release project `agent-acceptance`
   (`frontend/e2e/release/agent-acceptance.spec.ts`) registers a client, signs in with PKCE through
   the consent page as the Professor E2E account and asks for `read contribute`. It uses the same
   sign-in as the contribution round trip, now one function (`mcpSignIn.signIn`) that both call. The
   tokens go to a file in the runner's temporary folder, readable only by its owner, outside the
   artifact. Its shape is `shared/agent-acceptance.token.golden.json`, which both sides test. No
   token is printed. The run masks both tokens as it reads them and masks each pair a refresh
   brings. Access tokens live an hour, so the run refreshes ten minutes before the hour. The last
   step revokes the connection however the run ended.
3. **The model through the connector.** Each turn is a streamed `beta.messages` request with
   `betas: ["mcp-client-2026-09-15"]`. Its `mcp_servers` entry holds the production MCP URL and the
   access token, and a single `mcp_toolset` sets `default_config: {enabled: false}` and enables 13
   tools: `find_crafts`, `get_page`, `get_facts`, `list_components`, `search_sources`,
   `read_source`, `lookup`, `list_open_work`, `my_work`, `get_proposal`, `edit_draft`,
   `compose_component` and `preview_page`. Not offered are every `propose_*` tool, `propose_page`,
   `supply_source`, `give_pictures`, `check_pictures`, `reserve_tasks`, `steward_craft`, `ask` (it
   would store an answer and spend the site's own model budget) and the admin tools. A connector
   call runs before its reply returns, so the toolset is the guard and the loop is the tripwire: the
   loop stops at once on any call outside the list. Thinking is adaptive with summarized display,
   effort is `high`, `max_tokens` is 64,000 and caching is automatic.
4. **Only what a contributor's client would have.** The system prompt is one line saying the model
   is Claude, connected to the KalaVigyan MCP server with a contributor's account. Then come the
   server's own `instructions`, read live with `initialize` and placed as Claude Code and Claude
   Desktop place them, then the limit: build drafts and previews, never call `propose_page` or any
   proposing, publishing or review tool. No repository text, skill or hint is added. The user turn
   is the request, then "The craft: <name>".
5. **The cap, counted from usage.** Each response is priced from the usage it reports, at the
   provider catalogue's price for the model (`backend/app/providers/catalogue_specs.py`). Plain
   input, cache writes at 1.25 times the input price, cache reads at 0.1 times and output are each
   priced at their own rate. A turn is sent only while the money spent plus the last turn's cost
   stays under the cap less $1, which is kept for the second opinion. A run therefore passes that
   mark by at most one turn, and 150 turns is a further ceiling. The run stops when the model stops,
   when the cap is reached, on a refusal, when the model is cut off (`max_tokens` or the context
   window), on a call outside the list, or when a request fails.
6. **No fallback model.** The `claude-api` skill puts server-side fallbacks into Claude Opus 5.5
   code by default. They are left out here because a fallback would swap the model under test. A
   refusal ends the run and says so.
7. **What is kept.** The artifact `agent-acceptance-<run id>` holds:
   - `transcript.json`: each turn's stop reason, usage, cost, text and thinking summaries, every
     call's name and arguments, and every result, each cut at 2,000 characters with a note of how
     many were left out;
   - `preview.json`: the last preview that succeeded, as the model got it and as drawn again;
   - `pictures/`: the pictures, named by caption;
   - `preview-url.txt`, `cost.json`, `summary.md` (also in the job summary) and `opinion.md`.

   The transcript and the cost are rewritten after every turn, so a run that is stopped keeps its
   turns. The job fails only when a request failed or a call outside the list ran. Every other way
   of stopping is evidence.
8. **The pictures are drawn again.** After the loop the run calls `preview_page` itself with the
   arguments of the model's last successful preview. This makes one more private preview of the same
   draft, within the account's 30 previews a window, and the run keeps its pictures. The summary
   says how many non-text items reached the model through the connector.
9. **A second opinion, never the verdict.** When there are pictures and $1 of the cap is left, one
   call shows the pictures with sections 1 and 2 of the `kalavigyan-design` skill (principles and
   non-negotiables, read from the checkout). It asks for a judgement against each one with its
   reason, a rating out of 10 and three changes. It judges stills, so the motion rules that the
   owner's instructions override (motion that plays on its own) do not come into it.

## Consequences

- A run costs at most about its cap in API spend: the loop stops before it passes the cap less $1
  by more than one turn, and the second opinion fits in the $1 kept. Its GitHub minutes are those
  of one Chromium sign-in, a backend `uv sync` and the run itself (up to 150 minutes).
- Production gains only what a contributor's AI would leave: the Professor's private drafts and
  previews (alive 24 hours), one OAuth connection made and revoked, and the server's own records of
  each call. Nothing is proposed, published or reviewed.
- A run that spends the account's previews leaves none for the second drawing, and its summary says
  so. The pictures then come only from the private link.
- The connector's text-only results are a finding for the MCP path: a contributor whose client is
  driven through the API, rather than an MCP client that shows images, never sees the page it made.
- No migration, no product code and no new dependency. The workflow test parses the YAML with
  PyYAML, which the backend already installs through `uvicorn[standard]`.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by `tools/tests/test_acceptance_loop.py`
(the cap, the tool filter both ways, the resumed pause, failures, refusals, the turn limit and the
refused caps, with a fake API client), `tools/tests/test_acceptance_evidence.py` (the transcript, the
last successful preview, the pictures, the summary and the second opinion's inputs),
`tools/tests/test_acceptance_connection.py` (the token file, refresh, masking and revocation),
`tools/tests/test_acceptance_workflow.py` (the workflow parsed: dispatch only, its inputs, what each
step is given, the revocation and the artifact) and `frontend/e2e/release/mcp-sign-in-unit.spec.ts`
(the token file against the shared golden).
