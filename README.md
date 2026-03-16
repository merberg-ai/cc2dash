# cc2dash

A Raspberry Pi-hosted LAN dashboard scaffold for the Elegoo Centauri Carbon 2.

## Current state

This is an **initial working scaffold**. It includes:

- FastAPI app bootstrap
- SQLite database initialization
- SQLAlchemy models
- HTML pages for setup and dashboard
- Printer CRUD endpoints
- Discovery/API/service placeholders
- Runtime printer manager skeleton
- Event/state persistence skeleton

What it **does not fully implement yet**:

- Actual UDP discovery
- Actual MQTT registration / heartbeat / status parsing
- Camera proxying
- Live printer protocol integration

## Quick start

```bash
./run.sh
```

Then open:

```text
http://<pi-ip>:8008
```

## Project layout

- `app/` application code
- `data/cc2dash.db` SQLite database
- `migrations/001_initial.sql` initial schema snapshot

## Next step

Implement the real Centauri Carbon 2 LAN protocol inside:

- `app/core/discovery.py`
- `app/core/mqtt_protocol.py`
- `app/core/mqtt_client.py`
- `app/core/printer_manager.py`

