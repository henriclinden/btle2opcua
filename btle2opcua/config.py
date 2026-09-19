"""Runtime configuration for the btle2opcua gateway, loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    opcua_endpoint: str = field(
        default_factory=lambda: os.getenv("OPCUA_ENDPOINT", "opc.tcp://0.0.0.0:4840/btle2opcua/server/")
    )
    opcua_namespace: str = field(default_factory=lambda: os.getenv("OPCUA_NAMESPACE", "http://btle2opcua/"))
    # Devices that have not advertised for longer than this are removed from the address space. 0 disables expiry.
    device_ttl_seconds: float = field(default_factory=lambda: float(os.getenv("DEVICE_TTL_SECONDS", "300")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
