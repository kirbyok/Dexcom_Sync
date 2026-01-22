import requests
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GlookoClient:
    """Client for Glooko API to retrieve Omnipod pump treatment data only.
    
    This client fetches insulin pump data (boluses, basals, temp basals) from
    Glooko for Omnipod devices. It does NOT fetch CGM or glucose data.
    """
    
    BASE_URL = "https://api.glooko.com"  # May need adjustment based on actual API
    
    def __init__(self):
        self.email = os.getenv('GLOOKO_EMAIL')
        self.password = os.getenv('GLOOKO_PASSWORD')
        self.patient_id = os.getenv('GLOOKO_PATIENT_ID')
        self.access_token = None
        self.refresh_token = None
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DexSync-Glooko/1.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def login(self) -> bool:
        """Authenticate with Glooko API using OAuth2 password grant"""
        if not self.email or not self.password:
            logger.warning("GLOOKO: Email or password not configured")
            return False
        
        try:
            logger.info(f"Authenticating with Glooko for: {self.email}")
            
            # Glooko authentication endpoint (adjust based on actual API documentation)
            auth_url = f"{self.BASE_URL}/v1/oauth2/token"
            auth_data = {
                'email': self.email,
                'password': self.password,
                'grant_type': 'password'
            }
            
            response = self.session.post(auth_url, json=auth_data, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data.get('access_token')
            self.refresh_token = data.get('refresh_token')
            
            if self.access_token:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })
                logger.info("Successfully authenticated with Glooko")
                return True
            
            logger.error("No access token received from Glooko")
            return False
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Glooko authentication failed (401 Unauthorized)")
                logger.error("Please check your Glooko email/password")
            else:
                logger.error(f"HTTP Error {e.response.status_code}: {e.response.reason}")
            return False
        except Exception as e:
            logger.error(f"Error during Glooko authentication: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if authenticated with Glooko"""
        return bool(self.access_token)
    
    def logout(self):
        """Logout from Glooko"""
        self.access_token = None
        self.refresh_token = None
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
    
    def get_pump_treatments(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch Omnipod pump treatment data from Glooko.
        
        Returns boluses, basal rates, and temp basals formatted for Nightscout treatments.
        Does NOT return CGM/glucose data.
        
        Args:
            start_date: Start datetime for treatment retrieval (UTC)
            end_date: End datetime for treatment retrieval (UTC)
            
        Returns:
            List of treatment dictionaries formatted for Nightscout /api/v1/treatments
        """
        if not self.access_token:
            if not self.login():
                raise Exception("Not logged in to Glooko")
        
        # Default to last 24 hours
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(hours=24)
        
        try:
            # Glooko API endpoint for pump/insulin delivery data
            # NOTE: This endpoint is a placeholder and needs actual Glooko API documentation
            pump_url = f"{self.BASE_URL}/v1/users/me/data/insulin"
            
            params = {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'device_type': 'omnipod'  # Filter for Omnipod only
            }
            
            logger.info(f"Fetching Omnipod treatments from {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
            
            response = self.session.get(pump_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Parse treatment data
            treatments: List[Dict[str, Any]] = []
            
            # Parse based on Glooko API response structure (adjust based on actual API)
            if data and 'data' in data:
                for record in data['data']:
                    treatment = self._parse_pump_event(record)
                    if treatment:
                        treatments.append(treatment)
            
            # Sort by timestamp
            treatments.sort(key=lambda t: t.get('created_at', ''))
            
            logger.info(f"Retrieved {len(treatments)} Omnipod treatments from Glooko")
            return treatments
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Glooko session expired (401 Unauthorized)")
                self.access_token = None
                logger.info("Will re-authenticate on next attempt")
            else:
                logger.error(f"HTTP Error {e.response.status_code}: {e.response.reason}")
            return []
        except Exception as e:
            logger.error(f"Error fetching Omnipod treatments from Glooko: {e}")
            return []
    
    def _seconds_to_hhmm(self, seconds: int) -> str:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"

    def get_pump_settings(self, sync_timestamp: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch pump settings (basal, ratios, targets) for Omnipod devices via Glooko Pump Settings API."""
        if not self.access_token and not self.login():
            logger.error("Cannot fetch pump settings: not authenticated")
            return None
        if not self.patient_id:
            logger.warning("GLOOKO_PATIENT_ID not set; skipping pump settings fetch")
            return None
        try:
            url = f"{self.BASE_URL}/api/v2/external/pumps/settings"
            params: Dict[str, Any] = {'patient': self.patient_id}
            if sync_timestamp:
                params['syncTimestamp'] = sync_timestamp
            logger.info("Fetching Omnipod pump settings from Glooko")
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = cast(Dict[str, Any], resp.json())
            pumps_raw: Any = data.get('pumpsSettings', []) if data else []
            pumps_list = cast(List[Dict[str, Any]], pumps_raw) if isinstance(pumps_raw, list) else []
            pumps: List[Dict[str, Any]] = list(pumps_list)
            if not pumps:
                logger.info("No pump settings returned")
                return None

            # Use the latest by updatedAt
            pumps_sorted: List[Dict[str, Any]] = sorted(
                pumps,
                key=lambda p: str(p.get('updatedAt') or p.get('timestamp') or ''),
                reverse=True
            )
            settings: Dict[str, Any] = pumps_sorted[0]

            profile_name: str = str(settings.get('profileName') or 'Omnipod')
            utc_offset: str = str(settings.get('utcOffset', '+00:00'))

            # Basal segments
            basal_entries: List[Dict[str, Any]] = []
            basal_programs: List[Dict[str, Any]] = settings.get('basalSettings', []) or []
            for program in basal_programs:
                segments: List[Dict[str, Any]] = program.get('segments', []) or []
                for idx, seg in enumerate(segments):
                    start_secs = int(seg.get('start', 0))
                    rate = float(seg.get('rate', 0))
                    basal_entries.append({'i': idx, 'start': self._seconds_to_hhmm(start_secs), 'rate': rate})

            # Carb ratios
            carb_ratios: List[Dict[str, Any]] = []
            for idx, seg in enumerate(settings.get('insulinToCarbsRatioSegments', []) or []):
                time_val = self._seconds_to_hhmm(int(seg.get('start', 0)))
                value = float(seg.get('insulinToCarbsRatio', 0))
                carb_ratios.append({'i': idx, 'time': time_val, 'value': value})

            # ISF
            sens_list: List[Dict[str, Any]] = []
            for idx, seg in enumerate(settings.get('isfSegments', []) or []):
                time_val = self._seconds_to_hhmm(int(seg.get('start', 0)))
                value = float(seg.get('insulinSensitivityFactor', 0))
                sens_list.append({'i': idx, 'time': time_val, 'value': value})

            # Targets
            target_low: List[Dict[str, Any]] = []
            target_high: List[Dict[str, Any]] = []
            for idx, seg in enumerate(settings.get('targetBgSegments', []) or []):
                time_val = self._seconds_to_hhmm(int(seg.get('start', 0)))
                if 'targetBgLow' in seg or 'targetBgHigh' in seg:
                    low_val = float(seg.get('targetBgLow', seg.get('targetBg', 0)))
                    high_val = float(seg.get('targetBgHigh', seg.get('targetBg', low_val)))
                else:
                    val = float(seg.get('targetBg', 0))
                    low_val = val
                    high_val = val
                target_low.append({'i': idx, 'time': time_val, 'value': low_val})
                target_high.append({'i': idx, 'time': time_val, 'value': high_val})

            return {
                'profile_name': profile_name,
                'timezone': utc_offset,
                'basal_profile': basal_entries,
                'carb_ratios': carb_ratios,
                'insulin_sensitivity': sens_list,
                'target_low': target_low,
                'target_high': target_high,
            }
        except Exception as e:
            logger.error(f"Error fetching pump settings: {e}")
            return None
    
    def _parse_pump_event(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a Glooko pump event into Nightscout treatment format.
        
        Args:
            record: Raw pump event from Glooko API
            
        Returns:
            Nightscout treatment dict, or None if not Omnipod or unparseable
        """
        try:
            # Only process Omnipod data
            device_name = record.get('device', '').lower()
            if 'omnipod' not in device_name:
                return None
            
            event_type = record.get('type', '').lower()
            
            # Parse timestamp
            timestamp_str = record.get('timestamp') or record.get('date')
            if not timestamp_str:
                return None
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            
            treatment: Dict[str, Any] = {
                'created_at': timestamp.isoformat(),
                'enteredBy': 'Glooko/Omnipod',
                'device': 'Omnipod',
                'notes': f"Synced from Glooko ({record.get('device', 'Omnipod')})"
            }
            
            # Parse different event types
            if event_type in ['bolus', 'meal_bolus', 'correction_bolus', 'normal_bolus']:
                treatment['eventType'] = 'Meal Bolus' if 'meal' in event_type else 'Correction Bolus'
                treatment['insulin'] = float(record.get('amount', record.get('insulin', 0)))
                
                # Include carbs if present
                if 'carbs' in record and record['carbs']:
                    treatment['carbs'] = float(record['carbs'])
            
            elif event_type in ['temp_basal', 'temporary_basal']:
                treatment['eventType'] = 'Temp Basal'
                treatment['duration'] = int(record.get('duration_minutes', record.get('duration', 30)))
                treatment['absolute'] = float(record.get('rate', record.get('basal_rate', 0)))
                treatment['rate'] = treatment['absolute']
            
            elif event_type == 'basal':
                # Scheduled basal rates are typically not imported as treatments
                # Nightscout uses profile basals instead
                return None
            
            elif event_type == 'suspend':
                treatment['eventType'] = 'Temp Basal'
                treatment['duration'] = int(record.get('duration_minutes', 30))
                treatment['absolute'] = 0
                treatment['rate'] = 0
            
            else:
                logger.debug(f"Unknown Omnipod event type: {event_type}")
                return None
            
            return treatment
            
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Error parsing Omnipod pump event: {e}")
            return None
