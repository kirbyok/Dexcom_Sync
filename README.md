# Dexcom Sync - Lightweight CLI Tool

A minimal, command-line tool to fetch Dexcom glucose readings and optionally sync them to Nightscout.

**Architecture:** Similar to Tconnectsync - simple, no database, no web server, configuration via `.env` file.
## Quick Start

```bash
# 1. Setup
pip install -r requirements.txt
cp .env.example .env

# 2. Configure .env with your Dexcom credentials
# Edit .env and add:
#   DEXCOM_EMAIL=your_email@example.com
#   DEXCOM_PASSWORD=your_password

# 3. Run
python main.py once        # Fetch and display last 5 readings
python main.py continuous  # Sync every N minutes to Nightscout
```

## Commands

- `python main.py once` - Fetch glucose readings and display last 5 with timestamps
- `python main.py continuous` - Run continuous sync (configurable interval)
- `python main.py config` - Show current configuration

## Configuration

Edit `.env` file:

```env
# REQUIRED: Dexcom Share credentials
DEXCOM_EMAIL=your_email@example.com
DEXCOM_PASSWORD=your_password

# OPTIONAL: Nightscout integration
NIGHTSCOUT_URL=https://your-nightscout.herokuapp.com
NIGHTSCOUT_API_TOKEN=your_api_token

# Sync interval (minutes) - for continuous mode
SYNC_INTERVAL_MINUTES=5
```

## Features

- ✅ CLI-based (no web interface)
- ✅ Minimal dependencies (requests, python-dotenv)
- ✅ No database
- ✅ Show last 5 glucose readings with timestamps
- ✅ Optional Nightscout sync
- ✅ Works with US and International Dexcom
- ✅ Simple `.env` configuration

## Display Example

```
============================================================
DEXCOM GLUCOSE READINGS
============================================================
1. 145 mg/dL  [FortyFiveUp]  2026-01-21 15:30:00  (5 minutes ago)
2. 142 mg/dL  [Flat]         2026-01-21 15:25:00  (10 minutes ago)
3. 140 mg/dL  [Flat]         2026-01-21 15:20:00  (15 minutes ago)
4. 138 mg/dL  [FortyFiveDown] 2026-01-21 15:15:00 (20 minutes ago)
5. 136 mg/dL  [SingleDown]   2026-01-21 15:10:00  (25 minutes ago)
============================================================
```

## Requirements

- Python 3.7+
- See `requirements.txt` for dependencies

## License

See LICENSE file

1. **Login**: Navigate to `http://localhost:5000` (or your domain)
   - Default: username `admin`, password `changeme`
   - Change password after first login!

2. **Dashboard**: View current glucose levels and trends
   - See latest reading with trend arrow
   - View 24-hour glucose chart
   - Check sync status for each destination
   - View recent sync logs

3. **Settings**: Configure data destinations
   - Authorize Dexcom API
   - Configure Nightscout, MySQL, Airtable, Google Sheets
   - All sensitive data is encrypted

4. **Manual Sync**: Click "MANUAL SYNC" button on dashboard

### API Endpoints

```bash
# Get readings (last 24 hours)
GET /api/readings?hours=24

# Trigger manual sync
POST /api/sync

# Health check
GET /health
```

## Project Structure

```
dexcom-sync/
├── app.py                      # Main Flask application
├── config.py                   # Configuration with encryption
├── models.py                   # Database models
├── dexcom_client.py           # Dexcom API integration
├── sync_manager.py            # Sync logic coordinator
├── scheduler.py               # Background task scheduler
├── connectors/
│   ├── __init__.py
│   ├── nightscout_connector.py
│   ├── mysql_connector.py
│   ├── airtable_connector.py
│   └── sheets_connector.py
├── templates/
│   ├── base.html              # Base template with retro theme
│   ├── login.html             # Login page
│   ├── dashboard.html         # Main dashboard
│   └── settings.html          # Settings configuration
├── data/                       # Database storage (Docker volume)
├── logs/                       # Application logs
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml         # Docker Compose setup
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## Database Schema

### GlucoseReading
- `id`: Primary key
- `timestamp`: Reading timestamp
- `value`: Glucose value
- `trend`: Trend direction
- `unit`: Measurement unit (mg/dL)
- `synced_*`: Sync status flags for each destination

### Settings
- `id`: Primary key
- `key`: Setting name
- `value`: Setting value (encrypted if sensitive)
- `encrypted`: Boolean flag

### SyncLog
- `id`: Primary key
- `destination`: Target platform
- `status`: Success/error
- `readings_count`: Number of readings synced
- `message`: Log message
- `timestamp`: Log timestamp

## Troubleshooting

### Dexcom Authorization Issues
- Ensure redirect URI in Dexcom app matches your domain exactly
- Check that DEXCOM_USE_SANDBOX is set correctly (False for production)
- Verify OAuth tokens are being saved (check Settings table in database)

### Sync Not Working
- Check Dexcom connection status on dashboard
- Verify destinations are configured in Settings
- Check sync logs on dashboard for error messages
- Ensure sync interval is set (default: 5 minutes)

### Database Issues
- Default uses SQLite in `data/dexcom_sync.db`
- For MySQL, ensure database and user are created
- Check database permissions

### Docker Issues
```bash
# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check logs
docker-compose logs -f

# Access container shell
docker-compose exec dexcom-sync bash
```

## Security Best Practices

1. **Change Default Password**: Immediately change admin password after first login
2. **Use Strong Encryption Key**: Generate with `Fernet.generate_key()`
3. **Secure .env File**: Never commit `.env` to version control
4. **Use HTTPS**: Always use Cloudflared or another SSL solution
5. **Regular Updates**: Keep dependencies updated
6. **Backup Database**: Regular backups of `data/dexcom_sync.db`

## Development

### Running in Development Mode

```bash
# Set debug mode in .env
FLASK_DEBUG=True

# Run with auto-reload
python app.py
```

### Adding New Connectors

1. Create new connector in `connectors/` directory
2. Inherit pattern from existing connectors
3. Implement `is_configured()` and `upload_readings()` methods
4. Add to `sync_manager.py`
5. Add settings fields to `settings.html`

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review troubleshooting section above

## Acknowledgments

- Dexcom for CGM technology and API
- Nightscout community for open-source CGM platform
- Flask and Python communities
- All contributors to this project

## Changelog

### Version 1.0.0
- Initial release
- Dexcom API integration with OAuth
- Multiple destination support (Nightscout, MySQL, Airtable, Google Sheets)
- Retro industrial web interface
- Encrypted data storage
- Docker support
- Automatic background syncing
- Interactive dashboard with charts

---

**Note**: This application is for personal use and is not affiliated with or endorsed by Dexcom, Inc. Always consult with healthcare professionals for medical advice.
