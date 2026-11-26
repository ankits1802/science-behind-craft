# 0247. The tool list as Anthropic's Connectors Directory reads it: every parameter typed, every tool titled, and descriptions that only describe

Every parameter of every tool the MCP server lists has a JSON Schema type, in both protocol eras.
Every tool carries its human title as `annotations.title` beside its hints. Every tool and parameter
description says what the tool does, takes and returns, its limits, who may call it and what it
costs, and nothing else: no order to the model, no other tool's name, no order of calls and no
pointer to a guide page, the playbook or a skill. That guidance stays where an agent already reads
it unaided: the server's instructions, the page playbook, the contributor skill and the tools'
results. `read_source` names the services it reads, with their documentation.

Date: 2026-11-26. Status: accepted (the lead's lane brief `ux-1126/directory-listing`, for the
owner's submission to the Connectors Directory). It amends
[decision 0111](0111-fewer-mcp-tools.md) (small schemas: a reference is now typed beside its `$ref`),
[decision 0203](0203-the-guide-handed-over-page-by-page-at-the-step-it-serves.md) (the guide handed
over at the step it serves: a description no longer names a guide page; the results still hand them)
and [decision 0230](0230-the-mcp-server-teaches-the-thinking-and-serves-the-context-the-authors-had.md)
(the playbook taught: a page-building tool's description no longer says where it sits in the
playbook; the playbook and the skill do). The contracts are `docs/contracts/knowledge-api.md`
(Small schemas), `open-work.md` (Guide pages) and `mcp-ask-and-upload.md` (Timeout).

| For | Read |
|---|---|
| The small schemas and the tool budget | [decision 0111](0111-fewer-mcp-tools.md) |
| The guide pages handed in results | [decision 0203](0203-the-guide-handed-over-page-by-page-at-the-step-it-serves.md) |
| The playbook and the owner's rule that the agent needs no dictation | [decision 0230](0230-the-mcp-server-teaches-the-thinking-and-serves-the-context-the-authors-had.md), [decision 0240](0240-an-agent-reads-a-page-s-brief-in-one-call-and-the-acceptance-run-tells-the-whole-story.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **What the directory flagged.** Step 2 of "Submit an MCP connector" read the live `tools/list` on
  2026-11-26. It blocked the submission on five parameters without a `type`: `proposal` on
  `propose_dataset`, `propose_source` and `propose_structure`, and `identity` and `access` on
  `supply_source`. Each was a bare `{"$ref": ...}`, which Pydantic emits for a required model field.
  More properties, on 13 tools in all, had no type and were not flagged, because they hid under an
  `anyOf` of a reference and null, a discriminated union, or an `anyOf` of several simple types. The file
  argument's `digest.algorithm` was `{"const": "sha-256"}` alone. It also suggested, on all 26 tools,
  "Add `annotations.title`", and on `read_source`, "Reference the target API docs in the
  description".
- **What step 6 asks the owner to tick.** "Tool descriptions contain no instructions about model
  behavior, other tools, or external instruction sources, and no hidden or encoded text."
  Anthropic's review criteria (claude.com/docs/connectors/building/review-criteria.md, read on
  2026-11-26) say: "Describe what the tool does, and don't tell Claude how to behave." The Software
  Directory Policy (2.D to 2.G) forbids coercing Claude into calling other tools and directing it to
  pull behavioural instructions from external sources. The descriptions did both: "Read get_facts
  first", "preview_page, then propose_page", "Ask the person first ... never fill the declaration in
  for them", "Tell a person a fact is on the page only when readers.shown is true", "Follow the page
  playbook (playbook/1)", "guide hands over ...", "next_step says what to fix", "say so once, then go
  on building", "Search it before you fill a spec by hand", and imperatives to "you" throughout.
- **What must not be lost.** By the owner's rule (decisions 0230, 0240) a contributor's AI reaches
  the Kutch Ajrakh bar unaided. Almost all of that guidance already lived in the server's
  instructions, the playbook and the contributor skill. The descriptions repeated it.

## Decision

1. **Every parameter typed, once for every tool.** `api/mcp_schemas.typed` runs after `compact` on
   every input schema. It gives each property, and each array's `items`, that has no `type` the
   types its options resolve to through `$defs` (`schema_types`, the same reading the output schemas
   use), with `null` last. A model gets `object`, a choice `string`, a nullable reference
   `["object", "null"]`, a discriminated union `object`, and `int | str | None`
   `["integer", "string", "null"]`. The `$ref`, `anyOf` and discriminator stay beside it, so
   validation is unchanged. `mcp_files.file_schema` types `algorithm`. Both protocol eras list the
   same schemas; the 2026-07-28 era adds the typed file arguments.
2. **Every tool titled.** `Tool.listed` puts the tool's title in `annotations.title`, before
   `readOnlyHint`, `destructiveHint` and `openWorldHint`. The top-level `title` stays.
3. **Descriptions that only describe.** Every tool and parameter description was rewritten in the
   third person ("Proposes ...", "Reads ...", "For Admins: ..."). Each keeps every fact needed to
   call the tool correctly: limits, units, refusals, outcomes, scopes, allowances and costs. None
   names another tool, a guide page (`playbook/1`, `cookbook/1`, `design-critique/1`), a guide, a
   skill, `next_step` or a `kalavigyan://` resource other than a component kind's JSON Schema. None
   addresses the model as "you", orders calls with "first", or opens a sentence or a clause after a
   colon with an order. A value's source is told as a noun ("by the ids the page's brief lists",
   "the shape a page draft's add takes") or dropped ("A slug from find_crafts" is now "A craft's
   slug"). The `read_token` gate, the declaration that is the person's own and `readers.shown` are
   described as facts of the tool's behaviour. The results (`nextStep`, `guide`, notices) keep
   guiding, as decision 0203 has them.
4. **Where the guidance lives now.** Nothing an agent relied on is lost, and all of it is reachable
   from the initialize instructions, which name the playbook (`playbook/1`, also handed with a page's
   coverage) and the contributor skill (`kalavigyan-contributor`):

   | Taken out of the description of | Where an agent reads it |
   |---|---|
   | `get_page`, `get_facts`: the brief first, then whole facts by id | the instructions; playbook step 1; skill, The tools, in order, step 3 |
   | `list_components`: search the library before filling a spec by hand; the cookbook names each kind's tool | skill step 4; playbook step 3 (`cookbook/1`) |
   | `ask`: link the answer or draw it by the answer kit; name KalaVigyan and the Centre | skill, Drawing in KalaVigyan's design and Questions readers asked; the instructions |
   | `supply_source`: test each quote with `read_source`; cite it as `cite_as` gives it | skill, Sources only you can read |
   | `report_site_gap`: say it once, then go on building | the instructions; playbook, When the site falls short; skill, Never; the tool's own `nextStep` |
   | `get_proposal`: tell the person a fact is on its page only when `readers.shown` is true | skill, Never (added here) |
   | `propose_facts`, `propose_source`: read the facts before proposing; which tasks a new source closes | skill step 3 and Facts that lost their sources |
   | `propose_structure`, `compose_component`: what the composer reads; a helper beside coded figures | playbook steps 5 and 6 |
   | `propose_dataset`: the datasets guide | the datasets skill and the datasets reference |
   | `edit_draft`, `preview_page`, `propose_page`: the playbook's steps 4, 9 and 10, the critique rubric, `read_pictures`, the design pages before the opening components, rounds | playbook steps 4, 9 and 10 and its note on the `read_token`; the results' `nextStep` and `guide` |
   | `give_pictures`: ask the person, in their words; never fill the declaration in | skill, Pictures and Never; playbook, What to ask the person; the instructions |
   | `check_pictures`, `list_field_photos`: look at each picture; place a photograph by its label | skill, Checking pictures and Pictures |
   | `review_queue`, `stage_reviews`: the admin guide; re-reading a source | skill, Removing and editing published content (Admins) |

   The instructions did not change: at 2,579 of their 2,600 bytes they already named both homes.
5. **`read_source` names what it reads.** Its description names the publisher's page at the https
   address given, the Unpaywall REST API (https://unpaywall.org/products/api) for a DOI's open copy,
   the Wayback Machine's Availability API (https://archive.org/help/wayback_api.php) for an archived
   copy, and Save Page Now (https://web.archive.org/save) for `archive`, as `sources/scholarly/unpaywall`,
   `services/source_lookup_archive` and `sources/wayback_save` call them.
6. **The prompts stay prompts.** The seven prompts keep their steps. None is a tool, and no prompt's
   description is a tool's.
7. **AI-made media, checked and not changed.** No MCP tool call makes an AI model generate an image,
   video or audio, during the call or in the background. Traced from `api/mcp_tools.py`: no MCP
   module imports `app.media`, `app.voice`, `providers/media_router` or the film, listen and media
   dependencies. The answer pipeline `ask` runs (`api/mcp_ask_run.run_to_the_end`) calls text models
   only (`providers/answer_routes.py`). Its concept pictures are searched, not made
   (`services/simulation_builder._searched_picture`, `services/section_images.section_images` over
   `live.web_images`: Wikimedia Commons, Openverse and SearXNG in `sources/images/registry.py`). Its
   figures and art kit are drawn from data, and its molecules come from PubChem conformers.
   `give_pictures` takes pictures a person made, an AI illustration among them as made elsewhere and
   declared, and screens each with a vision model that reads it (`providers/picture_vision.screen_with_vision`).
   `preview_page` with `read_pictures` reads the preview's pictures with a vision model
   (`providers/design_vision.read_design`). `compose_component` builds data from PubChem, and
   `refresh_pages` rebuilds documents. AI media is made in one place only:
   `providers/media_router.MediaRouter._produce` (`generate_image`, `generate_audio`, `start_video`).
   It is reached from the site's own routes alone: `POST /media/jobs` through `media/jobs.submit_job`
   and the worker `media/runner`, the answer's Listen (`api/routes/listen.py`, ElevenLabs or Gemini
   speech in `voice/listen_voices.py`), its film score (`api/routes/film.py`, `voice/film_score.py`),
   and the voice conversations (`voice/relay.py`, `voice/artisan_relay.py`). One link remains: an
   answer `ask` stores can be listened to, or its film scored, on the site by the person who asked
   (`voice/listen_store.py` and `voice/film_store.py` read only `Answer.userId == user`), when they
   press Listen or the music toggle there. That is the site, not the MCP server, and nothing here
   changes it; the owner decides how to answer the directory's tick.
8. **The owner's words over the design skill.** None: no user interface changed.
9. No migration and no new dependency.

## Consequences

- Tested both ways, in `backend/tests/mcp/test_directory_listing.py` over the checks in
  `backend/tests/mcp/listing_policy.py`. Types: both eras' lists, an Admin's with the file arguments,
  hold no property without a type. The five flagged parameters are `object`. A sample of a reference,
  a nullable one, a choice, a discriminated union and a union of simple types leaves five untyped
  properties through `compact` alone and none through `input_schema`, each with its type. Titles:
  every listed tool's `annotations.title` is its title, beside boolean hints. A listing without the
  annotation, or with another title, is refused. Descriptions: every listed tool and parameter
  description in both eras passes. Eleven sentences quoted from the old descriptions are each
  refused. Five plain descriptions pass ("GIF as its first frame", "its first sheet", "the first
  screen"). `read_source` names its four services with their addresses. The guidance taken out is in
  the playbook and the skill, and the instructions name both. No prompt is a tool. Run over the old
  list, the same checks fail all 30 tools on their descriptions and their titles, and 13 on their
  types.
- Tests that encoded the old behaviour changed to the new one:
  `test_playbook_cookbook.py` (a page-building tool's place in the playbook is now told by the
  playbook or the skill and named in the instructions or the playbook, never in its description),
  `test_review_tools.py` (the admin guide is named by the skill, not the admin tools),
  `test_give_pictures.py` (the description states the declaration is the person's own; "never fill"
  is the skill's), `test_mcp_preview_critique.py` (the rubric's address is the playbook's),
  `test_mcp_body_names.py` (a bundle points to a page draft's add), and `test_admin_reports.py`,
  `test_mcp_source_tools.py` and `test_mcp_work.py` (the listed annotations carry the title).
- The contributors' list held 75,986 bytes of input schemas and descriptions and 84,456 in all
  before; it holds 75,209 and 84,577 now. The descriptions shrank from 25,209 bytes to 23,512, and the
  types and titles added the rest. An Admin's list holds 83,956 and 94,556. `test_tool_budget.py`
  is unchanged.
- For the owner: the step-2 flags should clear once this release is live. Step 6's tick on AI media
  is the owner's call on the finding above.
- Left as they are: the server's instructions still guide (they are not a tool description), and the
  results keep `nextStep`, `guide` and notices.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
