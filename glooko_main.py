#!/usr/bin/env python3
"""
Glooko Sync - Sync Omnipod pump treatments from Glooko to Nightscout
Runs independently from Dexcom CGM sync
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from glooko_client import GlookoClient
from nightscout_treatments import NightscoutTreatments

# Load environment variables
load_dotenv()

# Setup logging
def setup_logging():
    """Configure logging with file rotation every 2 days"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'glooko_sync.log'
    
    # Create logger
    logger = logging.getLogger('glooko_sync')
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

class GlookoSync:
    """Omnipod pump treatment sync manager"""
    
    def __init__(self):
        # Check if Glooko is enabled
        glooko_enabled = os.getenv('GLOOKO_SYNC_ENABLED', 'false').lower() == 'true'
        if not glooko_enabled:
            logger.error("Glooko sync is not enabled. Set GLOOKO_SYNC_ENABLED=true in .env")
            sys.exit(1)
        
        # Initialize Glooko client
        glooko_email = os.getenv('GLOOKO_EMAIL')
        glooko_password = os.getenv('GLOOKO_PASSWORD')
        
        if not glooko_email or not glooko_password:
            logger.error("GLOOKO_EMAIL and GLOOKO_PASSWORD must be set in .env")
            sys.exit(1)
        
        self.glooko = GlookoClient()
        
        # Initialize Nightscout treatments
        ns_url = os.getenv('NIGHTSCOUT_URL')
        ns_token = os.getenv('NIGHTSCOUT_API_TOKEN')
        
        if not ns_url or not ns_token:
            logger.error("NIGHTSCOUT_URL and NIGHTSCOUT_API_TOKEN must be set in .env")
            sys.exit(1)
        
        self.nightscout_treatments = NightscoutTreatments()
        logger.info("Glooko Omnipod Sync initialized")

    def _build_nightscout_profile(self, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert Omnipod settings into a Nightscout profile payload."""
        basal_profile: List[Dict[str, Any]] = settings.get('basal_profile', [])
        if not basal_profile:
            return None

        profile_name: str = settings.get('profile_name', 'Omnipod')
        timezone_name: str = settings.get('timezone', 'UTC')

        # Nightscout expects sorted basal by start time
        basal_entries = sorted(basal_profile, key=lambda b: b.get('start', '00:00'))
        carb_ratios: List[Dict[str, Any]] = settings.get('carb_ratios', [])
        sens_list: List[Dict[str, Any]] = settings.get('insulin_sensitivity', [])
        target_low: List[Dict[str, Any]] = settings.get('target_low', [])
        target_high: List[Dict[str, Any]] = settings.get('target_high', [])

        profile: Dict[str, Any] = {
            'defaultProfile': profile_name,
            'startDate': datetime.now(timezone.utc).isoformat(),
            'timezone': timezone_name,
            'store': {
                profile_name: {
                    'basal': basal_entries,
                    'carbratio': carb_ratios,
                    'sens': sens_list,
                    'target_low': target_low,
                    'target_high': target_high
                }
            }
        }

        return profile
    
    def sync(self, days: int = 0):
        """Sync Omnipod pump treatments from Glooko to Nightscout
        
        Args:
            days: Number of days to backfill (0 = default 24 hours, 1-30 = historical)
        """
        try:
            logger.info("=" * 60)
            logger.info("Starting Omnipod treatment sync...")
            logger.info("=" * 60)
            
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            if days > 0:
                start_date = end_date - timedelta(days=days)
                logger.info(f"Backfilling {days} day(s) of Omnipod treatments...")
            else:
                start_date = end_date - timedelta(hours=24)
                logger.info("Syncing last 24 hours of Omnipod treatments...")
            
            # Fetch treatments from Glooko
            treatments: List[Dict[str, Any]] = self.glooko.get_pump_treatments(
                start_date=start_date,
                end_date=end_date
            )
            
            if not treatments:
                logger.info("No Omnipod treatments found from Glooko")
                logger.info("=" * 60)
                return True
            
            logger.info(f"Retrieved {len(treatments)} Omnipod treatments from Glooko")
            
            # Show summary of treatments
            bolus_count = sum(1 for t in treatments if 'Bolus' in t.get('eventType', ''))
            basal_count = sum(1 for t in treatments if 'Basal' in t.get('eventType', ''))
            logger.info(f"  Meal/Correction Boluses: {bolus_count}")
            logger.info(f"  Temp Basals: {basal_count}")
            
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

            # Update Nightscout profile from Omnipod settings if available
            settings = self.glooko.get_pump_settings()
            if settings:
                profile_payload = self._build_nightscout_profile(settings)
                if profile_payload:
                    logger.info("Updating Nightscout profile with Omnipod basal/ratios/targets...")
                    if self.nightscout_treatments.update_profile(profile_payload):
                        logger.info("[OK] Nightscout profile updated from Omnipod settings")
                    else:
                        logger.warning("Failed to update Nightscout profile")
                else:
                    logger.info("Omnipod settings missing basal profile; skipping profile update")
            else:
                logger.info("No Omnipod pump settings available; skipping profile update")
            
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
                    elif 'Basal' in event_type:
                        rate = treatment.get('absolute', 0)
                        duration = treatment.get('duration', 0)
                        logger.info(f"  {i}. {event_type}: {rate} U/hr for {duration} min at {created_at}")
            
            # Push to Nightscout
            logger.info("\nPushing treatments to Nightscout...")
            success_count, fail_count = self.nightscout_treatments.push_treatments(treatments)
            
            logger.info("=" * 60)
            logger.info(f"[OK] Omnipod sync completed: {success_count} pushed, {fail_count} failed")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error(f"Omnipod treatment sync failed: {e}", exc_info=True)
            logger.info("=" * 60)
            return False
    
    def run_continuous(self):
        """Run continuous syncing for Omnipod treatments"""
        import time
        
        interval = int(os.getenv('SYNC_INTERVAL_MINUTES', '3')) * 60
        logger.info(f"Starting continuous Omnipod sync every {os.getenv('SYNC_INTERVAL_MINUTES', '3')} minutes")
        logger.info("Press Ctrl+C to stop.\n")
        
        try:
            while True:
                self.sync()
                logger.info(f"\nWaiting {interval // 60} minutes until next sync...\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("\nOmnipod sync stopped by user")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Glooko Sync - Sync Omnipod treatments to Nightscout')
    parser.add_argument(
        'action',
        nargs='?',
        default='once',
        choices=['once', 'continuous', 'config', 'backfill'],
        help='Action to perform (default: once)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Number of days to backfill (for backfill action, max 30)'
    )
    
    args = parser.parse_args()
    
    sync = GlookoSync()
    
    if args.action == 'config':
        logger.info("=" * 60)
        logger.info("GLOOKO SYNC CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"Glooko Email: {os.getenv('GLOOKO_EMAIL', 'NOT SET')}")
        logger.info(f"Glooko Sync Enabled: {os.getenv('GLOOKO_SYNC_ENABLED', 'false')}")
        logger.info(f"Nightscout URL: {os.getenv('NIGHTSCOUT_URL', 'NOT SET')}")
        logger.info(f"Sync Interval: {os.getenv('SYNC_INTERVAL_MINUTES', '3')} minutes")
        logger.info("=" * 60)
        
    elif args.action == 'once':
        sync.sync()
        
    elif args.action == 'continuous':
        sync.run_continuous()
        
    elif args.action == 'backfill':
        if args.days < 1 or args.days > 30:
            logger.error("Days must be between 1 and 30")
            sys.exit(1)
        logger.info(f"Backfilling {args.days} days of Omnipod treatments...")
        sync.sync(days=args.days)


if __name__ == '__main__':
    main()
