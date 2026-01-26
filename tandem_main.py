#!/usr/bin/env python3
"""
Tandem Sync - Sync Tandem pump treatments to Nightscout
Runs independently from Dexcom CGM sync
"""

import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from tandem_client import TandemClient
from nightscout_treatments import NightscoutTreatments

# Load environment variables
load_dotenv()

# Setup logging
def setup_logging():
    """Configure logging with file rotation every 2 days"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'tandem_sync.log'
    
    # Create logger
    logger = logging.getLogger('tandem_sync')
    logger.setLevel(logging.INFO)
    
    # Format: [YYYY-MM-DD HH:MM:SS] LEVEL: Message
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation every 2 days
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=2,
        backupCount=10  # Keep 10 backup files
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler for real-time output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

class TandemSync:
    """Tandem pump treatment sync manager"""
    
    def __init__(self):
        # Check if Tandem sync is enabled
        tandem_enabled = os.getenv('TCONNECT_SYNC_ENABLED', 'false').lower() == 'true'
        if not tandem_enabled:
            logger.error("Tandem sync is not enabled. Set TCONNECT_SYNC_ENABLED=true in .env")
            sys.exit(1)
        
        # Initialize Tandem client
        tconnect_username = os.getenv('TCONNECT_USERNAME')
        tconnect_password = os.getenv('TCONNECT_PASSWORD')
        
        if not tconnect_username or not tconnect_password:
            logger.error("TCONNECT_USERNAME and TCONNECT_PASSWORD must be set in .env")
            sys.exit(1)
        
        self.tandem = TandemClient(tconnect_username, tconnect_password)
        
        # Authenticate with t:connect
        if not self.tandem.authenticate():
            logger.error("Failed to authenticate with t:connect")
            sys.exit(1)
        
        # Initialize Nightscout treatments
        ns_url = os.getenv('NIGHTSCOUT_URL')
        ns_token = os.getenv('NIGHTSCOUT_API_TOKEN')
        
        if not ns_url or not ns_token:
            logger.error("NIGHTSCOUT_URL and NIGHTSCOUT_API_TOKEN must be set in .env")
            sys.exit(1)
        
        self.nightscout_treatments = NightscoutTreatments()
        logger.info("Tandem Pump Sync initialized")

    def _build_nightscout_profile(self, basal_segments: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Convert Tandem basal segments into a Nightscout profile payload."""
        if not basal_segments:
            return None

        profile_name: str = 'Tandem t:slim'
        timezone_name: str = os.getenv('TIMEZONE', 'UTC')

        # Convert basal segments to Nightscout format
        basal_entries: List[Dict[str, Any]] = []
        for segment in basal_segments:
            entry: Dict[str, Any] = {
                'start': segment.get('startTime', '00:00'),
                'minutes': 0,
                'rate': segment.get('rate', 0)
            }
            basal_entries.append(entry)

        profile: Dict[str, Any] = {
            'defaultProfile': profile_name,
            'startDate': datetime.now(timezone.utc).isoformat(),
            'timezone': timezone_name,
            'store': {
                profile_name: {
                    'basal': basal_entries,
                    'carbratio': [],
                    'sens': [],
                    'target_low': [],
                    'target_high': []
                }
            }
        }

        return profile
    
    def sync(self, hours: int = 24):
        """Sync Tandem pump treatments to Nightscout
        
        Args:
            hours: Number of hours to sync (default: 24)
        """
        try:
            logger.info("=" * 60)
            logger.info("Starting Tandem pump treatment sync...")
            logger.info("=" * 60)
            
            logger.info(f"Syncing last {hours} hours of Tandem treatments...")
            
            # Fetch therapy events from Tandem
            treatments: List[Dict[str, Any]] = self.tandem.process_therapy_events()
            
            if not treatments:
                logger.info("No Tandem pump treatments found from t:connect")
                logger.info("=" * 60)
                return True
            
            logger.info(f"Retrieved {len(treatments)} Tandem pump treatments")
            
            # Show summary of treatments
            bolus_count = sum(1 for t in treatments if 'Bolus' in t.get('eventType', ''))
            meal_count = sum(1 for t in treatments if 'Carb' in t.get('eventType', ''))
            correction_count = sum(1 for t in treatments if 'Correction' in t.get('eventType', ''))
            logger.info(f"  Boluses: {bolus_count}")
            logger.info(f"  Meals: {meal_count}")
            logger.info(f"  Corrections: {correction_count}")
            
            # Check for duplicates - filter out treatments already in Nightscout
            logger.info("\nChecking for existing treatments in Nightscout...")
            latest_ns_treatment = self.nightscout_treatments.get_latest_treatment()
            if latest_ns_treatment and 'created_at' in latest_ns_treatment:
                # Parse the latest timestamp from Nightscout
                latest_ns_time_str = latest_ns_treatment['created_at']
                if isinstance(latest_ns_time_str, str):
                    latest_ns_time = datetime.fromisoformat(latest_ns_time_str.replace('Z', '+00:00'))
                else:
                    latest_ns_time = latest_ns_time_str
                
                logger.info(f"Latest Nightscout treatment: {latest_ns_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Filter to only new treatments
                new_treatments: List[Dict[str, Any]] = []
                for t in treatments:
                    if 'created_at' in t:
                        t_time = datetime.fromisoformat(t['created_at'].replace('Z', '+00:00'))
                        if t_time > latest_ns_time:
                            new_treatments.append(t)
                
                if not new_treatments:
                    logger.info("[OK] No new treatments to push (all already in Nightscout)")
                    logger.info("=" * 60)
                    return True
                
                logger.info(f"Found {len(new_treatments)} new treatment(s) to push")
                treatments = new_treatments
            else:
                logger.info("No existing treatments in Nightscout, pushing all")

            # Update Nightscout profile from Tandem basal segments if available
            basal_segments = self.tandem.get_basal_rate_segments()
            if basal_segments:
                profile_payload = self._build_nightscout_profile(basal_segments)
                if profile_payload:
                    logger.info("Updating Nightscout profile with Tandem basal rates...")
                    if self.nightscout_treatments.update_profile(profile_payload):
                        logger.info("[OK] Nightscout profile updated from Tandem basal rates")
                    else:
                        logger.warning("Failed to update Nightscout profile")
                else:
                    logger.info("Tandem basal segments missing; skipping profile update")
            else:
                logger.info("No Tandem basal rate segments available; skipping profile update")
            
            # Show sample treatments
            if len(treatments) > 0:
                logger.info("\nMost recent treatments:")
                for i, treatment in enumerate(treatments[-3:], 1):
                    event_type = treatment.get('eventType', 'Unknown')
                    created_at = treatment.get('created_at', '')
                    
                    if 'Bolus' in event_type:
                        insulin = treatment.get('insulin', 0)
                        carbs = treatment.get('carbs', '')
                        carbs_str = f", {carbs}g carbs" if carbs else ""
                        logger.info(f"  {i}. {event_type}: {insulin}U{carbs_str} at {created_at}")
                    else:
                        logger.info(f"  {i}. {event_type} at {created_at}")
            
            # Push to Nightscout
            logger.info("\nPushing treatments to Nightscout...")
            success_count, fail_count = self.nightscout_treatments.push_treatments(treatments)
            
            logger.info("=" * 60)
            logger.info(f"[OK] Tandem sync completed: {success_count} pushed, {fail_count} failed")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error(f"Tandem pump treatment sync failed: {e}", exc_info=True)
            logger.info("=" * 60)
            return False
    
    def run_continuous(self):
        """Run continuous syncing for Tandem pump treatments"""
        import time
        
        interval = int(os.getenv('SYNC_INTERVAL_MINUTES', '3')) * 60
        logger.info(f"Starting continuous Tandem pump sync every {os.getenv('SYNC_INTERVAL_MINUTES', '3')} minutes")
        logger.info("Press Ctrl+C to stop.\n")
        
        try:
            while True:
                self.sync()
                logger.info(f"\nWaiting {interval // 60} minutes until next sync...\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("\nTandem pump sync stopped by user")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tandem Sync - Sync Tandem pump treatments to Nightscout')
    parser.add_argument(
        'action',
        nargs='?',
        default='once',
        choices=['once', 'continuous', 'config'],
        help='Action to perform (default: once)'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Number of hours to sync (default: 24)'
    )
    
    args = parser.parse_args()
    
    sync = TandemSync()
    
    if args.action == 'config':
        logger.info("=" * 60)
        logger.info("TANDEM SYNC CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"t:connect Username: {os.getenv('TCONNECT_USERNAME', 'NOT SET')}")
        logger.info(f"Tandem Sync Enabled: {os.getenv('TCONNECT_SYNC_ENABLED', 'false')}")
        logger.info(f"Nightscout URL: {os.getenv('NIGHTSCOUT_URL', 'NOT SET')}")
        logger.info(f"Sync Interval: {os.getenv('SYNC_INTERVAL_MINUTES', '3')} minutes")
        logger.info("=" * 60)
        
    elif args.action == 'once':
        sync.sync(hours=args.hours)
        
    elif args.action == 'continuous':
        sync.run_continuous()


if __name__ == '__main__':
    main()
