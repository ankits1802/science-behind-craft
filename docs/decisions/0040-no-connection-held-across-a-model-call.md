# 0040. No connection held across a model call

Date: 2026-11-17. Status: accepted.

## Context

The first production run of phase A (E2E run 43993673874) failed both known-answer questions with
"Something went wrong while answering". The server log shows `QueuePool limit of size 5
overflow 0 reached, connection timed out, timeout 30.00` from `router.load_routes`, reached from
`StoredKnowledgeSearch.search` inside a section's coverage check. Answers now run up to four
sections at once (decision 0032). Each section's stored search ran its first query, which checks a
connection out of the pool, and then embedded the question through the router, which needs a
second connection. Four sections, plus the answer's own work, held all five connections while each
waited for one more, so every section timed out together and `/api/answers/config` waited 25 s
behind them. Writing back a section's research (`indexing._fill`) and the craft resolver's
semantic step had the same shape.

`DATABASE_CONNECTION_LIMIT` stays 5 with no overflow: both API colours and the box scripts share
the Supabase session pooler, so a larger pool would trade this failure for the pooler's own limit.

## Decision

1. A caller never holds a pooled connection while it waits on the router. `app.core.db.
   release_connection(session)` commits a read-only session, which returns its connection; the
   session checks one out again on its next query.
2. `StoredKnowledgeSearch.search` embeds the question before its first query.
3. `indexing._fill` releases the connection before each embedding call, so writing back research,
   storing knowledge pieces and the nightly embedding job hold none while embedding.
4. `DatabaseCraftResolver._semantic` releases the connection before it embeds the question.
5. `tests/retrieval/test_connection_release.py` records each session's queries, commits and
   embedding calls and fails if an embedding call comes while a connection is held; all three
   failed before this change.
6. The production E2E bounds a craft tab click at 30 s and records why a click is refused (the
   page not answering a script, the tab moving, or what covers its centre, and Playwright's call
   log), so a stuck tab no longer spends the whole ten-minute run (plan finding 8a.3).

## Consequences

- The rule is in `docs/contracts/backend.md` under the AI router.
- `fill_descriptor_embeddings`, run only by the nightly script with nothing in parallel, still
  holds its connection while embedding.
