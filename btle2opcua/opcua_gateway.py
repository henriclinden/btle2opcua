"""Maps BTLE advertisements onto an OPC UA address space.

Each BTLE address gets its own object folder under Objects/BTLE/ByAddress with variables
for the main advertisement fields. Devices that advertise a local name are additionally
reachable under Objects/BTLE/ByName/<name>, which is a real OPC UA alias (an extra
"Organizes" reference to the same node) rather than a duplicate object.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from asyncua import Server, ua
from asyncua.common.node import Node
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class DeviceNode:
    """OPC UA nodes representing a single BTLE device."""

    object: Node
    address_var: Node
    name_var: Node
    rssi_var: Node
    tx_power_var: Node
    manufacturer_data_var: Node
    service_data_var: Node
    service_uuids_var: Node
    last_seen_var: Node
    aliased_name: Optional[str] = field(default=None)
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OpcuaGateway:
    """Bridges BTLE advertisements to an OPC UA address space."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._server = Server()
        self._idx = 0
        self._by_address_folder: Optional[Node] = None
        self._by_name_folder: Optional[Node] = None
        self._devices: Dict[str, DeviceNode] = {}

    async def start(self) -> None:
        await self._server.init()
        self._server.set_endpoint(self._settings.opcua_endpoint)
        self._idx = await self._server.register_namespace(self._settings.opcua_namespace)

        objects = self._server.nodes.objects
        root_folder = await objects.add_folder(self._idx, "BTLE")
        self._by_address_folder = await root_folder.add_folder(self._idx, "ByAddress")
        self._by_name_folder = await root_folder.add_folder(self._idx, "ByName")

        await self._server.start()
        logger.info("OPC UA server started at %s", self._settings.opcua_endpoint)

    async def stop(self) -> None:
        await self._server.stop()
        logger.info("OPC UA server stopped")

    @staticmethod
    def _safe_node_id_part(address: str) -> str:
        return address.replace(":", "-")

    @staticmethod
    def _format_manufacturer_data(data: Dict[int, bytes]) -> str:
        return "; ".join(f"0x{company_id:04X}:{value.hex()}" for company_id, value in data.items())

    @staticmethod
    def _format_service_data(data: Dict[str, bytes]) -> str:
        return "; ".join(f"{uuid}:{value.hex()}" for uuid, value in data.items())

    async def _create_device_node(self, address: str) -> DeviceNode:
        assert self._by_address_folder is not None
        nodeid_part = self._safe_node_id_part(address)
        obj = await self._by_address_folder.add_object(
            ua.NodeId(f"btle.device.{nodeid_part}", self._idx),
            ua.QualifiedName(address, self._idx),
        )

        address_var = await obj.add_variable(self._idx, "Address", address)
        name_var = await obj.add_variable(self._idx, "Name", "")
        rssi_var = await obj.add_variable(self._idx, "RSSI", ua.Variant(0, ua.VariantType.Int16))
        tx_power_var = await obj.add_variable(self._idx, "TxPower", ua.Variant(0, ua.VariantType.Int16))
        manufacturer_data_var = await obj.add_variable(self._idx, "ManufacturerData", "")
        service_data_var = await obj.add_variable(self._idx, "ServiceData", "")
        service_uuids_var = await obj.add_variable(self._idx, "ServiceUUIDs", "")
        last_seen_var = await obj.add_variable(
            self._idx, "LastSeen", ua.Variant(datetime.now(timezone.utc), ua.VariantType.DateTime)
        )

        for var in (
            address_var,
            name_var,
            rssi_var,
            tx_power_var,
            manufacturer_data_var,
            service_data_var,
            service_uuids_var,
            last_seen_var,
        ):
            await var.set_writable(False)

        device = DeviceNode(
            object=obj,
            address_var=address_var,
            name_var=name_var,
            rssi_var=rssi_var,
            tx_power_var=tx_power_var,
            manufacturer_data_var=manufacturer_data_var,
            service_data_var=service_data_var,
            service_uuids_var=service_uuids_var,
            last_seen_var=last_seen_var,
        )
        self._devices[address] = device
        logger.info("Created OPC UA node for BTLE device %s", address)
        return device

    async def _ensure_name_alias(self, device: DeviceNode, address: str, name: str) -> None:
        if not name or device.aliased_name == name:
            return
        assert self._by_name_folder is not None

        if device.aliased_name is not None:
            await self._by_name_folder.delete_reference(
                device.object.nodeid, ua.ObjectIds.Organizes, forward=True, bidirectional=False
            )

        await self._by_name_folder.add_reference(
            device.object.nodeid, ua.ObjectIds.Organizes, forward=True, bidirectional=False
        )
        device.aliased_name = name
        logger.info("Aliased BTLE device %s as %r", address, name)

    async def handle_advertisement(self, ble_device: BLEDevice, advertisement: AdvertisementData) -> None:
        address = ble_device.address
        device = self._devices.get(address)
        if device is None:
            device = await self._create_device_node(address)

        name = advertisement.local_name or ble_device.name or ""

        await device.name_var.write_value(name)
        await device.rssi_var.write_value(ua.Variant(advertisement.rssi, ua.VariantType.Int16))
        await device.tx_power_var.write_value(
            ua.Variant(advertisement.tx_power or 0, ua.VariantType.Int16)
        )
        await device.manufacturer_data_var.write_value(
            self._format_manufacturer_data(advertisement.manufacturer_data)
        )
        await device.service_data_var.write_value(self._format_service_data(advertisement.service_data))
        await device.service_uuids_var.write_value(", ".join(advertisement.service_uuids))
        device.last_seen = datetime.now(timezone.utc)
        await device.last_seen_var.write_value(ua.Variant(device.last_seen, ua.VariantType.DateTime))

        if name:
            await self._ensure_name_alias(device, address, name)

    async def expire_stale_devices(self) -> None:
        """Remove devices that have not advertised within the configured TTL."""
        ttl = self._settings.device_ttl_seconds
        if ttl <= 0:
            return
        now = datetime.now(timezone.utc)
        stale = [
            address
            for address, device in self._devices.items()
            if (now - device.last_seen).total_seconds() > ttl
        ]
        for address in stale:
            device = self._devices.pop(address)
            # delete_target_references (default True) also removes the ByAddress/ByName alias references.
            await self._server.delete_nodes([device.object], recursive=True)
            logger.info("Expired stale BTLE device %s", address)
