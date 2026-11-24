from __future__ import annotations

import uvicorn

from app.core.logging import configure_logging

from .render import BrowserRenderer
from .server import create_app
from .settings import RendererSettings


def main() -> None:
    settings = RendererSettings()
    configure_logging(settings.log_level)
    renderer = BrowserRenderer(browser=settings.browser, site=settings.site)
    uvicorn.run(
        create_app(renderer, site=settings.site),
        host=settings.host,
        port=settings.port,
        log_config=None,
        access_log=False,
        proxy_headers=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
