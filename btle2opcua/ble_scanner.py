"""Continuous BTLE advertisement scanning using bleak."""
from __future__ import annotations

import logging
from typing import Awaitable, Callable, Optional

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

logger = logging.getLogger(__name__)

DetectionCallback = Callable[[BLEDevice, AdvertisementData], Awaitable[None]]


class BleScanner:
    """Wraps BleakScanner to continuously forward advertisements to a callback."""

    def __init__(self, on_advertisement: DetectionCallback) -> None:
        self._on_advertisement = on_advertisement
        self._scanner: Optional[BleakScanner] = None

    async def _detection_callback(self, device: BLEDevice, advertisement_data: AdvertisementData) -> None:
        try:
            await self._on_advertisement(device, advertisement_data)
        except Exception:
            logger.exception("Error handling advertisement from %s", device.address)

    async def start(self) -> None:
        self._scanner = BleakScanner(detection_callback=self._detection_callback)
        await self._scanner.start()
        logger.info("BLE scanning started")

    async def stop(self) -> None:
        if self._scanner is not None:
            await self._scanner.stop()
            logger.info("BLE scanning stopped")
