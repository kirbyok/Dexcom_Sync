# Dexcom Sync - Simple CLI Tool

A lightweight command-line tool to fetch Dexcom glucose readings and sync them to Nightscout.

Similar architecture to Tconnectsync - simple, minimal dependencies, configuration via `.env` file.

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate virtual environment:
   - Windows: `.\venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

6. Edit `.env` with your Dexcom and optional Nightscout credentials

## Configuration

Edit `.env` file with your settings:

```env
# Required: Dexcom credentials (email or phone)
DEXCOM_EMAIL=your_email@example.com
# OR
DEXCOM_PHONE=+12125551234
DEXCOM_PASSWORD=your_password

# Optional: Nightscout
NIGHTSCOUT_URL=https://your-site.herokuapp.com
NIGHTSCOUT_API_TOKEN=your_token

# Sync interval (minutes) - only used for continuous mode
SYNC_INTERVAL_MINUTES=5
```

## Usage

### One-time sync and display
```bash
python main.py once
```

Shows the last 5 glucose readings with timestamps.

### Continuous syncing
```bash
python main.py continuous
```

Runs continuous sync at the configured interval and pushes to Nightscout.

### View configuration
```bash
python main.py config
```

Shows current configuration loaded from `.env`.

## Features

- ✅ Simple command-line interface
- ✅ Minimal dependencies
- ✅ Configuration via `.env` file
- ✅ Fetch last 5 glucose readings with display
- ✅ Optional Nightscout sync
- ✅ No database required
- ✅ No web server

## Dexcom Setup

1. Use your regular Dexcom Share account credentials
2. Works with both US and International Dexcom servers
3. Set `DEXCOM_USE_INTL=true` if outside the US

## License

See LICENSE file
