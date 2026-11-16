from ipaddress import ip_address

import pytest

from app.core.errors import ExternalFailure
from app.fetcher.addresses import is_public_address, public_addresses
from app.fetcher.targets import checked_target, redirect_target
from app.research.fetcher import FetchRefused

from .site import PUBLIC_A, PUBLIC_B, Site

REFUSED_ADDRESSES = [
    "127.0.0.1",
    "127.8.9.10",
    "10.0.0.1",
    "172.16.5.4",
    "172.31.255.255",
    "192.168.0.10",
    "100.64.0.1",
    "100.127.255.254",
    "169.254.169.254",
    "169.254.170.2",
    "169.254.1.1",
    "100.100.100.200",
    "0.0.0.0",
    "0.1.2.3",
    "224.0.0.251",
    "239.255.255.250",
    "255.255.255.255",
    "192.0.2.10",
    "198.18.0.1",
    "198.51.100.7",
    "203.0.113.9",
    "240.0.0.1",
    "::",
    "::1",
    "fe80::1",
    "fc00::1",
    "fd12:3456::1",
    "fd00:ec2::254",
    "ff02::1",
    "2001:db8::1",
    "::ffff:127.0.0.1",
    "::ffff:10.0.0.1",
    "::ffff:169.254.169.254",
    "2002:7f00:1::",
    "2002:a00:1::",
    "2002:808:808::",
    "64:ff9b::7f00:1",
    "64:ff9b::a9fe:a9fe",
]
PUBLIC_ADDRESSES = [
    "8.8.8.8",
    "1.1.1.1",
    "93.184.215.14",
    "172.32.0.1",
    "100.128.0.1",
    "2606:4700:4700::1111",
    "2a00:1450:4001:80b::200e",
    "::ffff:8.8.8.8",
    "64:ff9b::808:808",
]


@pytest.mark.parametrize("address", REFUSED_ADDRESSES)
def test_private_loopback_link_local_cgnat_ula_and_metadata_addresses_are_refused(address: str) -> None:
    assert is_public_address(ip_address(address)) is False


@pytest.mark.parametrize("address", PUBLIC_ADDRESSES)
def test_global_unicast_addresses_are_allowed(address: str) -> None:
    assert is_public_address(ip_address(address)) is True


async def test_one_private_answer_among_public_ones_refuses_the_host() -> None:
    site = Site(dns={"mixed.example": [PUBLIC_A, "10.0.0.7"]})
    with pytest.raises(FetchRefused) as refused:
        await public_addresses("mixed.example", 443, resolve=site.resolve, url="https://mixed.example/")
    assert refused.value.reason == "PRIVATE_ADDRESS"
    assert "10.0.0.7" in refused.value.detail


async def test_an_address_literal_is_checked_without_a_lookup() -> None:
    site = Site()
    with pytest.raises(FetchRefused) as refused:
        await public_addresses("::1", 443, resolve=site.resolve, url="https://[::1]/")
    assert refused.value.reason == "PRIVATE_ADDRESS"
    assert site.lookups == []


async def test_ipv4_answers_come_first_and_duplicates_go() -> None:
    site = Site(dns={"dual.example": ["2606:4700:4700::1111", PUBLIC_B, PUBLIC_B]})
    found = await public_addresses("dual.example", 443, resolve=site.resolve, url="https://dual.example/")
    assert [str(a) for a in found] == [PUBLIC_B, "2606:4700:4700::1111"]


async def test_a_name_that_does_not_resolve_is_a_not_found_failure() -> None:
    with pytest.raises(ExternalFailure) as failure:
        await public_addresses("nowhere.example", 443, resolve=Site().resolve, url="https://nowhere.example/")
    assert failure.value.kind == "not_found"


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("http://crafts.example.org/", "NOT_HTTPS"),
        ("ftp://crafts.example.org/file", "NOT_HTTPS"),
        ("https://user:pw@crafts.example.org/", "BAD_URL"),
        ("https://crafts.example.org:8443/", "BAD_URL"),
        ("https://crafts.example.org:99999/", "BAD_URL"),
        ("https:///no-host", "BAD_URL"),
        ("https://crafts.example.org/a b", "BAD_URL"),
        ("https://crafts.example.org/" + "a" * 2048, "BAD_URL"),
    ],
)
def test_urls_outside_the_rules_are_refused(url: str, reason: str) -> None:
    with pytest.raises(FetchRefused) as refused:
        checked_target(url)
    assert refused.value.reason == reason


def test_a_target_keeps_path_and_query_and_drops_the_fragment() -> None:
    target = checked_target("https://Crafts.Example.org:443/ajrakh/notes?page=2#mordants")
    assert (target.url, target.host, target.path) == (
        "https://crafts.example.org/ajrakh/notes?page=2",
        "crafts.example.org",
        "/ajrakh/notes?page=2",
    )


def test_an_international_host_is_sent_in_punycode() -> None:
    assert checked_target("https://例え.jp/").host == "xn--r8jz45g.jp"


def test_an_ipv6_literal_keeps_its_brackets_in_the_url() -> None:
    target = checked_target("https://[2606:4700:4700::1111]/dns")
    assert (target.host, target.netloc, target.url) == (
        "2606:4700:4700::1111",
        "[2606:4700:4700::1111]",
        "https://[2606:4700:4700::1111]/dns",
    )


def test_a_relative_redirect_resolves_against_the_current_page() -> None:
    current = checked_target("https://crafts.example.org/ajrakh/notes")
    assert redirect_target(current, "../bagru/notes").url == "https://crafts.example.org/bagru/notes"
    with pytest.raises(FetchRefused) as refused:
        redirect_target(current, "http://crafts.example.org/insecure")
    assert refused.value.reason == "NOT_HTTPS"
