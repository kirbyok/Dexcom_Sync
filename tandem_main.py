#!/usr/bin/env python3
"""
Tandem Sync - Sync Tandem pump treatments to Nightscout
Runs independently from Dexcom CGM sync
"""

import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from tandem_client import TandemClient
from nightscout_treatments import NightscoutTreatments
from tconnectsync_adapter import run_tconnectsync

# Load environment variables from explicit path
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


def _prepare_tconnect_environment() -> None:
    """Ensure tconnectsync has writable config/cache locations on read-only roots."""
    base = Path(os.getenv('LOG_DIR', '/app/logs'))
    config_dir = Path(os.getenv('TCONNECT_CACHE_DIR', base / '.config' / 'tconnectsync'))
    os.environ.setdefault('HOME', str(base))
    os.environ.setdefault('XDG_CONFIG_HOME', str(config_dir))
    os.environ.setdefault('XDG_CACHE_HOME', str(config_dir))
    os.environ.setdefault('TCONNECT_CACHE_DIR', str(config_dir))
    config_dir.mkdir(parents=True, exist_ok=True)
    base.mkdir(parents=True, exist_ok=True)


# Setup logging
def setup_logging():
    """Configure logging; falls back to console if file is not writable."""
    logger = logging.getLogger('tandem_sync')
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_dir = Path(os.getenv('LOG_DIR', '/app/logs'))
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'tandem_sync.log'
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=2,
            backupCount=10
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as exc:  # noqa: BLE001
        logger.warning("File logging disabled: %s", exc)

    return logger

logger = setup_logging()
_prepare_tconnect_environment()

class TandemSync:
    """Tandem pump treatment sync manager"""
    
    def __init__(self):
        # Check if Tandem sync is enabled
        tandem_enabled = os.getenv('TCONNECT_SYNC_ENABLED', 'false').lower() == 'true'
        if not tandem_enabled:
            logger.error("Tandem sync is not enabled. Set TCONNECT_SYNC_ENABLED=true in .env")
            sys.exit(1)
        
        self.backend = os.getenv('TCONNECT_BACKEND', 'tconnectsync').lower()
        use_tconnectsync = self.backend == 'tconnectsync'

        tconnect_username = os.getenv('TCONNECT_USERNAME')
        tconnect_password = os.getenv('TCONNECT_PASSWORD')
        ns_url = os.getenv('NS_URL') or os.getenv('NIGHTSCOUT_URL')
        ns_token = os.getenv('NS_SECRET') or os.getenv('NIGHTSCOUT_API_TOKEN')

        if not tconnect_username or not tconnect_password:
            logger.error("TCONNECT_USERNAME and TCONNECT_PASSWORD must be set in .env")
            sys.exit(1)

        if not ns_url or not ns_token:
            logger.error("NIGHTSCOUT_URL/NS_URL and NS_SECRET/NIGHTSCOUT_API_TOKEN must be set in .env")
            sys.exit(1)

        if use_tconnectsync:
            self.tandem = None
            self.nightscout_treatments = None
            logger.info("Using tconnectsync-master backend for Tandem pump sync")
        else:
            self.tandem = TandemClient(tconnect_username, tconnect_password)

            # Initialize secure auth; continue even if unavailable to keep container running
            if not self.tandem.authenticate():
                logger.error("Tandem secure auth not initialized; continuing without pump sync")

            self.nightscout_treatments = NightscoutTreatments()
            logger.info("Tandem Pump Sync initialized")

        # Feature toggles (default enabled)
        def _feature(flag: str) -> bool:
            return os.getenv(flag, 'true').lower() not in ('false', '0', 'no')

        self.features = {
            'BASAL': _feature('TCONNECT_FEATURE_BASAL'),
            'BOLUS': _feature('TCONNECT_FEATURE_BOLUS'),
            'PUMP_EVENTS': _feature('TCONNECT_FEATURE_PUMP_EVENTS'),
            'PROFILES': _feature('TCONNECT_FEATURE_PROFILES'),
        }
        logger.info(
            "Feature flags | BASAL=%s BOLUS=%s PUMP_EVENTS=%s PROFILES=%s",
            self.features['BASAL'],
            self.features['BOLUS'],
            self.features['PUMP_EVENTS'],
            self.features['PROFILES'],
        )

        # Optional diagnostics: check last uploaded event
        if self.tandem:
            pump_serial_env = os.getenv('TCONNECT_PUMP_SERIAL')
            pump_serial = int(pump_serial_env) if pump_serial_env and pump_serial_env.isdigit() else None
            last = self.tandem.get_last_event_uploaded(pump_serial)
            if last:
                logger.info(f"Pump last uploaded event index: {last.get('maxPumpEventIndex')} status={last.get('processingStatus')}")

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
        if self.backend == 'tconnectsync':
            logger.info("Running tconnectsync-master backend for last %s hour(s)...", hours)
            result = run_tconnectsync(hours, self.features, logger)
            logger.info("tconnectsync backend completed (success=%s)", result)
            return result
        try:
            logger.info("=" * 60)
            logger.info("Starting Tandem pump treatment sync...")
            logger.info("=" * 60)
            
            logger.info(f"Syncing last {hours} hours of Tandem treatments...")
            
            # Fetch therapy events from Tandem
            treatments: List[Dict[str, Any]] = self.tandem.process_therapy_events()

            # Apply feature filters
            def _category(t: Dict[str, Any]) -> str:
                et = (t.get('eventType') or '').lower()
                if et in ('bolus', 'correction bolus', 'carb'):
                    return 'BOLUS'
                if 'temp basal' in et or 'basal' in et:
                    return 'BASAL'
                return 'PUMP_EVENTS'

            filtered: List[Dict[str, Any]] = []
            for t in treatments:
                cat = _category(t)
                if cat == 'BASAL' and not self.features['BASAL']:
                    continue
                if cat == 'BOLUS' and not self.features['BOLUS']:
                    continue
                if cat == 'PUMP_EVENTS' and not self.features['PUMP_EVENTS']:
                    continue
                filtered.append(t)

            if len(filtered) != len(treatments):
                logger.info(
                    "Feature filters applied: kept %s of %s (BASAL=%s BOLUS=%s PUMP_EVENTS=%s)",
                    len(filtered), len(treatments),
                    self.features['BASAL'], self.features['BOLUS'], self.features['PUMP_EVENTS']
                )
            treatments = filtered
            
            # Update Nightscout profile independently from treatments (first, while we have segments)
            if self.features['PROFILES']:
                basal_segments = self.tandem.get_basal_rate_segments()
                if not basal_segments:
                    # Fallback: create a simple default profile for testing
                    logger.info("No basal segments from pump events; creating default profile for testing...")
                    basal_segments = [
                        {'startTime': '00:00', 'rate': 0.5},
                        {'startTime': '06:00', 'rate': 0.6},
                        {'startTime': '12:00', 'rate': 0.7},
                        {'startTime': '18:00', 'rate': 0.6},
                    ]
                
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
    parser.add_argument(
        '--features',
        type=str,
        default=None,
        help='Comma-separated feature list to enable (e.g., profiles or basal,bolus,pump_events,profiles)'
    )
    
    args = parser.parse_args()
    
    sync = TandemSync()
    
    # Override feature flags if --features specified
    if args.features:
        allowed_features = {'basal', 'bolus', 'pump_events', 'profiles'}
        requested = set(f.strip().lower() for f in args.features.split(','))
        invalid = requested - allowed_features
        if invalid:
            logger.error("Invalid feature(s): %s. Allowed: %s", invalid, allowed_features)
            return
        # Disable all, then enable only requested
        for feat in allowed_features:
            sync.features[feat.upper()] = feat in requested
        logger.info(
            "Feature overrides applied: BASAL=%s BOLUS=%s PUMP_EVENTS=%s PROFILES=%s",
            sync.features['BASAL'], sync.features['BOLUS'],
            sync.features['PUMP_EVENTS'], sync.features['PROFILES']
        )
    
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
