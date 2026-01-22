import requests
import os
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NightscoutTreatments:
    """Client for pushing pump treatments to Nightscout.
    
    Handles posting boluses, basal rates, and other pump events
    to Nightscout's /api/v1/treatments endpoint.
    """
    
    def __init__(self):
        self.base_url = os.getenv('NIGHTSCOUT_URL', '').rstrip('/')
        self.api_token = os.getenv('NIGHTSCOUT_API_TOKEN', '')
        
        if not self.base_url or not self.api_token:
            raise ValueError("NIGHTSCOUT_URL and NIGHTSCOUT_API_TOKEN must be set")
        
        self.session = requests.Session()
        self.session.headers.update({
            'api-secret': self.api_token,
            'Content-Type': 'application/json'
        })
    
    def push_treatment(self, treatment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Push a single treatment to Nightscout.
        
        Args:
            treatment: Treatment dictionary with keys like:
                - created_at: ISO timestamp
                - eventType: 'Meal Bolus', 'Correction Bolus', 'Temp Basal', etc.
                - insulin: amount in units (for boluses)
                - duration: minutes (for temp basals)
                - absolute: U/hr (for temp basals)
                - carbs: grams (optional)
                - enteredBy: source string
                
        Returns:
            Response data from Nightscout, or None if failed
        """
        try:
            url = f"{self.base_url}/api/v1/treatments"
            response = self.session.post(url, json=treatment, timeout=10)
            response.raise_for_status()
            
            logger.debug(f"Pushed treatment: {treatment['eventType']} at {treatment['created_at']}")
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Nightscout API authentication failed (401)")
                logger.error("Check your NIGHTSCOUT_API_TOKEN")
            else:
                logger.error(f"HTTP {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error pushing treatment to Nightscout: {e}")
            return None
    
    def push_treatments(self, treatments: list[Dict[str, Any]]) -> tuple[int, int]:
        """Push multiple treatments to Nightscout.
        
        Args:
            treatments: List of treatment dictionaries
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        if not treatments:
            logger.info("No treatments to push")
            return (0, 0)
        
        success_count = 0
        fail_count = 0
        
        for treatment in treatments:
            result = self.push_treatment(treatment)
            if result:
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"Pushed {success_count}/{len(treatments)} treatments to Nightscout")
        if fail_count > 0:
            logger.warning(f"Failed to push {fail_count} treatments")
        
        return (success_count, fail_count)
    
    def get_latest_treatment(self, event_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the most recent treatment from Nightscout.
        
        Useful for determining what data has already been synced.
        
        Args:
            event_type: Optional filter by eventType (e.g. 'Meal Bolus')
            
        Returns:
            Latest treatment dict, or None if none found
        """
        try:
            url = f"{self.base_url}/api/v1/treatments"
            params: Dict[str, Any] = {'count': 1}
            if event_type:
                params['find[eventType]'] = event_type
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            treatments = response.json()
            if treatments and len(treatments) > 0:
                return treatments[0]
            return None
            
        except Exception as e:
            logger.error(f"Error fetching latest treatment: {e}")
            return None

    def update_profile(self, profile: Dict[str, Any]) -> bool:
        """Update Nightscout profile settings (basal, ratios, targets)."""
        try:
            url = f"{self.base_url}/api/v1/profile"
            response = self.session.post(url, json=profile, timeout=10)
            response.raise_for_status()
            logger.info("Nightscout profile updated")
            return True
        except Exception as e:
            logger.error(f"Error updating Nightscout profile: {e}")
            return False
