# btle2opcua

OPC UA gateway that maps BTLE advertisements to OPC UA variables.

Each BTLE address gets its own object folder under `Objects/BTLE/ByAddress/<address>`
with variables for the main advertisement fields (`Name`, `RSSI`, `TxPower`,
`ManufacturerData`, `ServiceData`, `ServiceUUIDs`, `LastSeen`, `Address`). Devices that
advertise a local name are additionally reachable under `Objects/BTLE/ByName/<name>`,
which references the same node (a real OPC UA alias, not a copy).

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
