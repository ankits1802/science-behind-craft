# 0100. The Kutch Ajrakh craft page is the hand-built monograph, served as built

Date: 2026-11-19. Status: accepted. Overrides the craft page renderer (decisions 0071, 0095 and
0098) for one craft, Kutch Ajrakh; every other craft keeps it.

## Context

The owner approved a finished, hand-built Kutch Ajrakh page (the answer "How does Ajrakh work?"
and its monograph, built from the curation dossier by the scripts in the `_cons` working folder:
`build.py`, `build2.py`, `build3.py`, `kv.js`, `kv.css`) and asked for it to be the live Kutch
Ajrakh craft page exactly as it looks, now, not rebuilt in React.

## Decision

1. **The page is a static file.** It lives at `frontend/public/monographs/kutch-ajrakh/index.html`
   with its ten pictures in `img/` beside it. `CRAFT_MONOGRAPHS` in `frontend/next.config.ts` maps
   the slug `Kutch-Ajrakh` to that file, and a `beforeFiles` rewrite serves it at
   `/crafts/Kutch-Ajrakh` to every reader, signed in or not. Next.js matches rewrites without
   regard to case, so `/crafts/kutch-ajrakh` serves it too. The edition addresses
   (`/crafts/Kutch-Ajrakh/v1`) and every other craft keep the craft page renderer.
2. **Changed only to fit the app.** Line endings are LF, picture paths are absolute
   (`/monographs/kutch-ajrakh/img/...`), the brand goes to `/`, and each Ask next question is a
   link to `/ask?q=<question>&craft=Kutch-Ajrakh` instead of a demonstration toast, so a signed-out
   reader is sent to sign in as on any ask link. Content, design and animation are as approved.
   The citation texts keep their full `https://kalavigyan.vercel.app` addresses, since a copied
   citation needs one.
3. **The global headers apply.** The app's Content-Security-Policy sets no `script-src`,
   `style-src` or `font-src`, so the inline scripts and styles and the Google Fonts load; the
   pictures are `'self'`.
4. **This holds until the renderer matches it.** It is the Kutch Ajrakh page until the chapter
   renderer reproduces it. Removing the `Kutch-Ajrakh` entry from `CRAFT_MONOGRAPHS` returns the
   craft to the renderer.
5. **The dossier stays the source of facts.** `backend/app/data/curation/Kutch-Ajrakh.json` is
   still where the facts live. A dossier change does not reach this page by itself: rebuild the
   page from the `_cons` scripts, then copy it in again with the same four changes.

`e2e/craft-monograph-unit.spec.ts` checks the rewrite, the title, the pictures and the Ask next
links, and that other crafts are not rewritten.

## Ended (2026-11-20)

The React renderer of decision 0106 passed the parity proof at 360, 834 and 1440 in light and dark
(text, all 31 chapters, interactions; run 44617385866), so `/crafts/Kutch-Ajrakh` draws its stored
document like every other craft and the rewrite is gone. The approved file stays at
`/monographs/kutch-ajrakh/` as the parity reference, served with `X-Robots-Tag: noindex`;
`e2e/craft-monograph-unit.spec.ts` checks that arrangement.

