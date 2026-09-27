# btle2opcua

OPC UA gateway that maps BTLE advertisements to OPC UA variables.

Each BTLE address gets its own object folder under `Objects/BTLE/ByAddress/<address>`
with variables for the main advertisement fields (`Name`, `RSSI`, `TxPower`,
`ManufacturerData`, `ServiceData`, `ServiceUUIDs`, `LastSeen`, `Address`). Devices that
advertise a local name are additionally reachable under `Objects/BTLE/ByName/<name>`,
which references the same node (a real OPC UA alias, not a copy).

### ThermoBeacon Sensors

Discovered ThermoBeacon temperature and humidity sensors are automatically decoded and populated under `Objects/BTLE/ThermoBeacon/ByAddress/<address>` (and aliased under `Objects/BTLE/ThermoBeacon/ByName/<name>` when named) with dedicated variables:
- `Temperature` (Double, °C)
- `Humidity` (Double, % RH)
- `BatteryVoltage` (UInt16, mV)
- `Uptime` (UInt32, seconds)
- `Address` (String)
- `Name` (String)
- `RSSI` (Int16, dBm)
- `LastSeen` (DateTime)

## Setup

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

## Run

```powershell
python -m btle2opcua.main
```

Configuration is read from environment variables / `.env` (see `.env.example`):
`OPCUA_ENDPOINT`, `OPCUA_NAMESPACE`, `DEVICE_TTL_SECONDS` (removes devices that stop
advertising; `0` disables expiry), `LOG_LEVEL`.

## Docker

### Build & Run with Docker Compose

```bash
docker compose up -d
```

### Build & Run with Docker CLI

```bash
docker build -t btle2opcua .

# Run with host networking and D-Bus socket mount for Bluetooth access (Linux host)
docker run -d \
  --name btle2opcua \
  --net=host \
  -v /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket:ro \
  --env-file .env \
  btle2opcua
```

