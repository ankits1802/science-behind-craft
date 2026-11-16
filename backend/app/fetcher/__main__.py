from __future__ import annotations

import logging

import uvicorn

from app.core.logging import configure_logging

from .sandbox import SandboxFetcher
from .server import create_app
from .settings import FetcherSettings


def main() -> None:
    settings = FetcherSettings()
    configure_logging(settings.log_level)
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    uvicorn.run(
        create_app(SandboxFetcher.build()),
        host=settings.host,
        port=settings.port,
        log_config=None,
        access_log=False,
        proxy_headers=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
