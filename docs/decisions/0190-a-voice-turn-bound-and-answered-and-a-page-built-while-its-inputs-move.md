# 0190. A voice agent turn is bound by a variable header and answered within ElevenLabs' longest wait, and a page built while its inputs move is built again without an alarm

The reader agent names its conversation header as a dynamic-variable reference, waits up to 15 s
for our answer and has no backup model, so a voice agent turn is bound to its session and
answered with our cited reply; and a stored document whose inputs move while it is built keeps
the stamp it started from and is built again, so only a document that changed while its inputs
stood still is reported as an input the stamp misses.

Date: 2026-11-24. Status: accepted (the owner's "fix both" of 2026-11-24, after the release of
decisions 0184 to 0189). It amends [decision 0017](0017-voice-backend.md) (the agent's custom
LLM), [decision 0189](0189-lost-media-counted-a-recording-kept-with-its-row-refunds-on-the-hold-day-bands-as-read-and-a-bind-awaited.md)
(the bind wait and the header log) and [decision 0186](0186-pages-rebuilt-by-the-release-that-serves-and-a-deploy-that-never-goes-back.md)
(stored pages). The contracts are `docs/contracts/voice.md` (Unverified, items 1 to 3; the
agent, point 4) and `docs/contracts/monograph-document.md` (the stored English copy).

| For | Read |
|---|---|
| The voice binding and the custom LLM | [decision 0017](0017-voice-backend.md) |
| The header log that showed the template | [decision 0189](0189-lost-media-counted-a-recording-kept-with-its-row-refunds-on-the-hold-day-bands-as-read-and-a-bind-awaited.md) |
| Stored pages rebuilt by the release that serves | [decision 0186](0186-pages-rebuilt-by-the-release-that-serves-and-a-deploy-that-never-goes-back.md) |
| What is left | `docs/TECH_DEBT.md`: ElevenLabs behaviour not yet verified |
| Every decision, by group | [README.md](README.md) |

## Context

- **The header arrived as written.** Decision 0189's log showed every ElevenLabs request of the
  paid check of 2026-11-24 (run 45339662817) refused at the session record check with a
  27-character header not starting with `conv_`: the literal `{{system__conversation_id}}` that
  `voice/agent.py` wrote into `custom_llm.request_headers` as a plain string. ElevenLabs' pages
  list `{{...}}` substitution for system prompts, first messages and tool parameters, and the
  agent API types a dynamic-variable reference as `ConvAIDynamicVariable` with `variable_name`.
- **The answer came after ElevenLabs stopped waiting.** With the header as a reference
  (`{"variable_name": "system__conversation_id"}`, accepted by `PATCH /v1/convai/agents/{id}` and
  read back as stored), the next check (run 45343053992) was bound: three requests answered 200,
  each closed by ElevenLabs at 4.95 s after only our 0.7 s filler. The agent held
  `cascade_timeout_seconds` 4, the API's default ("Time in seconds before cascading to backup LLM.
  Must be between 2 and 15 seconds"), and with a custom LLM as primary ElevenLabs asks the same
  custom LLM again on a timeout. `backup_llm_config` was `default`, which ElevenLabs' cascading
  page says never falls back to its own models when a custom LLM is primary.
- **The unchanged-stamp alarm of Sanganeri was a race.** At 06:12 UTC on 2026-11-24 the stored
  document of Sanganeri Hand Block Printing was reported changed under an unchanged stamp. The
  post-deploy check publishes a Professor's fact on Sanganeri and retracts it after every release
  (`e2e/release/mcpContribution.ts`), which is why Sanganeri had 17 rebuilding reads in eight hours
  and its stored document is at version 55. A rebuild takes the stamp first and builds the document
  after, each read seeing what was committed when it ran, so a retraction committed between the
  two left content built after it under the stamp taken before; that stamp equalled the one already
  stored, and the alarm fired. A second rebuild in the same minute was a duplicate: its read had
  seen the copy stale, and its claim landed just after the first rebuild cleared `wantedAt`, since
  a claim never compared stamps. On the box the document built twice in one transaction, in three
  processes with different hash seeds, and from the stored or a fresh craft page snapshot was the
  same each time, and the stored copy equalled a fresh build.

## Decision

1. **The agent's header is a variable reference.** `voice/agent.py` writes
   `{CONVERSATION_HEADER: {"variable_name": "system__conversation_id"}}` (`CONVERSATION_ID_VARIABLE`),
   for the reader and the artisan agent alike.
2. **The agent waits ElevenLabs' longest and has no backup.** `cascade_timeout_seconds` is 15
   (`CASCADE_TIMEOUT_SECONDS`, the API's most) and `backup_llm_config` is
   `{"preference": "disabled"}` (`NO_BACKUP_LLM`), so no model but ours answers. The live reader
   agent was updated the same way through the agent API, its URL, key, model and four client tools
   read back unchanged.
3. **A rebuild reads the stamp again before it raises the alarm.** When `rebuild_document` stores a
   changed document under a stamp equal to the one held, it reads the stamp again: if it moved, the
   inputs moved while the document was built, the copy keeps the stamp it started from (so the next
   read builds it again) and the line is information; only a stamp that stood still is the error
   "an input the stamp misses moved". `craft_page_snapshots.rebuild_snapshots` does the same for a
   page snapshot.
4. **A read claims a rebuild only for a stale copy.** `claim_rebuild` takes the current stamp and
   claims when the copy is unclaimed and its stamp differs, or when a claim is older than
   `REBUILD_RETRY`; a read that saw the copy stale just before another rebuild finished claims
   nothing.

## Consequences

- The agent-only paid check (run 45343985030) was answered in one request of 10.1 s: "Let me check
  the sources... Ajrakh is a double-sided block-printed textile made by Khatri artisans. ...
  Sources: Edwards 2016; GI Journal 188; Ajrakh; Frater 2024." Its events are the fixture
  `backend/tests/voice/fixtures/agent_turn_events.json`. The voice call stays switched off
  (`VOICE_CALL_ENABLED` false) and `voice.transport` stays `RELAY` until the owner chooses the
  agent. A turn longer than 15 s is still cut by ElevenLabs; the register entry "ElevenLabs
  behaviour not yet verified" is rewritten to what is left.
- Sanganeri is still rebuilt after each release while the post-deploy check publishes and retracts
  its fact, which is the check's purpose; those rebuilds no longer raise a false alarm or run
  twice.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-24; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/voice/test_agent_provision.py`, `backend/tests/test_paid_checks.py` and
`backend/tests/db/test_stored_documents_db.py`.
