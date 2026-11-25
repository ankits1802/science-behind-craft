from __future__ import annotations

import re
from urllib.parse import urlsplit

from app.research.images import site_of

__all__ = [
    "BLOCKED_PICTURE_SITES",
    "SALE_HOST_LABELS",
    "SALE_TITLE",
    "SHOP_LISTING_SEGMENTS",
    "SHOP_PATH_SEGMENTS",
    "blocked_picture",
]

BLOCKED_PICTURE_SITES = frozenset(
    {
        "123rf",
        "1stdibs",
        "ajio",
        "alamy",
        "alibaba",
        "alicdn",
        "aliexpress",
        "aljantiques",
        "amazon",
        "artsy",
        "aurelia",
        "azafashions",
        "biba",
        "catawiki",
        "cbazaar",
        "cdninstagram",
        "craftsvilla",
        "depositphotos",
        "dreamstime",
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
        "freepik",
        "gettyimages",
        "gitagged",
        "globaldesi",
        "gocoop",
        "houseofelegance",
        "indiamart",
        "indianroots",
        "instagram",
        "invaluable",
        "istockphoto",
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
        "liveauctioneers",
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
        "pexels",
        "pinimg",
        "pinterest",
        "pixabay",
        "pothys",
        "quora",
        "rangriti",
        "redd",
        "reddit",
        "rugrabbit",
        "saatchiart",
        "sharechat",
        "shein",
        "shopclues",
        "shopify",
        "shopsy",
        "shutterstock",
        "snapchat",
        "snapdeal",
        "ssl-images-amazon",
        "stockcake",
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
        "trocadero",
        "tumblr",
        "twimg",
        "twitter",
        "unnatisilks",
        "unsplash",
        "utsavfashion",
        "vecteezy",
        "walmart",
        "weaverstory",
        "wforwoman",
        "worthpoint",
        "x",
        "youtu",
        "youtube",
        "ytimg",
    }
)
SHOP_PATH_SEGMENTS = frozenset(
    {"auction-lot", "buy", "cart", "checkout", "listing", "product", "products", "shop", "store", "stores"}
)
SHOP_LISTING_SEGMENTS = frozenset({"collections"})
SALE_HOST_LABELS = frozenset({"buy", "shop", "shopping", "stock", "store"})
SALE_TITLE = re.compile(
    r"^\s*(?:buy|shop|online)\b"
    r"|\bonline\s+(?:at|from|in|shopping)\b"
    r"|\bonline\s*(?:[|–—-]|\.{3}|…|$)"
    r"|\bbest\s+prices?\b"
    r"|\b(?:for|on)\s+sale\b"
    r"|\bat\s+auction\b"
    r"|\bstock\s+(?:photos?|images?|pictures?|footage)\b"
    r"|\broyalty[-\s]free\b",
    re.IGNORECASE,
)


def blocked_picture(*, page_url: str, image_url: str, title: str) -> bool:
    if SALE_TITLE.search(title):
        return True
    return any(_shop_or_social(url) for url in (page_url, image_url))


def _shop_or_social(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").casefold()
    site = site_of(host)
    if site is not None and (site.split(".")[0] in BLOCKED_PICTURE_SITES or _sale_host(host, site)):
        return True
    segments = [segment.casefold() for segment in parts.path.split("/") if segment]
    return bool(set(segments) & SHOP_PATH_SEGMENTS) or _shop_listing(segments)


def _sale_host(host: str, site: str) -> bool:
    site_labels = site.split(".")
    below = host.split(".")[: -len(site_labels)]
    return site_labels[-1] in SALE_HOST_LABELS or bool(set(below) & SALE_HOST_LABELS)


def _shop_listing(segments: list[str]) -> bool:
    return len(segments) == 2 and segments[0] in SHOP_LISTING_SEGMENTS
