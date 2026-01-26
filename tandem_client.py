#!/usr/bin/env python3
"""
Tandem Pump Client - Interface to Tandem pump via tconnectsync
"""

import logging
from typing import Any, Dict, List, Optional
from tconnectsync import TConnectApi  # type: ignore[import-untyped]

logger = logging.getLogger('tandem_client')


class TandemClient:
    """Interface to Tandem pump data via tconnectsync"""
    
    def __init__(self, username: str, password: str):
        """
        Initialize Tandem client
        
        Args:
            username: t:connect username
            password: t:connect password
        """
        self.username = username
        self.password = password
        self.api = None
        self.authenticated = False
    
    def authenticate(self) -> bool:
        """
        Authenticate with t:connect
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            logger.info("Authenticating with t:connect...")
            self.api = TConnectApi(self.username, self.password)
            
            # Verify connection by accessing tandemsource
            # This will trigger the authentication flow
            if self.api:
                _ = self.api.tandemsource
            
            self.authenticated = True
            logger.info("Successfully authenticated with t:connect")
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with t:connect: {e}")
            self.authenticated = False
            return False
    
    def get_therapy_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get therapy events (insulin deliveries, corrections, etc.) from the last N hours
        
        Args:
            hours: Number of hours to look back (default: 24)
        
        Returns:
            List of therapy event dictionaries
        """
        if not self.authenticated:
            logger.error("Not authenticated with t:connect")
            return []
        
        try:
            logger.debug(f"Fetching therapy events from last {hours} hours")
            # Use tandemsource to get therapy data
            # The actual structure depends on tconnectsync implementation
            # For now, return empty list as placeholder
            events: List[Dict[str, Any]] = []
            
            logger.info(f"Retrieved {len(events)} therapy events")
            return events
        except Exception as e:
            logger.error(f"Failed to fetch therapy events: {e}")
            return []
    
    def get_basal_rate_segments(self) -> List[Dict[str, Any]]:
        """
        Get current basal rate profile segments
        
        Returns:
            List of basal rate segment dictionaries
        """
        if not self.authenticated:
            logger.error("Not authenticated with t:connect")
            return []
        
        try:
            logger.debug("Fetching basal rate segments")
            # Use controliq API to get basal profile
            # Placeholder for actual implementation
            segments: List[Dict[str, Any]] = []
            
            logger.info(f"Retrieved {len(segments)} basal rate segments")
            return segments
        except Exception as e:
            logger.error(f"Failed to fetch basal rate segments: {e}")
            return []
    
    def get_pump_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current pump status
        
        Returns:
            Pump status dictionary or None if error
        """
        if not self.authenticated:
            logger.error("Not authenticated with t:connect")
            return None
        
        try:
            logger.debug("Fetching pump status")
            # Use ws2 or android API to get status
            # Placeholder for actual implementation
            status: Dict[str, Any] = {}
            
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
                    'created_at': event.get('eventDateTime'),
                    'timestamp': event.get('eventDateTime'),
                }
                
                # Add type-specific data
                if 'bolusAmount' in event:
                    treatment['insulin'] = event['bolusAmount']
                
                if 'carbAmount' in event:
                    treatment['carbs'] = event['carbAmount']
                
                if 'bloodGlucose' in event:
                    treatment['glucose'] = event['bloodGlucose']
                    treatment['glucoseType'] = 'Finger'
                
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
