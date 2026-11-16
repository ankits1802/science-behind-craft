from __future__ import annotations

import asyncio
import logging
import os
import signal
import socket

from app.core.config import get_settings
from app.core.db import dispose_engine
from app.core.errors import NotConfigured
from app.core.logging import configure_logging
from app.media.wiring import media_queue

logger = logging.getLogger("kalavigyan.worker")


async def serve() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for stop_signal in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(stop_signal, stop.set)
    try:
        queue = media_queue(settings, worker_id=f"{socket.gethostname()}:{os.getpid()}")
    except NotConfigured as missing:
        logger.error("media worker idle until %s is set", missing.name)
        await stop.wait()
        return
    try:
        await queue.run(stop)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(serve())
