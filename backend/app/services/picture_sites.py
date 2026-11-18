from __future__ import annotations

import re
from urllib.parse import urlsplit

from app.research.images import site_of

__all__ = ["BLOCKED_PICTURE_SITES", "SHOP_LISTING_SEGMENTS", "SHOP_PATH_SEGMENTS", "blocked_picture"]

BLOCKED_PICTURE_SITES = frozenset(
    {
        "ajio",
        "alibaba",
        "alicdn",
        "aliexpress",
        "amazon",
        "aurelia",
        "azafashions",
        "biba",
        "cbazaar",
        "cdninstagram",
        "craftsvilla",
        "ebay",
        "ebayimg",
        "etsy",
        "etsystatic",
        "exportersindia",
        "fabindia",
        "facebook",
        "fbcdn",
        "fbsbx",
        "festivefolks",
        "flipkart",
        "flixcart",
        "gitagged",
        "globaldesi",
        "gocoop",
        "houseofelegance",
        "indiamart",
        "indianroots",
        "instagram",
        "itokri",
        "jaypore",
        "jiomart",
        "kalkifashion",
        "kankatala",
        "koskii",
        "lashkaraa",
        "licdn",
        "limeroad",
        "linkedin",
        "media-amazon",
        "meesho",
        "mirraw",
        "myntra",
        "myshopify",
        "nalli",
        "nykaa",
        "nykaafashion",
        "ogaan",
        "okhai",
        "paytmmall",
        "peachmode",
        "perniaspopupshop",
        "pinimg",
        "pinterest",
        "pothys",
        "quora",
        "rangriti",
        "redd",
        "reddit",
        "sharechat",
        "shein",
        "shopclues",
        "shopify",
        "shopsy",
        "snapchat",
        "snapdeal",
        "ssl-images-amazon",
        "strandofsilk",
        "suta",
        "taneira",
        "tatacliq",
        "temu",
        "threads",
        "tiktok",
        "tilfi",
        "tjori",
        "tradeindia",
        "tumblr",
        "twimg",
        "twitter",
        "unnatisilks",
        "utsavfashion",
        "walmart",
        "weaverstory",
        "wforwoman",
        "x",
        "youtu",
        "youtube",
        "ytimg",
    }
)
SHOP_PATH_SEGMENTS = frozenset({"buy", "cart", "checkout", "product", "products", "shop", "store"})
SHOP_LISTING_SEGMENTS = frozenset({"collections"})
SHOP_TITLE = re.compile(r"^\s*(?:buy|shop)\b", re.IGNORECASE)


def blocked_picture(*, page_url: str, image_url: str, title: str) -> bool:
    if SHOP_TITLE.match(title):
        return True
    return any(_shop_or_social(url) for url in (page_url, image_url))


def _shop_or_social(url: str) -> bool:
    parts = urlsplit(url)
    site = site_of(parts.hostname or "")
    if site is not None and site.split(".")[0] in BLOCKED_PICTURE_SITES:
        return True
    segments = [segment.casefold() for segment in parts.path.split("/") if segment]
    return bool(set(segments) & SHOP_PATH_SEGMENTS) or _shop_listing(segments)


def _shop_listing(segments: list[str]) -> bool:
    return len(segments) == 2 and segments[0] in SHOP_LISTING_SEGMENTS
