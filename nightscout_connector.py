import logging
import os
import requests
from datetime import datetime
from hashlib import sha1
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class NightscoutConnector:
    """Connector for Nightscout API"""
    
    def __init__(self, url: str, api_token: str):
        self.url = url.rstrip('/')
        raw_secret = api_token.strip()
        # Role-based access tokens (e.g. "dexcom-abc123") use ?token= query param.
        # Plain API secrets (passwords) are SHA1-hashed into the api-secret header.
        if '-' in raw_secret and not (len(raw_secret) == 40 and all(c in '0123456789abcdef' for c in raw_secret.lower())):
            self.role_token = raw_secret
            self.api_secret = None
        else:
            self.role_token = None
            if len(raw_secret) == 40 and all(c in '0123456789abcdef' for c in raw_secret.lower()):
                self.api_secret = raw_secret
            else:
                self.api_secret = sha1(raw_secret.encode('utf-8')).hexdigest()
        # Allow overriding device name via env (fallback to Dexcom)
        self.device_name = os.getenv('DEXCOM_DEVICE_NAME', 'Dexcom')
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        if self.api_secret:
            self.session.headers.update({'api-secret': self.api_secret})
    
    def push_reading(self, reading: Dict[str, Any]) -> bool:
        """Push a glucose reading to Nightscout"""
        try:
            # Format reading for Nightscout
            ts = reading['timestamp']
            ns_entry: Dict[str, Any] = {
                'type': 'sgv',
                'dateString': ts.isoformat(),
                'date': int(ts.timestamp() * 1000),
                'sgv': reading['value'],
                'direction': reading['trend'],
                'device': self.device_name
            }

            # Optional fields when available from Dexcom
            if reading.get('trend_rate') is not None:
                ns_entry['trendRate'] = reading['trend_rate']
            if reading.get('filtered') is not None:
                ns_entry['filtered'] = reading['filtered']
            if reading.get('unfiltered') is not None:
                ns_entry['unfiltered'] = reading['unfiltered']
            if reading.get('rssi') is not None:
                ns_entry['rssi'] = reading['rssi']
            if reading.get('noise') is not None:
                ns_entry['noise'] = reading['noise']
            
            # POST to Nightscout
            url = f"{self.url}/api/v1/entries"
            params = {'token': self.role_token} if self.role_token else {}
            response = self.session.post(url, json=ns_entry, params=params, timeout=10)
            response.raise_for_status()
            
            logger.debug("[PUSH] SGV: %s, Device: %s, Time: %s",
                         ns_entry['sgv'], ns_entry.get('device', 'MISSING'), ns_entry['dateString'])
            return True
        except Exception as e:
            logger.error("Error pushing to Nightscout: %s", e)
            return False
    
    def get_latest_reading(self) -> Optional[Dict[str, Any]]:
        """Get latest reading from Nightscout"""
        try:
            url = f"{self.url}/api/v1/entries/sgv.json"
            params: Dict[str, Any] = {'count': 1}
            if self.role_token:
                params['token'] = self.role_token
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            entries = response.json()
            if entries:
                entry = entries[0]
                return {
                    'timestamp': datetime.fromisoformat(entry['dateString'].replace('Z', '+00:00')),
                    'value': entry['sgv'],
                    'trend': entry.get('direction', 'None')
                }
            return None
        except Exception as e:
            logger.error("Error getting latest reading from Nightscout: %s", e)
            return None


