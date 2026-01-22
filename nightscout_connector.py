import requests
import os
from datetime import datetime, timezone
from typing import Dict

class NightscoutConnector:
    """Connector for Nightscout API"""
    
    def __init__(self, url: str, api_token: str):
        self.url = url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'api-secret': api_token,
            'Content-Type': 'application/json'
        })
    
    def push_reading(self, reading: Dict) -> bool:
        """Push a glucose reading to Nightscout"""
        try:
            # Format reading for Nightscout
            ns_entry = {
                'type': 'sgv',
                'dateString': reading['timestamp'].isoformat(),
                'date': int(reading['timestamp'].timestamp() * 1000),
                'sgv': reading['value'],
                'direction': reading['trend']
            }
            
            # POST to Nightscout
            url = f"{self.url}/api/v1/entries"
            response = self.session.post(url, json=ns_entry, timeout=10)
            response.raise_for_status()
            
            return True
        except Exception as e:
            print(f"Error pushing to Nightscout: {e}")
            return False
    
    def get_latest_reading(self) -> Dict:
        """Get latest reading from Nightscout"""
        try:
            url = f"{self.url}/api/v1/entries/sgv"
            response = self.session.get(url, params={'count': 1}, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data:
                entry = data[0]
                return {
                    'timestamp': datetime.fromisoformat(entry['dateString'].replace('Z', '+00:00')),
                    'value': entry['sgv'],
                    'trend': entry.get('direction', 'None')
                }
            return None
        except Exception as e:
            print(f"Error getting latest reading from Nightscout: {e}")
            return None
