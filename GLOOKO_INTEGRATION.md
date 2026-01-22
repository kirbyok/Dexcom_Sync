# Glooko Omnipod Integration

## Overview

This integration syncs **Omnipod pump treatment data** from Glooko to Nightscout. It does **NOT** sync CGM or glucose readings - those come from Dexcom via the existing integration.

## What Gets Synced

From Glooko (Omnipod only):
- ✅ **Boluses** (meal bolus, correction bolus)
- ✅ **Temp Basals** (temporary basal rate changes)
- ✅ **Pump Suspends** (shown as 0 U/hr temp basal)
- ❌ **NOT CGM data** (Dexcom handles this)
- ❌ **NOT scheduled basal rates** (Nightscout uses profile basals)

## Configuration

### Environment Variables (.env)

```bash
# Glooko Configuration (for Omnipod pump data only)
GLOOKO_EMAIL=your-glooko-email@example.com
GLOOKO_PASSWORD=your-glooko-password
GLOOKO_SYNC_ENABLED=true
```

### Important Notes

1. **API Documentation Needed**: The current implementation uses placeholder endpoints. You need actual Glooko API documentation to configure:
   - Authentication endpoint (currently `/v1/oauth2/token`)
   - Insulin/pump data endpoint (currently `/v1/users/me/data/insulin`)
   - Response format structure

2. **Runs Alongside Dexcom**: 
   - Dexcom → CGM glucose readings → Nightscout `/api/v1/entries`
   - Glooko → Omnipod treatments → Nightscout `/api/v1/treatments`

3. **Nightscout Required**: Treatments push requires `NIGHTSCOUT_URL` and `NIGHTSCOUT_API_TOKEN` to be configured.

## Usage

### Continuous Mode (Recommended)
```bash
python main.py continuous
```
Every 3 minutes:
1. Syncs Dexcom CGM data
2. Syncs Glooko Omnipod treatments (if enabled)

### Manual Sync
```bash
# Sync recent Omnipod data (last 24 hours)
python main.py once

# Backfill 7 days of Omnipod treatments
python main.py backfill --days 7
```

## Architecture

### Data Flow
```
Omnipod Pod → Glooko Cloud → glooko_client.py → nightscout_treatments.py → Nightscout
```

### Files
- **glooko_client.py**: Fetches Omnipod pump events from Glooko API
- **nightscout_treatments.py**: Pushes treatments to Nightscout `/api/v1/treatments`
- **main.py**: Orchestrates both Dexcom CGM and Glooko pump syncs

## Treatment Format

Nightscout treatments follow this format:

### Bolus
```json
{
  "created_at": "2026-01-21T12:30:00Z",
  "eventType": "Meal Bolus",
  "insulin": 4.5,
  "carbs": 45,
  "enteredBy": "Glooko/Omnipod"
}
```

### Temp Basal
```json
{
  "created_at": "2026-01-21T12:00:00Z",
  "eventType": "Temp Basal",
  "duration": 30,
  "absolute": 1.5,
  "rate": 1.5,
  "enteredBy": "Glooko/Omnipod"
}
```

## Troubleshooting

### "GLOOKO: Email or password not configured"
- Check `.env` file has `GLOOKO_EMAIL` and `GLOOKO_PASSWORD` set
- Verify `GLOOKO_SYNC_ENABLED=true`

### "401 Unauthorized" from Glooko
- Verify Glooko credentials are correct
- Check if Glooko API endpoint URL is correct (needs documentation)

### "No Omnipod treatments found"
- Glooko may not have recent data
- API endpoint or filtering may need adjustment
- Check if device is actually named "Omnipod" in Glooko data

### Treatments not appearing in Nightscout
- Verify `NIGHTSCOUT_URL` and `NIGHTSCOUT_API_TOKEN` are correct
- Check Nightscout logs for authentication errors
- Ensure api-secret has write permissions

## API Documentation Needed

To complete this integration, you need Glooko API documentation for:

1. **Base URL**: Currently using `https://api.glooko.com` (placeholder)
2. **Authentication**: OAuth2 endpoint and required parameters
3. **Insulin Data Endpoint**: Path and query parameters
4. **Response Format**: JSON structure for pump events
5. **Device Filtering**: How to filter for Omnipod vs other pumps
6. **Rate Limits**: API throttling and pagination

## Related Documentation

- [Nightscout Connect Plugin](https://github.com/nightscout/cgm-remote-monitor#connect-nightscout-connect)
- [Nightscout Treatments API](https://github.com/nightscout/cgm-remote-monitor/blob/master/lib/server/treatments.js)
- Nightscout event types: Meal Bolus, Correction Bolus, Temp Basal, Site Change, etc.

## Support

If you have Glooko API documentation or experience with their API, please share:
1. Authentication flow details
2. Pump data endpoint paths
3. Response JSON examples
4. Device identification method
