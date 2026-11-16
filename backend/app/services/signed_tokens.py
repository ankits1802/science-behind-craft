import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

logger = logging.getLogger(__name__)

ALLOWED_ALGORITHMS = ("RS256", "ES256")
JWKS_TTL_SECONDS = 3600
JWKS_REFETCH_FLOOR_SECONDS = 60
HTTP_TIMEOUT_SECONDS = 10


class TokenRefused(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class SignedToken:
    header: dict[str, Any]
    claims: dict[str, Any]
    signing_input: bytes
    signature: bytes


@dataclass
class _KeySet:
    fetched_at: float
    keys: list[dict[str, Any]]


class SigningKeyCache:
    def __init__(self) -> None:
        self._sets: dict[str, _KeySet] = {}

    def get(self, uri: str) -> _KeySet | None:
        return self._sets.get(uri)

    def put(self, uri: str, keys: list[dict[str, Any]], fetched_at: float) -> None:
        self._sets[uri] = _KeySet(fetched_at=fetched_at, keys=keys)

    def clear(self) -> None:
        self._sets.clear()


_signing_keys = SigningKeyCache()


def forget_cached_keys() -> None:
    _signing_keys.clear()


async def _get_json(url: str) -> Any:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url, headers={"Accept": "application/json"})
    response.raise_for_status()
    return response.json()


async def _keys(uri: str, *, refresh: bool) -> list[dict[str, Any]]:
    now = time.monotonic()
    cached = _signing_keys.get(uri)
    if cached is not None:
        fresh = now - cached.fetched_at < JWKS_TTL_SECONDS
        may_refetch = now - cached.fetched_at >= JWKS_REFETCH_FLOOR_SECONDS
        if fresh and not (refresh and may_refetch):
            return cached.keys
    try:
        document = await _get_json(uri)
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("signing keys could not be read", extra={"uri": uri, "error": type(exc).__name__})
        if cached is not None:
            return cached.keys
        raise TokenRefused("jwks-unreachable") from exc
    keys = document.get("keys") if isinstance(document, dict) else None
    if not isinstance(keys, list):
        raise TokenRefused("jwks-malformed")
    keys = [key for key in keys if isinstance(key, dict)]
    _signing_keys.put(uri, keys, now)
    return keys


def b64url_decode(segment: str) -> bytes:
    padded = segment + "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _int_of(segment: str) -> int:
    return int.from_bytes(b64url_decode(segment), "big")


def _public_key(jwk: dict[str, Any], alg: str) -> Any:
    kty = jwk.get("kty")
    if alg == "RS256" and kty == "RSA":
        return rsa.RSAPublicNumbers(_int_of(jwk["e"]), _int_of(jwk["n"])).public_key()
    if alg == "ES256" and kty == "EC" and jwk.get("crv") == "P-256":
        point = ec.EllipticCurvePublicNumbers(_int_of(jwk["x"]), _int_of(jwk["y"]), ec.SECP256R1())
        return point.public_key()
    raise TokenRefused("key-type-mismatch")


def _verify_signature(key: Any, alg: str, signing_input: bytes, signature: bytes) -> None:
    try:
        if alg == "RS256":
            key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
            return
        if len(signature) != 64:
            raise TokenRefused("bad-signature")
        r, s = int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
        key.verify(encode_dss_signature(r, s), signing_input, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:
        raise TokenRefused("bad-signature") from exc


def split_token(token: str) -> SignedToken:
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenRefused("malformed-token")
    try:
        header = json.loads(b64url_decode(parts[0]))
        claims = json.loads(b64url_decode(parts[1]))
        signature = b64url_decode(parts[2])
    except (ValueError, UnicodeDecodeError) as exc:
        raise TokenRefused("malformed-token") from exc
    if not isinstance(header, dict) or not isinstance(claims, dict):
        raise TokenRefused("malformed-token")
    return SignedToken(header, claims, f"{parts[0]}.{parts[1]}".encode("ascii"), signature)


def _matching_keys(keys: list[dict[str, Any]], kid: Any, alg: str) -> list[dict[str, Any]]:
    return [
        key
        for key in keys
        if (kid is None or key.get("kid") == kid)
        and key.get("use", "sig") == "sig"
        and key.get("alg", alg) == alg
    ]


async def check_signature(token: SignedToken, jwks_uri: str) -> None:
    alg = token.header.get("alg")
    if alg not in ALLOWED_ALGORITHMS:
        raise TokenRefused("algorithm-refused")
    kid = token.header.get("kid")
    candidates = _matching_keys(await _keys(jwks_uri, refresh=False), kid, alg)
    if not candidates:
        candidates = _matching_keys(await _keys(jwks_uri, refresh=True), kid, alg)
    if not candidates:
        raise TokenRefused("unknown-key")
    last: TokenRefused | None = None
    for jwk in candidates:
        try:
            _verify_signature(_public_key(jwk, alg), alg, token.signing_input, token.signature)
            return
        except (TokenRefused, KeyError, ValueError) as exc:
            last = exc if isinstance(exc, TokenRefused) else TokenRefused("bad-key")
    raise last or TokenRefused("bad-signature")
