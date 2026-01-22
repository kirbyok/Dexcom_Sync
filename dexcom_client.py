import requests
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

class DexcomClient:
    """Client for interacting with Dexcom Share API (same as Nightscout)"""
    
    # Dexcom Share API endpoints - uses 2-step authentication
    # Based on: https://github.com/nightscout/share2nightscout-bridge
    US_SERVER = "share2.dexcom.com"
    INTL_SERVER = "shareous1.dexcom.com"
    
    # Dexcom application ID (constant from their API)
    APPLICATION_ID = "d89443d2-327c-4a6f-89e5-496bbb0317db"
    
    def __init__(self):
        self.session_id = None
        self.account_id = None
        self.username = os.getenv('DEXCOM_EMAIL') or os.getenv('DEXCOM_PHONE')
        self.password = os.getenv('DEXCOM_PASSWORD')
        self.use_intl = os.getenv('DEXCOM_USE_INTL', 'false').lower() == 'true'
        
        # Determine server
        self.server = self.INTL_SERVER if self.use_intl else self.US_SERVER
        
        # Build endpoints
        self.auth_url = f"https://{self.server}/ShareWebServices/Services/General/AuthenticatePublisherAccount"
        self.login_url = f"https://{self.server}/ShareWebServices/Services/General/LoginPublisherAccountById"
        self.glucose_url = f"https://{self.server}/ShareWebServices/Services/Publisher/ReadPublisherLatestGlucoseValues"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Dexcom-Sync/1.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def login(self) -> bool:
        """Login to Dexcom Share API - 2-step authentication process"""
        if not self.username or not self.password:
            return False
        
        try:
            print(f"Attempting Dexcom Share API authentication for: {self.username}")
            print(f"Using server: {self.server}")
            
            # Step 1: Authenticate to get account ID
            print("Step 1: Authenticating with Dexcom...")
            auth_data = {
                'accountName': self.username,
                'password': self.password,
                'applicationId': self.APPLICATION_ID
            }
            
            auth_response = self.session.post(self.auth_url, json=auth_data, timeout=10)
            auth_response.raise_for_status()
            
            # Response is the account ID (UUID string)
            self.account_id = auth_response.text.strip('"')  # Remove quotes
            print(f"[OK] Got account ID: {self.account_id[:8]}...")
            
            # Step 2: Login with account ID to get session token
            print("Step 2: Getting session token...")
            login_data = {
                'accountId': self.account_id,
                'password': self.password,
                'applicationId': self.APPLICATION_ID
            }
            
            login_response = self.session.post(self.login_url, json=login_data, timeout=10)
            login_response.raise_for_status()
            
            # Response is the session ID (UUID string)
            self.session_id = login_response.text.strip('"')  # Remove quotes
            print(f"[OK] Got session ID: {self.session_id[:8]}...")
            print("[OK] Successfully authenticated with Dexcom Share API")
            
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"ERROR: Authentication failed (401 Unauthorized)")
                print(f"  Please check your Dexcom username/password")
            else:
                print(f"HTTP Error {e.response.status_code}: {e.response.reason}")
                try:
                    print(f"  Response: {e.response.text[:200]}")
                except:
                    pass
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"Connection Error: Could not connect to {self.server}")
            print(f"  This may indicate a network issue or the server is unreachable")
            return False
        except Exception as e:
            print(f"Error during authentication: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if authenticated with Dexcom Share"""
        return bool(self.session_id)
    
    def logout(self):
        """Logout from Dexcom Share API"""
        self.session_id = None
        self.account_id = None
    
    def get_glucose_readings(self, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Fetch glucose readings from Dexcom Share API"""
        if not self.session_id:
            if not self.login():
                raise Exception("Not logged in to Dexcom. Please configure DEXCOM_EMAIL and DEXCOM_PASSWORD.")
        
        # Default to last 24 hours if not specified (use timezone-aware UTC)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(hours=24)
        
        try:
            # Calculate query parameters
            minutes_ago = int((end_date - start_date).total_seconds() / 60)
            
            # Dexcom API expects: minutes (time window) and maxCount (number of records)
            params = {
                'sessionID': self.session_id,
                'minutes': minutes_ago,
                'maxCount': 288  # Max 288 readings (5 minute intervals for 24 hours)
            }
            
            print(f"Fetching readings: {minutes_ago} minutes, max {params['maxCount']} records")
            
            response = self.session.post(self.glucose_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Parse readings
            readings = []
            if data:
                for record in data:
                    try:
                        # Parse the Dexcom timestamp format: 'Date(milliseconds)'
                        # Example: 'Date(1769049770234)'
                        wt_str = record.get('WT', '')
                        # Extract milliseconds: remove 'Date(' and ')'
                        ms_str = wt_str.replace('Date(', '').replace(')', '')
                        timestamp = datetime.fromtimestamp(int(ms_str) / 1000, tz=timezone.utc)
                        
                        readings.append({
                            'timestamp': timestamp,
                            'value': record.get('Value', 0),
                            'trend': record.get('Trend', 'Unknown'),  # Already a string from API
                            'unit': 'mg/dL'
                        })
                    except Exception as e:
                        print(f"Error parsing reading: {e}")
                        continue

                # Ensure readings are sorted from oldest to newest
                readings.sort(key=lambda r: r['timestamp'])
            
            return readings
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("ERROR: Session expired (401 Unauthorized)")
                self.session_id = None
                print("Will re-authenticate on next attempt")
            else:
                print(f"HTTP Error {e.response.status_code}: {e.response.reason}")
            return []
        except Exception as e:
            print(f"Error fetching glucose readings: {e}")
            return []
    
    def get_latest_glucose_reading(self) -> Optional[Dict]:
        """Get the most recent glucose reading"""
        try:
            readings = self.get_glucose_readings(
                start_date=datetime.utcnow() - timedelta(hours=1)
            )
            if readings:
                return readings[-1]  # Most recent is last
            return None
        except Exception as e:
            print(f"Error getting latest reading: {e}")
            return None

