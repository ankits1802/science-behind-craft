import time
import uuid
from typing import Any

import pytest

from app.core.config import get_settings
from app.services import google_auth

GOOGLE_CLIENT_ID = "google-client-id-for-tests.apps.googleusercontent.com"


class FakeGoogle:
    def __init__(self) -> None:
        self.claims: dict[str, dict[str, Any]] = {}

    def mint(self, email: str, nonce: str, *, iat: float | None = None, verified: bool = True) -> str:
        now = int(time.time())
        token = f"google-token-{uuid.uuid4().hex}"
        self.claims[token] = {
            "iss": "https://accounts.google.com",
            "aud": GOOGLE_CLIENT_ID,
            "sub": "google-subject",
            "email": email,
            "email_verified": verified,
            "iat": now if iat is None else int(iat),
            "exp": now + 3600,
            "nonce": nonce,
        }
        return token

    def verify(self, token: str, client_id: str) -> dict[str, Any]:
        if token not in self.claims or client_id != GOOGLE_CLIENT_ID:
            raise ValueError("token does not verify")
        return self.claims[token]

    def install(self, monkeypatch: pytest.MonkeyPatch) -> FakeGoogle:
        monkeypatch.setattr(get_settings(), "google_client_id", GOOGLE_CLIENT_ID)
        monkeypatch.setattr(google_auth, "_verify_sync", self.verify)
        return self
