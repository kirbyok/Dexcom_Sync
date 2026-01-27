# Quick Start Guide

This guide will help you get Dexcom Sync up and running in 15 minutes.

## Step 1: Prerequisites (5 minutes)

### A. Register with Dexcom Developer Portal
1. Go to https://developer.dexcom.com
2. Sign up for a developer account
3. Create a new application
4. Note down:
   - Client ID
   - Client Secret
   - Set Redirect URI to: `http://localhost:5000/dexcom/callback` (for testing)

### B. Install Docker (if not already installed)
- **Windows/Mac**: Download Docker Desktop from docker.com
- **Linux**: `sudo apt-get install docker.io docker-compose`

## Step 2: Setup Application (5 minutes)

### Clone or Download
```bash
cd d:\vsCode\Dexcom_Sync
```

### Configure Environment
```bash
# Copy the example environment file
copy .env.example .env

# Edit .env with your favorite editor
notepad .env
```

### Essential Settings in .env:
```env
# Change these!
ADMIN_PASSWORD=your-secure-password-here

# Add your Dexcom credentials
DEXCOM_CLIENT_ID=your-client-id-from-dexcom
DEXCOM_CLIENT_SECRET=your-client-secret-from-dexcom
DEXCOM_REDIRECT_URI=http://localhost:5000/dexcom/callback

# Tandem pump sync (optional)
TCONNECT_USERNAME=your_tconnect_email@example.com
TCONNECT_PASSWORD=your_tconnect_password
TCONNECT_SYNC_ENABLED=false
TCONNECT_DEVICE_NAME=Tandem
# Feature toggles (default true; set to false to disable)
TCONNECT_FEATURE_BASAL=true
TCONNECT_FEATURE_BOLUS=true
TCONNECT_FEATURE_PUMP_EVENTS=true
TCONNECT_FEATURE_PROFILES=true

# Generate these (run commands below)
FLASK_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
ENCRYPTION_KEY=<run: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
```

### Generate Keys (PowerShell):
```powershell
# Flask Secret Key
python -c "import secrets; print(secrets.token_hex(32))"

# Encryption Key  
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output and paste into your .env file.

## Step 3: Launch Application (2 minutes)

### With Docker (Recommended):
```bash
# Build and start
docker-compose up -d

# Check if running
docker-compose ps

# View logs
docker-compose logs -f
```

### Without Docker:
```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run
python app.py

# Backfill last 24h (either or both sources)
python backfill.py --source both --hours 24
python backfill.py --source dexcom --hours 24
python backfill.py --source tandem --hours 24
```

### Tandem feature toggles: quick guidance
- Turn off bolus sync if you log boluses manually in Nightscout: `TCONNECT_FEATURE_BOLUS=false`.
- Leave pump events on to see sleep/exercise modes, alarms, suspend/resume: `TCONNECT_FEATURE_PUMP_EVENTS=true` (default).
- Turn off profiles if you manage insulin profiles only in Nightscout: `TCONNECT_FEATURE_PROFILES=false`.
- Turn off basal/temp basal if you only care about boluses: `TCONNECT_FEATURE_BASAL=false`.

## Step 4: Access Dashboard (1 minute)

1. Open browser: http://localhost:5000
2. Login:
   - Username: `admin`
   - Password: (what you set in .env)

## Step 5: Connect Dexcom (2 minutes)

1. Click **Settings** in the navigation
2. Click **AUTHORIZE DEXCOM** button
3. Login to your Dexcom account
4. Authorize the application
5. You'll be redirected back to settings

## Step 6: Configure Destinations (Optional)

Choose which services you want to sync to:

### Nightscout
1. Enter your Nightscout URL (e.g., `https://yourname.herokuapp.com`)
2. Enter your API Secret
3. Click Save

### MySQL
1. Setup a MySQL database
2. Enter host, port, database name, username, password
3. Click Save

### Airtable
1. Create an Airtable base
2. Get your API key from https://airtable.com/account
3. Enter API key and Base ID
4. Click Save

### Google Sheets
1. Create a Google Cloud service account
2. Download JSON credentials
3. Share your spreadsheet with service account email
4. Paste JSON credentials in settings
5. Click Save

## Step 7: Test Sync

1. Return to Dashboard
2. Click **MANUAL SYNC** button
3. Watch for success message
4. Check your configured destinations for data

## Troubleshooting

### Can't connect to Dexcom
- Verify Client ID and Secret are correct
- Check Redirect URI matches exactly
- Try using sandbox mode first: `DEXCOM_USE_SANDBOX=True`

### No data syncing
- Ensure you completed Dexcom authorization
- Check that you have recent CGM data in your Dexcom account
- View sync logs on dashboard for errors

### Docker issues
```bash
# Rebuild everything
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Port 5000 already in use
Change port in docker-compose.yml:
```yaml
ports:
  - "8080:5000"  # Use 8080 instead
```

## Next Steps

1. **Setup Cloudflared** for HTTPS access (see README.md)
2. **Configure automatic backups** of your database
3. **Monitor sync logs** to ensure data is flowing
4. **Customize sync interval** in Settings (default: 5 minutes)

## Security Reminders

- ✅ Change default admin password immediately
- ✅ Use strong encryption keys (never share)
- ✅ Don't commit .env file to git
- ✅ Use HTTPS in production (Cloudflared)
- ✅ Regular database backups

## Getting Help

- Read the full README.md
- Check GitHub issues
- Review troubleshooting section above

## Production Deployment

For production use:
1. Set `FLASK_DEBUG=False` in .env
2. Use strong passwords and keys
3. Setup Cloudflared tunnel for HTTPS
4. Configure proper firewall rules
5. Setup automated backups
6. Monitor logs regularly

---

**Congratulations!** Your Dexcom Sync system is now running. Your glucose data will automatically sync every 5 minutes to your configured destinations.
