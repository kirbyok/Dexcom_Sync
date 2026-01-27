#!/usr/bin/env python3
"""
Tandem Pump Client - Interface to Tandem pump via tconnectsync
"""

import logging
from typing import Any, Dict, List, Optional
from typing import cast
import os
import time
import datetime
import base64
import hashlib
import json
import urllib.parse
import requests

logger = logging.getLogger('tandem_client')


class TandemClient:
    """Secure interface to Tandem pump data (framework-inspired, no external lib)."""
    
    def __init__(self, username: str, password: str):
        """
        Initialize Tandem client
        
        Args:
            username: t:connect username
            password: t:connect password
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DexcomSync/1.0 (+security minimal)'
        })
        self.base_url = os.getenv('TCONNECT_BASE_URL', 'https://tdcservices.tandemdiabetes.com')
        self.token: Optional[str] = None
        self.token_exp: Optional[int] = None
        self.user_id: Optional[str] = None
    
    @staticmethod
    def _extract_events(payload: Any) -> List[Dict[str, Any]]:
        """Return list of dict events from Tandem API payloads."""
        if isinstance(payload, dict):
            payload_dict = cast(Dict[str, Any], payload)
            events_obj: Any = payload_dict.get('event', [])
            events_list: List[Any] = cast(List[Any], events_obj) if isinstance(events_obj, list) else []
            return [cast(Dict[str, Any], e) for e in events_list if isinstance(e, dict)]
        if isinstance(payload, list):
            payload_list = cast(List[Any], payload)
            return [cast(Dict[str, Any], e) for e in payload_list if isinstance(e, dict)]
        return []

    def authenticate(self) -> bool:
        """
        Authenticate with t:connect
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            logger.info("Authenticating with Tandem (secure client)...")
            if not self.username or not self.password:
                logger.error("Missing t:connect credentials")
                return False

            # Tandem Source OIDC PKCE flow
            region = (os.getenv('TCONNECT_REGION') or 'US').upper()
            if region not in ('US', 'EU'):
                region = 'US'

            if region == 'US':
                login_api_url = 'https://tdcservices.tandemdiabetes.com/accounts/api/login'
                authorization_endpoint = 'https://tdcservices.tandemdiabetes.com/accounts/api/connect/authorize'
                token_endpoint = 'https://tdcservices.tandemdiabetes.com/accounts/api/connect/token'
                client_id = '0oa27ho9tpZE9Arjy4h7'
                redirect_uri = 'https://sso.tandemdiabetes.com/auth/callback'
            else:
                login_api_url = 'https://tdcservices.eu.tandemdiabetes.com/accounts/api/login'
                authorization_endpoint = 'https://tdcservices.eu.tandemdiabetes.com/accounts/api/connect/authorize'
                token_endpoint = 'https://tdcservices.eu.tandemdiabetes.com/accounts/api/connect/token'
                client_id = '1519e414-eeec-492e-8c5e-97bea4815a10'
                redirect_uri = 'https://source.eu.tandemdiabetes.com/authorize/callback'

            # Step 1: Login API
            req = self.session.post(
                login_api_url,
                json={'username': self.username, 'password': self.password},
                headers={'Content-Type': 'application/json'},
                timeout=20
            )
            if req.status_code != 200:
                logger.error('Login API failed: HTTP %s', req.status_code)
                return False
            j = req.json()
            if j.get('status') != 'SUCCESS':
                logger.error('Login status not SUCCESS')
                return False

            # Step 2: Authorization (PKCE)
            def _code_verifier() -> str:
                return base64.urlsafe_b64encode(os.urandom(64)).decode('utf-8').rstrip('=')

            def _code_challenge(verifier: str) -> str:
                digest = hashlib.sha256(verifier.encode('utf-8')).digest()
                return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')

            verifier = _code_verifier()
            challenge = _code_challenge(verifier)
            params = {
                'client_id': client_id,
                'response_type': 'code',
                'scope': 'openid profile email',
                'redirect_uri': redirect_uri,
                'code_challenge': challenge,
                'code_challenge_method': 'S256',
            }
            auth_res = self.session.get(
                authorization_endpoint + '?' + urllib.parse.urlencode(params),
                allow_redirects=True,
                timeout=30
            )
            # Final URL should contain code
            loc = auth_res.url
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
            if 'code' not in qs:
                logger.error('OIDC authorize did not return code')
                return False
            code = qs['code'][0]

            # Step 3: Token exchange
            token_data = {
                'grant_type': 'authorization_code',
                'client_id': client_id,
                'code': code,
                'redirect_uri': redirect_uri,
                'code_verifier': verifier,
            }
            tok = self.session.post(
                token_endpoint,
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=20
            )
            if tok.status_code // 100 != 2:
                logger.error('Token exchange failed: HTTP %s', tok.status_code)
                return False
            tj = tok.json()
            access = tj.get('access_token')
            id_token = tj.get('id_token')
            expires_in = int(tj.get('expires_in', 3600))
            if not access or not id_token:
                logger.error('Missing access_token or id_token')
                return False

            # Decode id_token claims (unverified) to read userId
            try:
                parts = id_token.split('.')
                payload_b64 = parts[1] + '==='  # pad base64url
                payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode('utf-8'))
                self.user_id = payload.get('userId')
                sub = payload.get('sub') or ''
                # sub looks like 'user:GUID'
                self.user_guid = sub.split(':', 1)[1] if ':' in sub else None
            except Exception:
                self.user_id = None
                self.user_guid = None

            self.token = access
            self.token_exp = int(time.time()) + expires_in
            logger.info('Authentication successful (OIDC PKCE)')
            return True
        except Exception as e:
            logger.error(f"Failed to initialize authentication: {e}")
            return False
    
    def get_therapy_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get therapy events (insulin deliveries, corrections, etc.) from the last N hours
        
        Args:
            hours: Number of hours to look back (default: 24)
        
        Returns:
            List of therapy event dictionaries
        """
        if not self.token:
            logger.error("Not authenticated with t:connect")
            return []
        
        try:
            logger.debug(f"Fetching therapy events from last {hours} hours")
            # Compute date range (endpoint expects YYYY-MM-DD, inclusive)
            end_dt = datetime.datetime.now(datetime.timezone.utc)
            start_dt = end_dt - datetime.timedelta(hours=hours)
            start_date = start_dt.strftime('%Y-%m-%d')
            end_date = end_dt.strftime('%Y-%m-%d')

            logger.info(f"Date range: {start_date} to {end_date}")

            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }

            # Try both endpoints: TherapyEvents and ControlIQ therapy timeline
            raw_events_te: List[Dict[str, Any]] = []
            raw_events_ci: List[Dict[str, Any]] = []

            # Endpoint 1: tconnect/therapyevents (Source API)
            if self.user_id:
                te_url = f"{self.base_url}/tconnect/therapyevents/api/TherapyEvents/{start_date}/{end_date}/false?userId={self.user_id}"
                try:
                    resp = self.session.get(te_url, headers=headers, timeout=20)
                    logger.info(f"TherapyEvents URL: {te_url}")
                    logger.info(f"TherapyEvents HTTP {resp.status_code}")
                    if resp.status_code == 200:
                        payload_any: Any = resp.json()
                        logger.info(f"TherapyEvents raw payload keys: {list(payload_any.keys()) if isinstance(payload_any, dict) else 'not a dict'}")
                        if isinstance(payload_any, dict) and 'event' in payload_any:
                            logger.info(f"TherapyEvents 'event' key type: {type(payload_any['event'])}, len={len(payload_any['event']) if isinstance(payload_any['event'], list) else 'N/A'}")
                        raw_events_te = self._extract_events(payload_any)
                        logger.info(f"TherapyEvents endpoint returned {len(raw_events_te)} events")
                    else:
                        logger.info(f"TherapyEvents response: {resp.text[:500]}")
                except Exception as e:
                    logger.error(f"TherapyEvents fetch failed: {e}")

            # Endpoint 2: ControlIQ therapy timeline (also with Source API but different path)
            if self.user_guid:
                ci_url = f"{self.base_url}/tconnect/controliq/api/therapytimeline/users/{self.user_guid}?startDate={start_date}&endDate={end_date}"
                try:
                    ci_resp = self.session.get(ci_url, headers=headers, timeout=20)
                    logger.info(f"ControlIQ URL: {ci_url}")
                    logger.info(f"ControlIQ HTTP {ci_resp.status_code}")
                    if ci_resp.status_code == 200:
                        ci_payload_any: Any = ci_resp.json()
                        raw_events_ci = self._extract_events(ci_payload_any)
                        logger.info(f"ControlIQ timeline returned {len(raw_events_ci)} events")
                    else:
                        logger.info(f"ControlIQ response: {ci_resp.text[:500]}")
                except Exception as e:
                    logger.error(f"ControlIQ timeline fetch failed: {e}")

            combined_list: List[Dict[str, Any]] = []
            combined_list.extend(raw_events_te or [])
            combined_list.extend(raw_events_ci or [])

            # Define pump vs CGM classifications
            pump_types = {
                'Bolus', 'BolusWizard', 'Correction', 'Meal',
                'TempBasal', 'Basal', 'Suspend', 'Resume', 'SuspendResume',
                'InfusionSet', 'Reservoir', 'CartridgeChange', 'SiteChange',
            }
            cgm_indicators = ('CGM', 'Sensor', 'Calibration', 'BloodGlucose', 'Transmitter', 'BG')

            def is_pump_event(ev: Dict[str, Any]) -> bool:
                et = (ev.get('type') or '').strip()
                if any(ind in et for ind in cgm_indicators):
                    return False
                if et in pump_types:
                    return True
                # Fallback: exclude if event carries glucose-like fields
                keys = set(ev.keys())
                glucose_keys = {'sgv', 'glucose', 'glucoseValue', 'calculatedBG', 'meterBg'}
                if keys & glucose_keys:
                    return False
                return True

            events: List[Dict[str, Any]] = []
            for ev in combined_list:
                if not is_pump_event(ev):
                    continue
                etype = ev.get('type')
                created_at = ev.get('eventDateTime') or ev.get('dateTime') or ev.get('timestamp')
                treatment: Dict[str, Any] = {
                    'eventType': self._map_event_type(etype or ''),
                    'created_at': created_at,
                    'enteredBy': 'Tandem',
                }
                # Map bolus amounts
                if etype == 'Bolus' or etype == 'Correction' or etype == 'BolusWizard':
                    amt = ev.get('standard') or ev.get('extended') or ev.get('amount') or ev.get('bolusAmount')
                    if isinstance(amt, (int, float)):
                        treatment['insulin'] = float(amt)
                    carbs = ev.get('carbs') or ev.get('mealCarbs') or ev.get('carbAmount')
                    if isinstance(carbs, (int, float)):
                        treatment['carbs'] = int(carbs)
                # Map temp basal
                if etype == 'TempBasal':
                    pct = ev.get('percent')
                    rate = ev.get('rate')
                    duration = ev.get('duration')
                    if isinstance(pct, (int, float)):
                        treatment['percent'] = int(pct)
                    if isinstance(rate, (int, float)):
                        treatment['rate'] = float(rate)
                    if isinstance(duration, (int, float)):
                        treatment['duration'] = int(duration)
                # Map suspend/resume
                if etype in ('Suspend', 'Resume', 'SuspendResume'):
                    treatment['notes'] = etype
                # Map site/reservoir changes
                if etype in ('InfusionSet', 'SiteChange'):
                    treatment['eventType'] = 'Site Change'
                if etype in ('Reservoir', 'CartridgeChange'):
                    treatment['notes'] = 'Reservoir/Cartridge change'

                events.append(treatment)

            logger.info(f"Retrieved {len(events)} therapy events")
            return events
        except Exception as e:
            logger.error(f"Failed to fetch therapy events: {e}")
            return []

    def get_last_event_uploaded(self, pump_serial: Optional[int]) -> Optional[Dict[str, Any]]:
        """Check last uploaded event index for a given pump serial number."""
        if not self.token:
            logger.error("Not authenticated with t:connect")
            return None
        if not pump_serial:
            return None
        try:
            url = f"{self.base_url}/cloud/upload/getlasteventuploaded?sn={pump_serial}"
            headers = {
                'Authorization': f'Bearer {self.token}',
                'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 12; Pixel 4a Build/SP2A.220305.012)'
            }
            resp = self.session.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.warning("last_event_uploaded failed: HTTP %s", resp.status_code)
                return None
            return resp.json()
        except Exception as e:
            logger.error("Failed to query last_event_uploaded: %s", e)
            return None
    
    def get_basal_rate_segments(self) -> List[Dict[str, Any]]:
        """
        Get basal rate profile segments derived from recent pump events
        
        Returns:
            List of basal rate segment dictionaries
        """
        if not self.token:
            logger.error("Not authenticated with t:connect")
            return []
        
        try:
            logger.debug("Deriving basal rate segments from recent events")
            # Derive segments from last 24h events (Basal and TempBasal)
            events = self.get_therapy_events(hours=24)
            segments: List[Dict[str, Any]] = []
            # Build a simple schedule of basal changes observed
            for ev in events:
                et = (ev.get('eventType') or '').lower()
                if 'basal' in et or et == 'temp basal' or 'tempbasal' in (ev.get('type') or ''):
                    created_at = ev.get('created_at')
                    rate = ev.get('rate')
                    if isinstance(rate, (int, float)) and isinstance(created_at, str):
                        try:
                            # Extract HH:MM from timestamp
                            # Accept ISO strings with Z or offset
                            ts = created_at.replace('Z', '+00:00')
                            dt = datetime.datetime.fromisoformat(ts)
                            start_str = dt.strftime('%H:%M')
                        except Exception:
                            start_str = '00:00'
                        segment: Dict[str, Any] = {
                            'startTime': start_str,
                            'rate': float(rate),
                        }
                        segments.append(segment)
            
            logger.info(f"Retrieved {len(segments)} basal rate segments")
            return segments
        except Exception as e:
            logger.error(f"Failed to fetch basal rate segments: {e}")
            return []
    
    def get_pump_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current pump status derived from recent events and diagnostics
        
        Returns:
            Pump status dictionary or None if error
        """
        if not self.token:
            logger.error("Not authenticated with t:connect")
            return None
        
        try:
            logger.debug("Deriving pump status from recent events")
            status: Dict[str, Any] = {
                'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            # Determine suspended/resumed state by last event
            events = self.get_therapy_events(hours=24)
            suspended = None
            last_suspend_ts = None
            last_resume_ts = None
            for ev in events:
                et = (ev.get('eventType') or '')
                ts = ev.get('created_at')
                if et in ('Suspend', 'Suspend/Resume'):
                    suspended = True
                    last_suspend_ts = ts
                elif et == 'Resume':
                    suspended = False
                    last_resume_ts = ts
            if suspended is not None:
                status['suspended'] = suspended
            if last_suspend_ts:
                status['last_suspend'] = last_suspend_ts
            if last_resume_ts:
                status['last_resume'] = last_resume_ts

            # Include last uploaded event index if pump serial provided
            pump_serial_env = os.getenv('TCONNECT_PUMP_SERIAL')
            pump_serial = int(pump_serial_env) if pump_serial_env and pump_serial_env.isdigit() else None
            last = self.get_last_event_uploaded(pump_serial)
            if last:
                status['lastEventIndex'] = last.get('maxPumpEventIndex')
                status['processingStatus'] = last.get('processingStatus')

            logger.info("Retrieved pump status")
            return status
        except Exception as e:
            logger.error(f"Failed to fetch pump status: {e}")
            return None
    
    def process_therapy_events(self) -> List[Dict[str, Any]]:
        """
        Process therapy events for syncing to Nightscout
        
        Returns:
            List of processed events ready for Nightscout
        """
        events = self.get_therapy_events(hours=24)
        processed: List[Dict[str, Any]] = []
        
        for event in events:
            try:
                # Map Tandem event types to Nightscout format
                treatment: Dict[str, Any] = {
                    'eventType': self._map_event_type(event.get('eventType', '')),
                    'created_at': event.get('created_at') or event.get('eventDateTime'),
                    'enteredBy': 'Tandem',
                }
                
                # Add type-specific data
                if 'insulin' in event:
                    treatment['insulin'] = event['insulin']
                
                if 'carbs' in event:
                    treatment['carbs'] = event['carbs']
                
                # Explicitly avoid any CGM/BG fields; Dexcom handles CGM
                
                processed.append(treatment)
            except Exception as e:
                logger.warning(f"Failed to process event: {e}")
                continue
        
        return processed
    
    @staticmethod
    def _map_event_type(tandem_event_type: str) -> str:
        """
        Map Tandem event types to Nightscout event types
        
        Args:
            tandem_event_type: Event type from Tandem API
        
        Returns:
            Nightscout event type
        """
        event_mapping = {
            'Bolus': 'Bolus',
            'BolusWizard': 'Bolus',
            'Meal': 'Carb',
            'Exercise': 'Exercise',
            'Correction': 'Correction Bolus',
            'InfusionSet': 'Site Change',
            'Reservoir': 'Rewind',
            'SuspendResume': 'Suspend/Resume',
        }
        return event_mapping.get(tandem_event_type, 'Note')
