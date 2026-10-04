"""Parser for Inkbird IBS-TH2 BLE advertisements."""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class InkbirdReading:
    """Decoded temperature, humidity, and battery reading."""

    temperature: float
    humidity: float
    battery_percent: int


def parse_inkbird(
    manufacturer_data: Dict[int, bytes],
    name: Optional[str] = None,
) -> Optional[InkbirdReading]:
    """Parse an IBS-TH2 advertisement whose local name is ``sps``."""
    if not name or name.strip().lower() != "sps":
        return None

    for company_id, payload in manufacturer_data.items():
        # Bleak separates the first two manufacturer bytes into company_id;
        # the IBS-TH2 uses those bytes for temperature, so restore them here.
        data = struct.pack("<H", company_id) + payload
        if len(data) != 9:
            continue

        try:
            temperature_raw, humidity_raw, probe, _modbus, battery_percent = struct.unpack(
                "<hHBHB", data[:8]
            )
        except struct.error:
            continue

        temperature = round(temperature_raw / 100.0, 2)
        humidity = round(humidity_raw / 100.0, 2)
        if probe == 0 and -50.0 <= temperature <= 100.0 and 0.0 <= humidity <= 100.0:
            return InkbirdReading(temperature, humidity, battery_percent)

    return None