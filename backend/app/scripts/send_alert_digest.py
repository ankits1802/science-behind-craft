import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.core.db import dispose_engine, sessionmaker
from app.services import mailer
from app.services.alert_digest import send_alert_digests

NOT_CONFIGURED = {"enabled": True, "ok": False, "error": "MAIL_FROM_ADDRESS is not set"}


async def run() -> dict[str, Any]:
    settings = get_settings()
    if settings.alert_digest_enabled and not mailer.mail_configured():
        return dict(NOT_CONFIGURED)
    try:
        report = await send_alert_digests(
            sessionmaker(),
            now=datetime.now(UTC),
            enabled=settings.alert_digest_enabled,
            web_url=settings.public_web_url,
            send=mailer.send,
        )
    finally:
        await dispose_engine()
    return report.as_dict()


def main() -> int:
    report = asyncio.run(run())
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
