import os
import requests
from datetime import datetime
from hashlib import sha1
from typing import Any, Dict, Optional

class NightscoutConnector:
    """Connector for Nightscout API"""
    
    def __init__(self, url: str, api_token: str):
        self.url = url.rstrip('/')
        raw_secret = api_token.strip()
        # Nightscout expects a SHA1 hash; if the provided token is not already a 40-char hex hash, hash it.
        if len(raw_secret) == 40 and all(c in '0123456789abcdef' for c in raw_secret.lower()):
            self.api_secret = raw_secret
        else:
            self.api_secret = sha1(raw_secret.encode('utf-8')).hexdigest()
        # Allow overriding device name via env (fallback to Dexcom)
        self.device_name = os.getenv('DEXCOM_DEVICE_NAME', 'Dexcom')
        self.session = requests.Session()
        self.session.headers.update({
            'api-secret': self.api_secret,
            'Content-Type': 'application/json'
        })
    
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
            response = self.session.post(url, json=ns_entry, timeout=10)
            response.raise_for_status()
            
            # Debug: log what we sent
            print(f"[PUSH] SGV: {ns_entry['sgv']}, Device: {ns_entry.get('device', 'MISSING')}, Time: {ns_entry['dateString']}")
            
            return True
        except Exception as e:
            print(f"Error pushing to Nightscout: {e}")
            return False
    
    def get_latest_reading(self) -> Optional[Dict[str, Any]]:
        """Get latest reading from Nightscout"""
        try:
            url = f"{self.url}/api/v1/entries/sgv"
            response = self.session.get(url, params={'count': 1}, timeout=10)
            response.raise_for_status()
            
            # The endpoint returns tab-separated values with quoted fields
            # Format: "2026-01-22T06:47:50.329Z"  1769064470329  109  "Flat"  "unknown"
            text = response.text.strip()
            
            # Split by whitespace (including tabs), removing quotes
            parts = [p.strip('"') for p in text.split() if p]
            if len(parts) >= 3:
                date_str = parts[0]
                sgv = int(parts[2])
                direction = parts[3] if len(parts) > 3 else 'None'
                
                return {
                    'timestamp': datetime.fromisoformat(date_str.replace('Z', '+00:00')),
                    'value': sgv,
                    'trend': direction
                }
            return None
        except Exception as e:
            print(f"Error getting latest reading from Nightscout: {e}")
            return None


