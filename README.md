# Dexcom Sync - Lightweight CLI Tool

A minimal, command-line tool to fetch Dexcom glucose readings and sync them to Nightscout.

**Architecture:** Simple, no database, no web server, configuration via `.env` file.

## Quick Start

```bash
# 1. Setup
pip install -r requirements.txt
cp .env.example .env

# 2. Configure .env with your credentials
# Edit .env and set DEXCOM_EMAIL/DEXCOM_PHONE and DEXCOM_PASSWORD

# 3. Run
python main.py once        # Fetch and display last 5 readings
python main.py continuous  # Sync every N minutes to Nightscout
```

## Commands

- `python main.py once` — Fetch glucose readings and display last 5
- `python main.py continuous` — Run continuous sync (configurable interval)
- `python main.py config` — Show current configuration
- `python main.py backfill --days N` — Backfill N days of historical data (1–30)

## Configuration

Edit `.env`:

```env
# REQUIRED: Dexcom Share credentials (use email or phone)
DEXCOM_EMAIL=your_email@example.com
DEXCOM_PASSWORD=your_password
DEXCOM_USE_INTL=false       # true for non-US Dexcom servers

# OPTIONAL: Nightscout integration
NIGHTSCOUT_URL=https://your-nightscout.example.com
NS_SECRET=your_api_secret   # plain API secret (auto SHA1-hashed)
# -- OR role-based access token --
# NIGHTSCOUT_API_TOKEN=dexcom-yourtoken  # sent as ?token= query param

# Sync interval for continuous mode
SYNC_INTERVAL_MINUTES=3
```

**Nightscout auth:** The connector auto-detects the credential type:
- Plain API secret (`NS_SECRET`) → SHA1-hashed into `api-secret` header
- Role token with a dash (`NIGHTSCOUT_API_TOKEN=role-xxx`) → sent as `?token=` query param

## Docker (Recommended)

Uses the hardened DHI image from DockerHub:

```bash
# docker-compose.yml is pre-configured — just add your .env
docker compose up -d
docker compose logs -f
```

### Images

| Tag | Description |
|-----|-------------|
| `zbaize01/dexcom-sync:dhi` | Hardened image (read-only FS, no pip, ~55 MB) — **recommended** |
| `zbaize01/dexcom-sync:latest` | Standard image |

The DHI image uses a read-only filesystem — logs go to stdout only (`docker compose logs`).

## Display Example

```
============================================================
DEXCOM GLUCOSE READINGS
============================================================
  1. 125 mg/dL  [        Flat]  2026-03-19 13:00:14  (23 minutes ago)
  2. 123 mg/dL  [        Flat]  2026-03-19 13:05:14  (18 minutes ago)
  3. 122 mg/dL  [        Flat]  2026-03-19 13:10:14  (13 minutes ago)
  4. 124 mg/dL  [        Flat]  2026-03-19 13:15:14  (8 minutes ago)
  5. 125 mg/dL  [        Flat]  2026-03-19 13:20:14  (3 minutes ago)
============================================================
```

## Requirements

- Python 3.12+
- See `requirements.txt` for dependencies

## License

MIT
