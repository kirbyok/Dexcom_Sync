# Docker Setup

## Overview

The system now runs in **two separate Docker containers**:

1. **dexcom-sync** - Syncs Dexcom CGM glucose readings
2. **glooko-sync** - Syncs Omnipod pump treatments from Glooko

Both containers share the same `.env` configuration file and `logs/` directory.

## Container Architecture

```
┌─────────────────────┐     ┌─────────────────────┐
│  dexcom-sync        │     │  glooko-sync        │
│  (main.py)          │     │  (glooko_main.py)   │
│                     │     │                     │
│  Dexcom CGM Data    │     │  Omnipod Treatments │
│  ↓                  │     │  ↓                  │
│  /api/v1/entries    │     │  /api/v1/treatments │
└─────────────────────┘     └─────────────────────┘
         ↓                            ↓
         └────────────┬───────────────┘
                      ↓
              Nightscout Server
```

## Log Files

Each container writes to its own log file in the `logs/` directory:

- **logs/dexcom_sync.log** - Dexcom CGM sync logs
- **logs/glooko_sync.log** - Glooko Omnipod sync logs

Both logs rotate every 2 days, keeping 10 backup files.

## Quick Start

### Start Both Containers
```bash
docker compose up -d
```

### Start Only Dexcom
```bash
docker compose up -d dexcom-sync
```

### Start Only Glooko
```bash
docker compose up -d glooko-sync
```

### View Logs
```bash
# Dexcom logs
docker compose logs -f dexcom-sync

# Glooko logs
docker compose logs -f glooko-sync

# Both
docker compose logs -f
```

### Stop Containers
```bash
# Stop all
docker compose down

# Stop specific container
docker compose stop dexcom-sync
docker compose stop glooko-sync
```

## Manual Operations

### Run Once (No Container)
```bash
# Dexcom CGM sync
docker compose run --rm dexcom-sync python main.py once

# Glooko Omnipod sync
docker compose run --rm glooko-sync python glooko_main.py once
```

### Backfill Historical Data
```bash
# Backfill 30 days of Dexcom CGM data
docker compose run --rm dexcom-sync python main.py backfill --days 30

# Backfill 7 days of Omnipod treatments
docker compose run --rm glooko-sync python glooko_main.py backfill --days 7
```

### Check Configuration
```bash
# Dexcom config
docker compose run --rm dexcom-sync python main.py config

# Glooko config
docker compose run --rm glooko-sync python glooko_main.py config
```

## Configuration (.env)

Both containers use the same `.env` file:

```bash
# Dexcom Configuration (for dexcom-sync container)
DEXCOM_PHONE=+1234567890
DEXCOM_PASSWORD=your-password
DEXCOM_USE_INTL=false
DEXCOM_DEVICE_NAME=DexSync

# Nightscout Configuration (used by both containers)
NIGHTSCOUT_URL=https://your-site.nightscoutpro.com/
NIGHTSCOUT_API_TOKEN=your-api-token

# Glooko Configuration (for glooko-sync container)
GLOOKO_EMAIL=your-email@example.com
GLOOKO_PASSWORD=your-password
GLOOKO_SYNC_ENABLED=true

# Sync Settings (applies to both containers)
SYNC_INTERVAL_MINUTES=3
TIMEZONE=UTC
```

## Enabling/Disabling Services

### Disable Glooko
Set in `.env`:
```bash
GLOOKO_SYNC_ENABLED=false
```
Then restart:
```bash
docker compose restart glooko-sync
```

Or remove from docker-compose.yml and restart all:
```bash
docker compose down
docker compose up -d dexcom-sync
```

### Run Only Dexcom (No Glooko at all)
Comment out the glooko-sync service in `docker-compose.yml`:
```yaml
services:
  dexcom-sync:
    # ... config ...
  
  # glooko-sync:
  #   build: .
  #   ...
```

## Monitoring

### Container Status
```bash
docker compose ps
```

### Resource Usage
```bash
docker stats dexcom-sync glooko-sync
```

### Follow Logs in Real-time
```bash
# Tail both logs from the host
tail -f logs/dexcom_sync.log logs/glooko_sync.log
```

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker compose logs dexcom-sync
docker compose logs glooko-sync
```

Common issues:
- Missing `.env` file
- Invalid credentials
- Nightscout URL/token not set

### Glooko Container Exits Immediately

If `GLOOKO_SYNC_ENABLED=false`, the container will exit. Set to `true` and ensure credentials are configured.

### No Data Syncing

Check individual container logs and verify:
1. Credentials are correct in `.env`
2. Nightscout URL and token are valid
3. Containers are running: `docker compose ps`

## Rebuilding Containers

After code changes, rebuild:
```bash
docker compose down
docker compose build
docker compose up -d
```

Or rebuild specific container:
```bash
docker compose build glooko-sync
docker compose up -d glooko-sync
```

## Production Recommendations

1. **Use Docker Compose restart policies**: Already set to `restart: unless-stopped`
2. **Monitor logs regularly**: Check `logs/` directory
3. **Backup logs**: The 10-file rotation provides ~20 days of history
4. **Resource limits**: Add to docker-compose.yml if needed:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '0.5'
         memory: 256M
   ```

5. **Health checks**: Consider adding health checks to docker-compose.yml

## Environment Variables Reference

| Variable | Container | Purpose |
|----------|-----------|---------|
| `DEXCOM_PHONE` | dexcom-sync | Dexcom Share account phone |
| `DEXCOM_PASSWORD` | dexcom-sync | Dexcom Share password |
| `GLOOKO_EMAIL` | glooko-sync | Glooko account email |
| `GLOOKO_PASSWORD` | glooko-sync | Glooko account password |
| `GLOOKO_SYNC_ENABLED` | glooko-sync | Enable/disable Glooko sync |
| `NIGHTSCOUT_URL` | both | Nightscout server URL |
| `NIGHTSCOUT_API_TOKEN` | both | Nightscout api-secret |
| `SYNC_INTERVAL_MINUTES` | both | Minutes between syncs |
| `TIMEZONE` | both | Timezone for logging |
