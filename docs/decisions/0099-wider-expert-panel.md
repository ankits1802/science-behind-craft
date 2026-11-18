# 0099. The expert panel searches its own fields, calls each seat on its own, seats up to 12 at Expert, and hears the artisan from field transcripts

Date: 2026-11-19. Status: accepted. Extends decision 0046 (the expert panel); keeps decision 0080
(the claim ledger) as it is; the add-on route stays on Claude Sonnet 5.5 (decision 0089).

## Context

The owner wants Expert answers to show many more expert perspectives. The panel was built
(decision 0046) but was nearly silent on real answers. It offered only the claims the section's
blocks did not yet cite, so on a curated craft, where the section cites nearly every stored claim,
the seats had no evidence and no call was made. All seats shared one call. No seat looked for
evidence in its own field, and the artisan's seat never spoke.

## Decision

1. **Seat evidence of its own.** Each speaking seat runs one stored search of its own
   (`services/seat_search.py`) through the answer's retriever (`SessionScopedSearch`, now on
   `BuilderTools.retriever`): the craft, the answer's mode, and a text made of the question, the
   craft name, the seat's label and its fields' descriptions. Of the claims found, the seat keeps
   up to 6 fact-level stored claims the section does not cite and that cite a source of one of its
   `SeatBrief.source_kinds`. No live search, no fetch and no new claim: stored evidence and the
   existing retrieval only. The seat may still cite the section's claims alongside its own, which
   are offered after them.
2. **One call per seat.** Each offered seat gets its own `COMPOSE` call (`compose_take`), all at
   once, and up to 3 take sentences each. A seat whose offer holds nothing the section does not
   cite is not called. A failed or off-schema reply drops that seat's view only. Differences are
   proposed in one final pass over the seats that spoke (`compose_differences`), asked only when
   two offered statements on one concept cite no common source; the pairing rules of 0046 are
   unchanged. Every take sentence still passes the prose checks, and a view that adds nothing new
   is still hidden.
3. **More seats at Expert.** `DepthPolicy.max_experts` for Expert is 12 (was 10); Basic 2 and
   Detailed 4 are unchanged. At Expert (`WIDENED_DEPTHS`) a section hears the seated experts first
   and then every other panel seat whose fields hold the section's field, up to 12
   (`panel_seats`). At Basic and Detailed the seats are the understanding step's, as before. The
   live reading order (`seat_reading_kinds`) follows the same seats.
4. **The artisan speaks from field transcripts.** When `ARTISAN` is a voiced seat of the section
   (`voiced_seats`: seated, or any section of its fields at Expert), `FIELD_VOICES_ENABLED` is on
   and the retriever returns field transcript chunks of the craft for the question (chunk ACLs
   `PUBLIC` and `SIGNED_IN`), the seat quotes up to 3 stored claims whose citation quotes those
   chunks and whose speaker is recorded as an artisan on a recording shown for the craft
   (`services/artisan_seat.py`). The sentence is written by the server, not the model, as one
   artisan's account with the speaker's recorded name, craft and district, and cites the claim
   and its transcript source. The quoted words pass `prose_problems`; the attribution comes from
   the recording. With no such transcript the seat is not shown and nothing on screen says so.
   The seat never takes part in a difference.
5. **Time.** The builder waits 90 s (was 45 s), within `BUILDER_WAIT_MAX_SECONDS`.
6. **Spend.** There are no spend or token caps in the builder; each seat call, the difference
   pass and the seat searches' embeddings are recorded as the answer's spend as every other call.
7. **Frontend.** `frontend/lib/explainerExperts.ts` already parses any listed seat, `ARTISAN`
   among them, a take of one or more sentences and any number of views, and the panel renderer
   draws each view it is given; nothing changed there.

## Consequences

- A curated section now hears every seat that finds unshown evidence in its own field, so Expert
  answers show up to one view per panel seat of the field (at most 7 seats share any one field).
- An Expert section makes up to one call per speaking seat plus one difference pass, so builder
  spend per Expert answer rises with the number of sections and seats.
- The ledger still decides what is new across the answer: a seat citing only claims an earlier
  section showed is dropped there, and two seats resting on one new claim keep the first.
- The old single-call API (`PanelAsk`, `compose_takes`, `panel_message`, `panel_schema`,
  `parsed_panel`, `PanelDraft`) is removed.
