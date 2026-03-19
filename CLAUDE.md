# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A lightweight CLI tool that syncs Dexcom CGM glucose readings to Nightscout. No web UI — pure CLI and Docker containerization.

## Common Commands

```bash
# Run modes
python main.py once              # Single sync, display last 5 readings
python main.py continuous        # Loop sync every SYNC_INTERVAL_MINUTES (default: 3)
python main.py config            # Show current configuration
python main.py backfill --days N # Backfill N days of historical data

# Backfill utility
python backfill.py --source dexcom --hours 24
python backfill.py --source tandem --hours 24  # Tandem not yet implemented
python backfill.py --source both --hours 24

# Docker
docker compose up -d
docker compose logs -f
docker compose run --rm dexcom-sync python main.py once

# Build and push
docker build -t zbaize01/dexcom-sync:latest .
docker build -f Dockerfile.hardened --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") --build-arg VCS_REF=$(git rev-parse --short HEAD) -t zbaize01/dexcom-sync:dhi .
docker push zbaize01/dexcom-sync:latest && docker push zbaize01/dexcom-sync:dhi
```

## Architecture

**Core files:**

- `main.py` — `DexcomSync` class; CLI entry point with `sync()`, `display_readings()`, `run_continuous()`; file-rotated logging; reads `NIGHTSCOUT_URL`/`NS_URL` and `NIGHTSCOUT_API_TOKEN`/`NS_SECRET`
- `dexcom_client.py` — `DexcomClient`; 2-step Dexcom Share API auth (authenticate → login by account ID → fetch readings); US/International server selection; auto-retry on session expiry; dynamic maxCount scaling
- `nightscout_connector.py` — `NightscoutConnector`; pushes SGV entries to `/api/v1/entries`; auto-detects auth type: role tokens (`role-xxx`) use `?token=` query param, plain API secrets use SHA1-hashed `api-secret` header
- `nightscout_treatments.py` — `NightscoutTreatments`; pushes bolus/basal/pump events to `/api/v1/treatments`
- `backfill.py` — Backfill utility; Tandem import is lazy (fails gracefully if `tandem_main.py` is absent)

**Data flow:**

```
Dexcom Share API (username/password, not OAuth)
  └─ DexcomClient → GlucoseReading dicts
       └─ NightscoutConnector → /api/v1/entries (CGM)
       └─ NightscoutTreatments → /api/v1/treatments (pump)
```

**GlucoseReading dict shape:** `timestamp` (UTC-aware datetime), `value` (mg/dL int), `trend` (string like `'FortyFiveUp'`), `unit`, plus optional `trend_rate`, `filtered`, `unfiltered`, `rssi`, `noise`.

## Key Configuration (`.env`)

```env
DEXCOM_EMAIL=          # or DEXCOM_PHONE
DEXCOM_PASSWORD=
DEXCOM_USE_INTL=false  # true for non-US servers
NIGHTSCOUT_URL=        # or NS_URL
NIGHTSCOUT_API_TOKEN=  # or NS_SECRET; auto-detects role token vs API secret
SYNC_INTERVAL_MINUTES=3
```

**Nightscout auth:** If the token contains a dash (e.g. `dexcom-abc123`), it is treated as a role-based access token and sent as `?token=`. Otherwise it is SHA1-hashed and sent as the `api-secret` header. `NS_SECRET` is the recommended env var for plain API secrets.

Copy `.env.example` to `.env` to start.

## Docker

`docker-compose.yml` uses the hardened DHI image (`zbaize01/dexcom-sync:dhi`) with read-only filesystem, no-new-privileges, and 256M memory cap. `Dockerfile` is the standard build; `Dockerfile.hardened` builds the DHI variant (no pip at runtime, ~55 MB).

The DHI image uses a read-only root filesystem — file logging is disabled by design; all logs go to stdout (`docker compose logs`).

## Datetime Handling

All datetimes must be timezone-aware UTC (`timezone.utc`). Never use naive datetimes or `datetime.utcnow()`.

## Known Issues

- `tandem_main.py` does not exist — Tandem backfill is not implemented. `backfill.py` fails gracefully with an error message rather than crashing at import.
