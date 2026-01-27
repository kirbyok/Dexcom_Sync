# Docker Setup

## Overview
**dexcom-sync** – Dexcom CGM glucose readings → Nightscout entries

## Quick Start
- Start: `docker compose up -d`
- View logs: `docker compose logs -f`
- Stop: `docker compose down`

## One-off Runs / Backfill
- Run once: `docker compose run --rm dexcom-sync python main.py once`
- Backfill 30 days: `docker compose run --rm dexcom-sync python main.py backfill --days 30`

## Check Config
- `docker compose run --rm dexcom-sync python main.py config`

## .env Reference
```
# Dexcom
DEXCOM_PHONE=+1234567890
DEXCOM_PASSWORD=your-password
DEXCOM_USE_INTL=false
DEXCOM_DEVICE_NAME=DexSync

# Nightscout
NIGHTSCOUT_URL=https://your-site.nightscoutpro.com/
NIGHTSCOUT_API_TOKEN=your-api-secret
NS_URL=https://your-site.nightscoutpro.com/
NS_SECRET=your-api-secret

# Sync
SYNC_INTERVAL_MINUTES=3
TIMEZONE=UTC
```

## Monitoring
- Status: `docker compose ps`
- Resources: `docker stats dexcom-sync`
- Tail logs: `tail -f logs/dexcom_sync.log`

## Troubleshooting
- Missing `.env` or bad credentials
- Nightscout URL/token incorrect

## Rebuild
```
docker compose down
docker compose build
docker compose up -d
```

## Environment Variables
| Variable | Purpose |
| --- | --- |
| DEXCOM_PHONE | Dexcom Share phone |
| DEXCOM_PASSWORD | Dexcom Share password |
| NIGHTSCOUT_URL | Nightscout URL |
| NIGHTSCOUT_API_TOKEN | Nightscout api-secret |
| NS_URL | Nightscout URL (alt) |
| NS_SECRET | Nightscout api-secret (alt) |
| SYNC_INTERVAL_MINUTES | Minutes between runs |
| TIMEZONE | Timezone for logging |
