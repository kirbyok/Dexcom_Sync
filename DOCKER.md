# Docker Setup

## Overview
- **dexcom-sync** – Dexcom CGM glucose readings → Nightscout entries
- **tandem-sync** – Tandem pump treatments/profiles → Nightscout treatments (tconnectsync backend)

Both services share the same `.env` and `logs/` directory.

## Container Diagram
```
┌─────────────────────┐     ┌─────────────────────┐
│  dexcom-sync        │     │  tandem-sync        │
│  (main.py)          │     │  (tandem_main.py)   │
│                     │     │                     │
│  Dexcom CGM Data    │     │  Pump Treatments    │
│  ↓                  │     │  ↓                  │
│  /api/v1/entries    │     │  /api/v1/treatments │
└─────────────────────┘     └─────────────────────┘
         ↓                            ↓
         └────────────┬───────────────┘
                      ↓
              Nightscout Server
```

## Logs
- `logs/dexcom_sync.log` – Dexcom
- `logs/tandem_sync.log` – Tandem

## Quick Start
- Start both: `docker compose up -d`
- Only Dexcom: `docker compose up -d dexcom-sync`
- Only Tandem: `docker compose up -d tandem-sync`
- View logs: `docker compose logs -f` (or per service)
- Stop: `docker compose down`

## One-off Runs / Backfill
- Dexcom once: `docker compose run --rm dexcom-sync python main.py once`
- Tandem once: `docker compose run --rm tandem-sync python tandem_main.py once`
- Dexcom backfill 30d: `docker compose run --rm dexcom-sync python main.py backfill --days 30`
- Tandem last 24h: `docker compose run --rm tandem-sync python tandem_main.py once --hours 24`

## Check Config
- Dexcom: `docker compose run --rm dexcom-sync python main.py config`
- Tandem: `docker compose run --rm tandem-sync python tandem_main.py config`

## .env Reference
```
# Dexcom
DEXCOM_PHONE=+1234567890
DEXCOM_PASSWORD=your-password
DEXCOM_USE_INTL=false
DEXCOM_DEVICE_NAME=DexSync

# Nightscout (both)
NIGHTSCOUT_URL=https://your-site.nightscoutpro.com/
NIGHTSCOUT_API_TOKEN=your-api-secret
NS_URL=https://your-site.nightscoutpro.com/
NS_SECRET=your-api-secret

# Tandem
TCONNECT_USERNAME=your-email@example.com
TCONNECT_PASSWORD=your-password
TCONNECT_SYNC_ENABLED=true
TCONNECT_FEATURE_BASAL=true
TCONNECT_FEATURE_BOLUS=true
TCONNECT_FEATURE_PUMP_EVENTS=true
TCONNECT_FEATURE_PROFILES=true

# Sync
SYNC_INTERVAL_MINUTES=3
TIMEZONE=UTC
```

## Enable/Disable
- Disable Tandem: set `TCONNECT_SYNC_ENABLED=false`, then `docker compose restart tandem-sync`
- Disable Dexcom: stop or comment out the service in `docker-compose.yml`

## Monitoring
- Status: `docker compose ps`
- Resources: `docker stats dexcom-sync tandem-sync`
- Tail logs: `tail -f logs/dexcom_sync.log logs/tandem_sync.log`

## Troubleshooting
- Missing `.env` or bad credentials
- Nightscout URL/token incorrect
- Tandem cache unwritable (ensure `logs/` writable by UID 1000)
- Pump has not yet uploaded to Tandem Source

## Rebuild
```
docker compose down
docker compose build
docker compose up -d
```
- Rebuild one: `docker compose build tandem-sync && docker compose up -d tandem-sync`

## Environment Variables
| Variable | Container | Purpose |
| --- | --- | --- |
| DEXCOM_PHONE | dexcom-sync | Dexcom Share phone |
| DEXCOM_PASSWORD | dexcom-sync | Dexcom Share password |
| NIGHTSCOUT_URL | both | Nightscout URL |
| NIGHTSCOUT_API_TOKEN | both | Nightscout api-secret |
| NS_URL | both | Nightscout URL (tconnectsync) |
| NS_SECRET | both | Nightscout api-secret (tconnectsync) |
| TCONNECT_USERNAME | tandem-sync | Tandem login |
| TCONNECT_PASSWORD | tandem-sync | Tandem login password |
| TCONNECT_SYNC_ENABLED | tandem-sync | Enable Tandem sync |
| TCONNECT_FEATURE_BASAL | tandem-sync | Basal toggle |
| TCONNECT_FEATURE_BOLUS | tandem-sync | Bolus toggle |
| TCONNECT_FEATURE_PUMP_EVENTS | tandem-sync | Pump events toggle |
| TCONNECT_FEATURE_PROFILES | tandem-sync | Profile toggle |
| SYNC_INTERVAL_MINUTES | both | Minutes between runs |
| TIMEZONE | both | Timezone for logging |
