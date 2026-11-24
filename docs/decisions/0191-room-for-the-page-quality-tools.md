# 0191. The MCP tool list has room for the page-quality tools

The MCP server may list up to 32 tools to a contributor, with 100 KB of input schemas and
descriptions and 200 KB in all, and an Admin four more tools within 108 KB of input, so the tools
that bring every page built over MCP to the Kutch Ajrakh standard can be added.

Date: 2026-11-24. Status: accepted (the owner: "increase the limit ... Paginate the instructions if
required", after judging the Sanganeri Hand Block Printing page built over MCP far below Kutch
Ajrakh). It amends [decision 0111](0111-fewer-mcp-tools.md) (the list's budget) and
[decision 0170](0170-review-over-mcp-staged-and-pages-refreshed-now.md) (the Admin's budget). The
contract is `docs/contracts/knowledge-api.md` (the tools and the list's budget).

| For | Read |
|---|---|
| Why the list was cut to 22 tools and 60 KB | [decision 0111](0111-fewer-mcp-tools.md) |
| The Admin tools and their own budget | [decision 0170](0170-review-over-mcp-staged-and-pages-refreshed-now.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- Decision 0111 cut the list from 42 tools to 21 to keep a client's context small, and
  `tests/mcp/test_tool_budget.py` held it at 22 tools, 60 KB of input and 120 KB in all. On
  2026-11-23 it held 61,316 of 61,440 bytes of input, so no tool could be added without cutting
  another's guidance.
- The page-quality work needs new tools: placing open-licence pictures with their credit,
  withdrawing or replacing a contributor's own component, drawing a map and timeline from the
  site's geodata, rebuilding a family's flagship interactive on a craft's own facts, and seeing
  the rendered preview.

## Decision

1. **The budget is 32 tools, 100 KB of input and 200 KB in all** for a contributor, and an Admin's
   list four more tools within 108 KB of input; the test holds both.
2. **Long guidance is paged.** A tool whose guidance outgrows its description points to a served
   reference, as the contributor skill's references already are, rather than growing the list.

## Consequences

- A client reads up to about 40 KB more of the list than before; the list still names no
  component kind, so a new kind never grows it.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-24; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by `backend/tests/mcp/test_tool_budget.py`.
