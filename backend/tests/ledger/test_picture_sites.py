import pytest

from app.research.images import ImageCandidate
from app.services.picture_sites import blocked_picture
from app.services.section_images import SectionImages

from ..images.fakes import RETRIEVED, FakeContexts, FakeMediaStore, FakeSource, searched_by
from ..images.test_section_images import STICKY, ask


def at(page_url: str, image_url: str | None = None, title: str = "Ajrakh cloth") -> ImageCandidate:
    return ImageCandidate(
        provider="searxng",
        page_url=page_url,
        image_url=image_url or f"{page_url.rstrip('/')}/picture.jpg",
        original_url=image_url or f"{page_url.rstrip('/')}/picture.jpg",
        title=title,
        site="pictures",
        retrieved_at=RETRIEVED,
    )


@pytest.mark.parametrize(
    "page_url",
    [
        "https://www.itokri.com/kutch-ajrakh-dress",
        "https://www.jiomart.com/p/ajrakh-saree",
        "https://houseofelegance.in/indigo-duo",
        "https://gitagged.com/ajrakh",
        "https://festivefolks.com/ajrakh",
        "https://www.instagram.com/p/Cx1",
        "https://m.facebook.com/ajrakh",
        "https://in.pinterest.com/pin/1",
        "https://www.amazon.in/dp/B0",
        "https://www.flipkart.com/ajrakh",
        "https://www.etsy.com/listing/1",
        "https://www.meesho.com/ajrakh",
        "https://ajrakh-store.myshopify.com/collections/all",
        "https://craftmark.example.org/products/ajrakh-stole",
        "https://weavers.example.org/shop/ajrakh",
        "https://www.fabindia.com/ajrakh-kurta-10712345",
        "https://www.gocoop.com/ajrakh-saree",
        "https://www.exportersindia.com/ajrakh.htm",
        "https://www.tjori.com/ajrakh",
        "https://www.biba.in/ajrakh",
        "https://www.kalkifashion.com/ajrakh",
        "https://www.unnatisilks.com/ajrakh",
        "https://www.peachmode.com/ajrakh",
        "https://www.youtube.com/watch?v=abc",
        "https://anystore.in/collections/ajrakh-dupatta",
        "https://weavers.example.org/store/ajrakh",
        "https://shop.gaatha.com/ajrakh-saree-natural-dyed-tussar-silk-indigo",
        "https://aham.store/blogs/journal/ajrakh-saree-guide",
        "https://stock.adobe.com/images/ajrakh-block/123",
        "https://www.alamy.com/india-gujerat-rann-of-kutch-crafts-dhamadka-village",
        "https://www.gettyimages.com/photos/bidar-fort",
        "https://www.shutterstock.com/search/indian-natures",
        "https://stockcake.com/i/indian-pigment-artistry_2777266_1416709",
        "https://www.invaluable.com/auction-lot/indian-madhubani-folk-art-mixed-media-painting",
        "https://trocadero.com/stores/galeriehafner/items/1458245/bidri-ware-spitoon",
        "https://www.saatchiart.com/en-de/art/Mixed-Media-Kalamkari-traditional-Indian-art/3114227/view",
    ],
)
def test_a_shop_marketplace_or_social_page_is_never_shown(page_url: str) -> None:
    found = at(page_url)
    assert blocked_picture(page_url=found.page_url, image_url=found.image_url, title=found.title)


def test_a_shop_s_image_host_or_a_buy_title_is_never_shown() -> None:
    assert blocked_picture(
        page_url="https://blog.example.org/ajrakh",
        image_url="https://i.pinimg.com/originals/ab/cd/ajrakh.jpg",
        title="Ajrakh",
    )
    assert blocked_picture(
        page_url="https://blog.example.org/ajrakh",
        image_url="https://blog.example.org/a.jpg",
        title="Buy Ajrakh",
    )


@pytest.mark.parametrize(
    "page_url",
    [
        "https://commons.wikimedia.org/wiki/File:Ajrak_Printing_Materials_1.jpg",
        "https://www.flickr.com/photos/nevilzaveri/123",
        "https://collections.vam.ac.uk/item/O132500/",
        "https://www.metmuseum.org/art/collection/search/1",
        "https://exhibitions-khamir.org/ajrakh/art-of-ajrakh",
        "https://harvardartmuseums.org/collections/object/229947",
        "https://india.mongabay.com/2019/10/water-woes-kutchs-age-old-ajrakh-craft",
        "https://www.dsource.in/resource/ajrakh-block-printing-kutch-gujarat/making-process",
        "https://www.mykutch.org/crafts/ajrakh.html",
        "https://www.shopnews.example.org/ajrakh-printers-of-dhamadka",
    ],
)
def test_museum_archive_and_open_photo_pages_are_shown(page_url: str) -> None:
    found = at(page_url)
    assert not blocked_picture(page_url=found.page_url, image_url=found.image_url, title=found.title)


@pytest.mark.parametrize(
    "title",
    [
        "online Ajrakh Tussar Silk Saree with Natural Dyed Indigo | Gaatha",
        "Buy Kutch Ajrakh Handblock Printed Cotton Dress Material Online at Best Price",
        "Bihar Roots - Authentic Mithila & Madhubani Art Paintings Online",
        "Ajrakh Dupatta Online - Handloom House",
        "At Auction: INDIAN MADHUBANI FOLK ART MIXED MEDIA PAINTING",
        "Antique Bidri Ware Huqqa Base for Sale",
        "16 Bidar Fort Stock Photos, High-Res Pictures, and Images - Getty Images",
        "2,426,167 Indian Natures Royalty-Free Images, Stock Photos ...",
    ],
)
def test_a_picture_titled_as_a_sale_or_a_stock_photo_is_never_shown(title: str) -> None:
    assert blocked_picture(
        page_url="https://blog.example.org/ajrakh", image_url="https://blog.example.org/a.jpg", title=title
    )


@pytest.mark.parametrize(
    "title",
    [
        "Workers beating the vats at an indigo factory in Allahabad in 1877",
        "Ajrakh Block Printing | Crafts of Kutch - Handicrafts of Kutch",
        "Water woes: Kutch's age-old Ajrakh craft faces its nemesis, once again",
        "Kutch Ajrakh: an online exhibition of the Dhamadka block printers",
        "Shopkeepers of Bhuj selling ajrakh in the old market, 1960",
    ],
)
def test_a_picture_titled_by_what_it_shows_is_shown(title: str) -> None:
    assert not blocked_picture(
        page_url="https://blog.example.org/ajrakh", image_url="https://blog.example.org/a.jpg", title=title
    )


async def test_section_pictures_never_offer_a_shop_s_picture() -> None:
    shop = at("https://www.itokri.com/sticky-gums-printing", title="Printing with sticky gums")
    museum = at("https://collections.vam.ac.uk/item/O1/", title="Printing with sticky gums, a museum sample")
    store = FakeMediaStore({STICKY.claim_id: STICKY})
    block = await SectionImages(
        sources=searched_by(
            FakeSource("searxng", [shop, museum]),
        ),
        store=store,
        context=FakeContexts(),
    ).block(ask(STICKY))
    assert block is not None
    assert [item.media.page_url for item in block.items] == ["https://collections.vam.ac.uk/item/O1/"]
