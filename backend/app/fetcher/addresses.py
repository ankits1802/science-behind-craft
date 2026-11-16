from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable, Iterable, Sequence
from ipaddress import IPv4Address, IPv6Address

from app.core.errors import ExternalFailure
from app.research.fetcher import FetchRefused

__all__ = [
    "METADATA_ADDRESSES",
    "IpAddress",
    "Resolver",
    "is_public_address",
    "public_addresses",
    "system_resolver",
]

IpAddress = IPv4Address | IPv6Address
Resolver = Callable[[str, int], Awaitable[Sequence[str]]]

METADATA_ADDRESSES = frozenset(
    {
        IPv4Address("169.254.169.254"),
        IPv4Address("169.254.170.2"),
        IPv4Address("100.100.100.200"),
        IPv6Address("fd00:ec2::254"),
    }
)
NAT64_PREFIX = ipaddress.IPv6Network("64:ff9b::/96")


def is_public_address(address: IpAddress) -> bool:
    if address in METADATA_ADDRESSES or address.is_multicast or not address.is_global:
        return False
    if isinstance(address, IPv6Address):
        embedded = _embedded_ipv4(address)
        return embedded is None or is_public_address(embedded)
    return True


async def public_addresses(host: str, port: int, *, resolve: Resolver, url: str) -> list[IpAddress]:
    literal = _literal(host)
    if literal is not None:
        names = [str(literal)]
    else:
        try:
            names = list(await resolve(host, port))
        except OSError:
            raise ExternalFailure(f"{host} did not resolve", kind="not_found", service="fetcher") from None
    addresses = _unique(ipaddress.ip_address(name.split("%")[0]) for name in names)
    if not addresses:
        raise ExternalFailure(f"{host} has no address", kind="not_found", service="fetcher")
    private = [str(a) for a in addresses if not is_public_address(a)]
    if private:
        raise FetchRefused(url, "PRIVATE_ADDRESS", f"{host} resolves to {', '.join(private)}")
    return sorted(addresses, key=lambda a: a.version)


async def system_resolver(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


def _embedded_ipv4(address: IPv6Address) -> IPv4Address | None:
    if address.ipv4_mapped is not None:
        return address.ipv4_mapped
    if address.sixtofour is not None:
        return address.sixtofour
    if address in NAT64_PREFIX:
        return IPv4Address(int(address) & 0xFFFFFFFF)
    return None


def _literal(host: str) -> IpAddress | None:
    try:
        return ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return None


def _unique(addresses: Iterable[IpAddress]) -> list[IpAddress]:
    seen: list[IpAddress] = []
    for address in addresses:
        if address not in seen:
            seen.append(address)
    return seen
