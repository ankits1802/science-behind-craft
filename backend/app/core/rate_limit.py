import hashlib
import hmac
import threading
import time
from collections import OrderedDict, deque
from ipaddress import ip_address

from starlette.requests import HTTPConnection

from app.core.config import get_settings

_MAX_KEYS = 50_000


class SlidingWindow:
    def __init__(self) -> None:
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def attempt(
        self, key: str, limit: int, window_seconds: float, now: float | None = None
    ) -> tuple[bool, float]:
        moment = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                hits = deque()
                self._hits[key] = hits
            self._hits.move_to_end(key)
            while hits and hits[0] <= moment - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False, max(0.0, hits[0] + window_seconds - moment)
            hits.append(moment)
            while len(self._hits) > _MAX_KEYS:
                self._hits.popitem(last=False)
            return True, 0.0

    def refund(self, key: str) -> None:
        with self._lock:
            hits = self._hits.get(key)
            if hits:
                hits.pop()

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


_windows = SlidingWindow()

WEB_PROXY_SECRET_HEADER = "x-web-proxy-secret"
VIEWER_ADDRESS_HEADER = "x-viewer-address"


def trusted_viewer_address(connection: HTTPConnection) -> str | None:
    secret = (get_settings().web_proxy_secret or "").strip()
    if not secret:
        return None
    sent = connection.headers.get(WEB_PROXY_SECRET_HEADER)
    viewer = connection.headers.get(VIEWER_ADDRESS_HEADER)
    if sent is None or viewer is None:
        return None
    if not hmac.compare_digest(sent.strip().encode("utf-8"), secret.encode("utf-8")):
        return None
    try:
        return str(ip_address(viewer.strip()))
    except ValueError:
        return None


def client_ip(connection: HTTPConnection) -> str:
    viewer = trusted_viewer_address(connection)
    if viewer:
        return viewer
    direct = connection.client.host if connection.client else ""
    try:
        trusted = ip_address(direct).is_loopback if direct else False
    except ValueError:
        trusted = False
    if trusted:
        forwarded = connection.headers.get("x-forwarded-for", "")
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        depth = get_settings().forwarded_client_hops
        if hops:
            return hops[-depth] if len(hops) >= depth else hops[0]
        real = connection.headers.get("x-real-ip", "").strip()
        if real:
            return real
    return direct or "unknown"


def ip_hash(address: str) -> str:
    key = get_settings().jwt_secret.encode("utf-8")
    return hmac.new(key, f"ip:{address}".encode(), hashlib.sha256).hexdigest()[:32]


def sign_in_attempt_by_ip(connection: HTTPConnection) -> tuple[bool, float]:
    settings = get_settings()
    return _windows.attempt(
        f"ip:{client_ip(connection)}", settings.sign_in_attempts_per_ip, settings.sign_in_window_seconds
    )


def sign_in_attempt_by_account(account_key: str) -> tuple[bool, float]:
    settings = get_settings()
    return _windows.attempt(
        f"acct:{account_key}", settings.sign_in_attempts_per_account, settings.sign_in_window_seconds
    )


def refund_account(account_key: str) -> None:
    _windows.refund(f"acct:{account_key}")


def refund_ip(connection: HTTPConnection) -> None:
    _windows.refund(f"ip:{client_ip(connection)}")


def forgot_password_attempt(connection: HTTPConnection) -> tuple[bool, float]:
    return _windows.attempt(f"forgot:{client_ip(connection)}", 5, 3600)


def code_attempt(user_id: str) -> tuple[bool, float]:
    return _windows.attempt(f"code:{user_id}", 10, 900)


def refund_code(user_id: str) -> None:
    _windows.refund(f"code:{user_id}")


def ask_attempt(user_id: str) -> tuple[bool, float]:
    return _windows.attempt(f"ask:{user_id}", 30, 600)


def term_attempt(user_id: str) -> tuple[bool, float]:
    return _windows.attempt(f"term:{user_id}", 60, 600)


def listen_attempt(user_id: str) -> tuple[bool, float]:
    return _windows.attempt(f"listen:{user_id}", 30, 600)


def voice_session_attempt(user_id: str) -> tuple[bool, float]:
    return _windows.attempt(f"voice:{user_id}", 10, 600)


def voice_turn_attempt(user_id: str) -> tuple[bool, float]:
    return _windows.attempt(f"voice-turn:{user_id}", 40, 600)


def voice_speech_attempt(user_id: str) -> tuple[bool, float]:
    return _windows.attempt(f"voice-speech:{user_id}", 60, 600)


def reset_all() -> None:
    _windows.clear()
