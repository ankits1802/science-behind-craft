# 0211. A picture from a shop, a stock agency or an auction is not shown, whatever its title names

A searched picture is left out when its page or image is on a shop's subdomain or a store domain,
on a stock agency or an auction, under a store's or an auction lot's path, or when its title sells
it. The rule reads the same three things it read before (the page address, the image address and
the title), at search and when a stored picture is served, so nothing stored is deleted and no
model call is added.

Date: 2026-11-25. Status: accepted (the owner, 2026-11-25: "fix the #1", the shop pictures of the
measured answer run). It amends [decision 0080](0080-claim-ledger.md) (no picture from a shop,
marketplace or social site) and [decision 0207](0207-a-searched-picture-names-its-craft-s-world-and-a-stored-one-that-does-not-is-not-served.md)
(a searched picture names its craft's world). The contract is `docs/contracts/explainer.md`
(Pictures and terms as served).

| For | Read |
|---|---|
| The shop and social rule it amends | [decision 0080](0080-claim-ledger.md) |
| The craft-world rule it follows | [decision 0207](0207-a-searched-picture-names-its-craft-s-world-and-a-stored-one-that-does-not-is-not-served.md) |
| Why no model call is added | [decision 0165](0165-answers-counted-as-settled-asked-as-asked.md) |
| The design rule: no stock, shopping or AI imagery | `.claude/skills/kalavigyan-design`, principle 9 |
| Every decision, by group | [README.md](README.md) |

## Context

- **Decision 0207 let shop listings through.** Once a searched picture had to name its craft's
  world in its title, the farm, fruit and wallpaper photographs were refused, and the measured run
  on release 12607d72 (45565723558, Kutch Ajrakh, four questions) showed in their place
  "online Ajrakh Tussar Silk Saree with Natural Dyed Indigo | Gaatha" and "Ajrakh Cotton Scarf Red
  Floral | Star Medallion Print | Gaatha", both from `shop.gaatha.com`: they name Ajrakh, so the
  world rule keeps them, and the shop rule missed them.
- **What the shop rule read.** `services/picture_sites.blocked_picture` refused a registrable
  site named in `BLOCKED_PICTURE_SITES`, a `buy`, `cart`, `checkout`, `product`, `products`,
  `shop` or `store` path segment, a `/collections/<name>` listing and a title starting "Buy" or
  "Shop". It never read the labels below the site (`shop.gaatha.com`), the top-level domain
  (`aham.store`), the stock agencies or the auctions.
- **What production held.** The searched pictures stored against claims (`MediaRef` with a `TEXT`
  link, read on the box on 2026-11-25) included, besides the Gaatha pair, product pages under
  `/products/` and `/product/` (already refused), `aham.store`, stock agencies (Alamy, Getty
  Images, Shutterstock, Stockcake), auctions and dealers (Invaluable, Trocadero, an antiques
  dealer, a rug dealers' market, Saatchi Art), and titles such as "Buy … Online at Best Price",
  "… Paintings Online", "At Auction: …", "16 Bidar Fort Stock Photos …" and "… Royalty-Free
  Images, Stock Photos …".

## Decision

1. **A sale host is refused.** A page or image whose host has a `buy`, `shop`, `shopping`,
   `stock` or `store` label below its registrable site (`shop.gaatha.com`, `stock.adobe.com`), or
   whose site ends in one (`aham.store`), is not shown (`SALE_HOST_LABELS`). A label is compared
   whole, so `shopnews.example.org` is not refused.
2. **The stock agencies and the auctions join the maintained list.** `BLOCKED_PICTURE_SITES` adds
   123RF, 1stDibs, Alamy, an antiques dealer seen in the store (`aljantiques`), Artsy, Catawiki,
   Depositphotos, Dreamstime, Freepik, Getty Images, Invaluable, iStock, LiveAuctioneers, Pexels,
   Pixabay, RugRabbit, Saatchi Art, Shutterstock, Stockcake, Trocadero, Unsplash, Vecteezy and
   WorthPoint.
3. **Two more path segments.** `stores` and `auction-lot` (and `listing`) join `SHOP_PATH_SEGMENTS`;
   `item` does not, because the V&A's collection pages use it.
4. **A title that sells is refused** (`SALE_TITLE`): one starting "Buy", "Shop" or "Online"; "online
   at", "online from", "online in" or "online shopping"; "Online" closing the title or a part of it
   (before `|`, a dash or an ellipsis); "best price"; "for sale" or "on sale"; "at auction"; "stock
   photos", "stock images", "stock pictures" or "stock footage"; "royalty-free". A title that names
   what the picture shows keeps it: "an online exhibition of the Dhamadka block printers" and
   "Shopkeepers of Bhuj selling ajrakh" are shown.
5. **Where it applies.** As before, at search (`section_images.shown_candidates`) and on every read
   of a stored picture (`section_images.stored_items`), so the Gaatha pair already stored against
   Kutch Ajrakh's claims stops being served without a row deleted. The stored read holds every
   picture to it, a curator's pick included, as decision 0080's rule already did; none of the
   curators' picks held on 2026-11-25 (Wikimedia Commons, Flickr and the Met) is on a sale host.

## Consequences

- No model call or input token is added to an answer.
- A sale page whose address and title carry none of these signs still passes on its words alone
  (a dealer's page under an ordinary path with a descriptive title); the vision check that waits
  on the owner (`docs/TECH_DEBT.md`, Relevance is by text only) would catch it.
- `BLOCKED_PICTURE_SITES` stays maintained by hand: a new shop or agency seen in a measured run
  joins it in the change that sees it.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/ledger/test_picture_sites.py`.
