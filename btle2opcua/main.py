"""Entry point for the btle2opcua gateway."""
from __future__ import annotations

import asyncio
import logging

from .ble_scanner import BleScanner
from .config import Settings
from .opcua_gateway import OpcuaGateway

logger = logging.getLogger(__name__)


async def _expire_loop(gateway: OpcuaGateway, interval_seconds: float) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        await gateway.expire_stale_devices()


async def run() -> None:
    settings = Settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    gateway = OpcuaGateway(settings)
    scanner = BleScanner(gateway.handle_advertisement)

    await gateway.start()
    expire_task = None
    if settings.device_ttl_seconds > 0:
        expire_task = asyncio.create_task(_expire_loop(gateway, max(settings.device_ttl_seconds / 2, 30)))

    try:
        await scanner.start()
        logger.info("btle2opcua gateway running, press Ctrl+C to stop")
        await asyncio.Event().wait()
    finally:
        if expire_task is not None:
            expire_task.cancel()
        await scanner.stop()
        await gateway.stop()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
