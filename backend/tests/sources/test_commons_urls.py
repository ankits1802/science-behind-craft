import pytest

from app.sources.reference.commons_urls import commons_fitting_width, commons_thumbnail_url, standard_width

UPLOADS = "https://upload.wikimedia.org/wikipedia/commons/"


@pytest.mark.parametrize(
    ("url", "thumbnail"),
    [
        (f"{UPLOADS}5/54/AT_WORKSHOP.jpg", f"{UPLOADS}thumb/5/54/AT_WORKSHOP.jpg/500px-AT_WORKSHOP.jpg"),
        (
            f"{UPLOADS}6/62/Bidri_craft%2C_Hyderabad%2C_India.jpg",
            f"{UPLOADS}thumb/6/62/Bidri_craft%2C_Hyderabad%2C_India.jpg/500px-Bidri_craft%2C_Hyderabad%2C_India.jpg",
        ),
        (f"{UPLOADS}3/34/Pottery.png", f"{UPLOADS}thumb/3/34/Pottery.png/500px-Pottery.png"),
        (f"{UPLOADS}a/ab/Star.svg", f"{UPLOADS}thumb/a/ab/Star.svg/500px-Star.svg.png"),
        (f"{UPLOADS}thumb/c/cb/Cloth.jpg/960px-Cloth.jpg", f"{UPLOADS}thumb/c/cb/Cloth.jpg/500px-Cloth.jpg"),
    ],
)
def test_a_commons_file_is_resized_through_its_thumbnail_path(url: str, thumbnail: str) -> None:
    assert commons_thumbnail_url(url, 500) == thumbnail


@pytest.mark.parametrize(
    "url",
    [
        "https://live.staticflickr.com/4117/4929397431_d5cebd3520_b.jpg",
        f"{UPLOADS}b/b8/Scan.tif",
        f"{UPLOADS}b/b8/{'Long_name_' * 13}.jpg",
        "https://upload.wikimedia.org/wikipedia/en/b/b8/Local.jpg",
    ],
)
def test_other_files_are_left_as_they_are(url: str) -> None:
    assert commons_thumbnail_url(url, 500) is None


@pytest.mark.parametrize(
    ("requested", "width"), [(1, 330), (330, 330), (331, 500), (1051, 1280), (1920, 1920), (4000, 1920)]
)
def test_a_requested_width_takes_the_first_standard_width_at_least_as_wide(
    requested: int, width: int
) -> None:
    assert standard_width(requested) == width


@pytest.mark.parametrize(
    ("original", "width"), [(4000, 1280), (1280, 1280), (1279, 960), (600, 500), (330, 330), (329, None)]
)
def test_a_standard_width_never_passes_the_original_s_own(original: int, width: int | None) -> None:
    assert commons_fitting_width(1051, original) == width
