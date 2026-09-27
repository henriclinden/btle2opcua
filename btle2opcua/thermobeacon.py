"""Parser for ThermoBeacon BLE manufacturer advertisement data."""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Dict, Optional, Set

# Known ThermoBeacon manufacturer / company IDs
# 0x0010 (16) is the standard ThermoBeacon company ID.
# Other variants and reverse-endian representations encountered in various devices/stacks.
THERMOBEACON_COMPANY_IDS: Set[int] = {0x0010, 0x0011, 0x0015, 0x1000, 0x1100}


@dataclass(frozen=True)
class ThermoBeaconReading:
    """Decoded sensor reading from a ThermoBeacon advertisement."""

    temperature: float  # Degrees Celsius (°C)
    humidity: float  # Relative humidity percentage (%)
    battery_mv: int  # Battery voltage in millivolts (mV)
    uptime_seconds: int  # Device uptime in seconds


def parse_thermobeacon(
    manufacturer_data: Dict[int, bytes],
    name: Optional[str] = None,
) -> Optional[ThermoBeaconReading]:
    """Parse ThermoBeacon sensor data from BLE advertisement manufacturer data.

    ThermoBeacon sensor advertisement layout (18 bytes payload):
      - bytes 0..1:   Header / Packet type (uint16 LE)
      - bytes 2..7:   Device MAC address (6 bytes LE)
      - bytes 8..9:   Battery voltage in mV (uint16 LE)
      - bytes 10..11: Current temperature (int16 LE, scale factor 1/16.0)
      - bytes 12..13: Current relative humidity (uint16 LE, scale factor 1/16.0)
      - bytes 14..17: Uptime in seconds (uint32 LE, or uint16 LE in 16-byte frames)
    """
    for company_id, raw_bytes in manufacturer_data.items():
        is_known_id = company_id in THERMOBEACON_COMPANY_IDS
        has_matching_name = bool(name and "thermobeacon" in name.lower())

        if not (is_known_id or has_matching_name or len(raw_bytes) in (16, 18, 20)):
            continue

        data = raw_bytes

        # Some stacks include the 2-byte company ID (0x0010 / 0x1000) at the beginning of the payload
        if len(data) == 20 and (data.startswith(b"\x10\x00") or data.startswith(b"\x00\x10")):
            data = data[2:]

        # Real-time sensor reading advertisements have a payload length of 18 bytes
        # (or 16 bytes on some truncated/compact firmware revisions).
        # Longer payloads (e.g., 20 bytes without company ID prefix) are history / sync log frames.
        if len(data) not in (16, 18):
            continue

        try:
            batt_mv = struct.unpack_from("<H", data, 8)[0]
            temp_raw = struct.unpack_from("<h", data, 10)[0]
            hum_raw = struct.unpack_from("<H", data, 12)[0]
            temp = round(temp_raw / 16.0, 2)
            hum = round(hum_raw / 16.0, 2)

            # Plausibility checks for sensor limits
            if (-50.0 <= temp <= 100.0) and (0.0 <= hum <= 105.0) and (1000 <= batt_mv <= 6000):
                if len(data) >= 18:
                    uptime_seconds = struct.unpack_from("<I", data, 14)[0]
                else:
                    uptime_seconds = struct.unpack_from("<H", data, 14)[0]

                return ThermoBeaconReading(
                    temperature=temp,
                    humidity=hum,
                    battery_mv=batt_mv,
                    uptime_seconds=uptime_seconds,
                )
        except (struct.error, IndexError):
            continue

    return None
