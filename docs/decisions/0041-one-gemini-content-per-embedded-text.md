# 0041. One Gemini content per embedded text

Date: 2026-11-17. Status: accepted.

## Context

Storing the first production knowledge pieces logged `The embedding route returned 1 vectors for 5
texts`. A read of production then showed every one of the 1,919 claims without a vector, so stored
search had run on its lexical ranking alone. `GeminiAdapter.embed` passed the texts to
`embed_content` as a list of strings. For `gemini-embedding-2`, google-genai 3.3.0 normalises the
contents with `t_contents`, which folds consecutive strings into the parts of one `Content`, and
the model returns one embedding for the whole content. A single text (the question at search time)
was unaffected, which is why answers still ran.

## Decision

1. `GeminiAdapter.embed` sends one `Content` with one text `Part` per text, which the SDK keeps
   apart, so the route returns one vector per text.
2. `tests/test_gemini_embedding.py` passes the adapter's request through the SDK's own
   `t_contents` and checks one vector per text; it fails on the old list of strings. It also pins
   the SDK behaviour that caused this: plain strings fold into one content.
3. After the deploy, `app.scripts.embed_craft_descriptors` and `app.scripts.embed_knowledge` run
   once on the box to fill the missing vectors; the nightly enrichment run keeps them filled.

## Consequences

- `checked_vectors` already refuses a count that does not match, so a future SDK change that folds
  texts again fails loudly at write time rather than storing wrong vectors.
